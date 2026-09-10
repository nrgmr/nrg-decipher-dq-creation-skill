"""Shared types and scanners for the verify suite.

Checks are grouped into topical modules rather than one file per check. Each
check is still an individually named, individually reported unit -- the grouping
is for maintenance, not for lumping results together.
"""

import hashlib
import json
import re
from pathlib import Path
from xml.etree import ElementTree

ERROR = "error"
WARN = "warning"

TEXT_SUFFIXES = {".xml", ".js", ".css", ".less", ".json", ".md", ".txt"}

CONFIG_DEFAULTS = {
    "host": "<your-decipher-host>",
    "server_root": "/home/hermes/v2/selfserve",
    "test_company": "55c",
    "forbidden_companies": ["53b"],
    "local_root": "test_environment",
}


def config():
    """The environment values, from config.json at the skill root.

    Nothing in this skill hardcodes a company code, a host or a server root.
    Set them once and every path, URL and guard follows.

    config.local.json is read last and wins. It is gitignored, so a value that
    should not be published -- an internal hostname, a company code -- stays out
    of the repository and out of everyone else's working tree.
    """
    values = dict(CONFIG_DEFAULTS)
    root = Path(__file__).resolve().parent.parent
    for name in ("config.json", "config.local.json"):
        path = root / name
        if not path.is_file():
            continue
        loaded = json.loads(path.read_text(encoding="utf-8"))
        values.update({k: v for k, v in loaded.items()
                       if k in CONFIG_DEFAULTS})
    return values

# Class names the Forsta survey theme already owns. An unscoped selector on any
# of these reaches elements that are not ours.
THEME_CLASSES = ["grid", "cell", "hidden", "modal", "close", "question",
                 "answers", "question-text", "survey-body", "survey-page"]


class Finding:
    def __init__(self, severity, check, message, prevents="", where=""):
        self.severity = severity
        self.check = check
        self.message = message
        self.prevents = prevents
        self.where = where

    def as_dict(self):
        out = {"severity": self.severity, "check": self.check,
               "message": self.message}
        if self.where:
            out["where"] = self.where
        if self.prevents:
            out["prevents"] = self.prevents
        return out

    def __str__(self):
        head = "%-7s %-22s %s" % (self.severity.upper(), self.check, self.message)
        if self.where:
            head += "\n            at %s" % self.where
        if self.prevents:
            head += "\n            prevents: %s" % self.prevents
        return head


def error(check, message, prevents="", where=""):
    return Finding(ERROR, check, message, prevents, where)


def warn(check, message, prevents="", where=""):
    return Finding(WARN, check, message, prevents, where)


class Ctx:
    """Everything the checks need, parsed once."""

    def __init__(self, package):
        self.dir = Path(package).resolve()
        self.name = None
        self.version = None
        self.errors_reading = []
        self.text = {}          # relative posix path -> file text
        self.xml = {}           # filename -> parsed root, when it parsed
        self.spec = None
        self.legacy = False     # authored before the fenced convention

        m = re.fullmatch(r"v(\d+)", self.dir.name)
        if m and self.dir.parent.name:
            self.name = self.dir.parent.name
            self.version = int(m.group(1))

        for path in sorted(self.dir.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(self.dir).as_posix()
            if path.suffix.lower() in TEXT_SUFFIXES:
                try:
                    self.text[rel] = path.read_text(encoding="utf-8")
                except Exception as exc:                       # noqa: BLE001
                    self.errors_reading.append((rel, str(exc)))

        for name in ("meta.xml", "styles.xml", "survey.xml", "res.xml"):
            if name in self.text:
                try:
                    self.xml[name] = ElementTree.fromstring(self.text[name])
                except ElementTree.ParseError as exc:
                    self.errors_reading.append((name, "XML parse: %s" % exc))

        if "spec.json" in self.text:
            try:
                self.spec = json.loads(self.text["spec.json"])
            except ValueError as exc:
                self.errors_reading.append(("spec.json", "JSON parse: %s" % exc))

        self.legacy = "survey.xml" in self.text and not FENCE_OPEN.search(
            self.text["survey.xml"])

    def js_files(self):
        return {k: v for k, v in self.text.items()
                if k.endswith(".js")}

    def css_files(self):
        return {k: v for k, v in self.text.items()
                if k.endswith(".css")}

    def stylevars(self):
        """name -> {type, title, desc, values, default}"""
        out = {}
        root = self.xml.get("styles.xml")
        if root is None:
            return out
        for node in root:
            if local(node.tag) != "stylevar":
                continue
            full = node.get("name") or ""
            local_name = full.split(":", 1)[1] if ":" in full else full
            out[local_name] = {
                "full": full,
                "type": node.get("type") or "",
                "title": node.get("title") or "",
                "desc": node.get("desc") or "",
                "values": node.get("values") or "",
                "default": (node.text or ""),
            }
        return out

    def includes(self):
        root = self.xml.get("styles.xml")
        if root is None:
            return []
        return [n.get("href") or "" for n in root
                if local(n.tag) in ("include", "less")]


FENCE_OPEN = re.compile(
    r"<!--\s*dq:block\s+(?P<attrs>[^>]*?)-->", re.I)
FENCE_CLOSE = re.compile(r"<!--\s*dq:endblock\s*-->", re.I)
REQUIRES = re.compile(
    r"<!--\s*dq:requires\s+(?P<kind>[a-z-]+)\s+(?P<rest>[^>]*?)-->", re.I)
ATTR = re.compile(r'(\w[\w-]*)\s*=\s*"([^"]*)"')

FENCE_ACTIONS = {"edit", "copy", "copy-verbatim", "optional"}


def local(tag):
    return tag.split("}", 1)[-1]


def parse_fences(text):
    """Return [{id, action, title, body, start, end}] for dq:block regions."""
    blocks = []
    pos = 0
    while True:
        open_m = FENCE_OPEN.search(text, pos)
        if not open_m:
            break
        close_m = FENCE_CLOSE.search(text, open_m.end())
        if not close_m:
            blocks.append({"id": dict(ATTR.findall(open_m.group("attrs"))).get("id", "?"),
                           "action": "", "title": "", "body": "",
                           "start": open_m.start(), "end": -1,
                           "unterminated": True})
            break
        attrs = dict(ATTR.findall(open_m.group("attrs")))
        blocks.append({
            "id": attrs.get("id", ""),
            "action": attrs.get("action", ""),
            "title": attrs.get("title", ""),
            "body": text[open_m.end():close_m.start()],
            "start": open_m.start(),
            "end": close_m.end(),
            "unterminated": False,
        })
        pos = close_m.end()
    return blocks


def parse_requires(text):
    out = []
    for m in REQUIRES.finditer(text):
        out.append({"kind": m.group("kind").strip(),
                    "rest": m.group("rest").strip()})
    return out


def declaration_hash(body):
    """Stable hash of a capture block's declarations.

    Whitespace-insensitive on purpose: the same declarations formatted two ways
    must hash the same, because formatting differences between two copies of a
    block are exactly what made `diff` useless in the previous convention.
    """
    try:
        root = ElementTree.fromstring(wrap_fragment(body))
    except ElementTree.ParseError:
        return None
    parts = []

    def walk(node):
        parts.append(local(node.tag))
        for key in sorted(node.attrib):
            if key == "id":          # server-generated, not ours
                continue
            parts.append("%s=%s" % (key, node.attrib[key]))
        if node.text and node.text.strip():
            parts.append(" ".join(node.text.split()))
        for child in node:
            walk(child)
        parts.append("/" + local(node.tag))

    for child in root:
        walk(child)
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def js_balance(src):
    """Bracket, string, regex and comment balance for ES5-style JavaScript.

    Not a parser. It proves literal and bracket structure, which is what breaks
    when a template interpolates badly -- and that is the whole reason it exists.
    """
    problems = []
    stack = []
    i, n, line = 0, len(src), 1
    prev = ""
    while i < n:
        c = src[i]
        if c == "\n":
            line += 1
            i += 1
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            i = n if j == -1 else j
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            if j == -1:
                problems.append((line, "unterminated block comment"))
                break
            line += src.count("\n", i, j)
            i = j + 2
            continue
        if c in "\"'`":
            quote, j, start = c, i + 1, line
            closed = False
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == "\n":
                    if quote != "`":
                        problems.append((start, "newline inside %s string" % quote))
                        break
                    line += 1
                if src[j] == quote:
                    closed = True
                    break
                j += 1
            if not closed and j >= n:
                problems.append((start, "unterminated %s string" % quote))
                break
            i = j + 1
            prev = quote
            continue
        if c == "/" and (prev == "" or prev in "(,=:[!&|?{};+-*%~^<>"):
            j, in_class, ok = i + 1, False, False
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == "\n":
                    break
                if src[j] == "[":
                    in_class = True
                elif src[j] == "]":
                    in_class = False
                elif src[j] == "/" and not in_class:
                    ok = True
                    break
                j += 1
            if ok:
                i = j + 1
                prev = "/"
                continue
        if c in "([{":
            stack.append((c, line))
            prev = c
            i += 1
            continue
        if c in ")]}":
            want = {")": "(", "]": "[", "}": "{"}[c]
            if not stack:
                problems.append((line, "unmatched closing %s" % c))
            else:
                got, at = stack.pop()
                if got != want:
                    problems.append(
                        (line, "%s closes %s opened on line %d" % (c, got, at)))
            prev = c
            i += 1
            continue
        if not c.isspace():
            prev = c
        i += 1
    for ch, at in stack:
        problems.append((at, "unclosed %s" % ch))
    return problems


def css_balance(src):
    opens = src.count("{")
    closes = src.count("}")
    if opens == closes:
        return []
    return [(0, "brace imbalance: %d open, %d close" % (opens, closes))]


def render_styles(text, stylevars):
    """Substitute every stylevar default into the styles.xml template.

    This is the check that catches an interpolation fault before a browser does.
    """
    def sub_or(m):
        name, fallback = m.group(1), m.group(2)
        info = stylevars.get(name)
        value = info["default"].strip() if info else ""
        return value if value else fallback

    out = re.sub(r'<stylevar\b.*?</stylevar>', '', text, flags=re.S)
    out = re.sub(r"\$\{this\.styles\.[a-z0-9_]+\.([a-z0-9_]+) or '([^']*)'\}",
                 sub_or, out)
    out = re.sub(r"\$\{this\.styles\.[a-z0-9_]+\.([a-z0-9_]+)\}",
                 lambda m: (stylevars.get(m.group(1), {})
                            .get("default", "").strip()), out)
    out = out.replace("${this.label}", "Q_DEMO")
    out = out.replace("${jsexport()}",
                      '{"label":"Q_DEMO","rows":[{"label":"r1","text":"a"},'
                      '{"label":"r2","text":"b"}]}')
    return out


def extract_blocks(text, tag):
    """Return the inner text of every <style name="tag"> block.

    A style block's CDATA routinely contains its own <style type="text/css">,
    so a non-greedy match to the first </style> captures the wrong thing. Match
    the CDATA section instead, and only fall back to the tag form when there is
    no CDATA.
    """
    out = []
    opener = re.compile(r'<style[^>]*\bname="%s"[^>]*>' % re.escape(tag))
    for match in opener.finditer(text):
        rest = text[match.end():]
        cdata = re.match(r"\s*<!\[CDATA\[(.*?)\]\]>", rest, re.S)
        if cdata:
            out.append(cdata.group(1))
            continue
        close = rest.rfind("</style>")
        out.append(rest[:close] if close != -1 else rest)
    return out


def wrap_fragment(body, extra_prefixes=()):
    """Wrap an XML fragment so undeclared namespace prefixes still parse.

    A Builder <template> legitimately uses builder: and the DQ's own prefix,
    neither of which is bound inside the fragment.
    """
    prefixes = {"builder", "ss", "html"} | set(extra_prefixes)
    for match in re.finditer(r"[\s<]([a-z][a-z0-9_]*):[a-zA-Z]", body):
        prefixes.add(match.group(1))
    decls = " ".join('xmlns:%s="urn:x-%s"' % (p, p) for p in sorted(prefixes))
    return "<wrap %s>%s</wrap>" % (decls, body)
