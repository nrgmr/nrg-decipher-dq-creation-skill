"""The demo survey: fences, declared-versus-used attributes, prerequisites."""

import re

from .common import (error, warn, local, parse_fences, parse_requires,
                     FENCE_ACTIONS)

BLOCK_TITLE_FORBIDDEN = re.compile(r"<block\b[^>]*\btitle\s*=", re.I)
EXEC_BAD_VAR = re.compile(r"^\s*(_[A-Za-z0-9_]*)\s*=", re.M)


def demo_fences(ctx):
    """The demo must be fenced so paste blocks can be generated from it."""
    out = []
    text = ctx.text.get("survey.xml")
    if not text:
        return out
    blocks = parse_fences(text)
    if not blocks:
        out.append(warn("demo_fences",
                        "survey.xml has no dq:block fences",
                        "Generated fragments and IMPORT.md come from the fences; "
                        "without them the adopter has a 1,000-line file and no "
                        "boundaries."))
        return out
    ids = []
    for block in blocks:
        if block.get("unterminated"):
            out.append(error("demo_fences",
                             "dq:block id=%r has no dq:endblock" % block["id"]))
            continue
        if not block["id"]:
            out.append(error("demo_fences", "a dq:block has no id"))
        if block["action"] not in FENCE_ACTIONS:
            out.append(error("demo_fences",
                             "dq:block id=%r has action %r; expected one of %s"
                             % (block["id"], block["action"],
                                ", ".join(sorted(FENCE_ACTIONS)))))
        if not block["title"]:
            out.append(warn("demo_fences",
                            "dq:block id=%r has no title" % block["id"],
                            "The title is what IMPORT.md shows the designer."))
        ids.append(block["id"])
    for dupe in {i for i in ids if ids.count(i) > 1}:
        out.append(error("demo_fences", "duplicate dq:block id %r" % dupe))
    if "question" not in ids:
        out.append(error("demo_fences",
                         'no dq:block with id="question"',
                         "IMPORT.md needs to point at the block the designer "
                         "edits."))
    return out


def demo_uses(ctx):
    out = []
    text = ctx.text.get("survey.xml")
    if not text or ctx.name is None:
        return out
    found = re.findall(r'uses="%s\.(\d+)"' % re.escape(ctx.name), text)
    if not found:
        out.append(error("demo_uses",
                         "the demo never invokes %s.%d" % (ctx.name, ctx.version),
                         "A demo that does not use the DQ demonstrates nothing."))
        return out
    wrong = sorted({v for v in found if int(v) != ctx.version})
    for value in wrong:
        out.append(error("demo_uses",
                         "the demo invokes %s.%s but lives in v%d"
                         % (ctx.name, value, ctx.version)))
    if len(set(found)) > 1:
        out.append(error("demo_uses",
                         "the demo invokes more than one version of %s" % ctx.name,
                         "Two versions of one DQ in a survey is fatal."))
    if 'showSource="1"' not in text:
        out.append(warn("demo_uses", 'no showSource="1" on the demo question',
                        "Designers cannot see the XML they are meant to copy."))
    return out


def demo_attrs(ctx):
    """Every namespaced attribute in the demo must be a declared stylevar.

    The packaged demo is never compiled by the platform. Three consecutive
    versions of one package here shipped a demo setting a stylevar the package
    did not declare, in the file adopters are told to copy. This is the check
    that stands in for the compile gate the demo does not get.
    """
    out = []
    text = ctx.text.get("survey.xml")
    if not text or ctx.name is None:
        return out
    declared = set(ctx.stylevars())
    used = set(re.findall(r"%s:([a-z0-9_]+)\s*=" % re.escape(ctx.name), text))
    for name in sorted(used - declared):
        out.append(error("demo_attrs",
                         "the demo sets %s:%s but styles.xml does not declare it"
                         % (ctx.name, name),
                         "Compile error: Style attribute %s:%s is unknown."
                         % (ctx.name, name)))
    if ctx.spec is not None:
        classified = {e.get("name"): e.get("class")
                      for e in ctx.spec.get("parameters", [])}
        restated = []
        for name in sorted(used):
            info = ctx.stylevars().get(name)
            if not info:
                continue
            if classified.get(name) == "internal":
                out.append(warn("demo_attrs",
                                "the demo sets %s:%s, classified internal"
                                % (ctx.name, name),
                                "Internal parameters should not appear on the "
                                "adopting question."))
            match = re.search(r'%s:%s="([^"]*)"' % (re.escape(ctx.name), name),
                              text)
            if match and match.group(1) == info["default"].strip():
                restated.append(name)
        if len(restated) > 6:
            out.append(warn("demo_attrs",
                            "%d demo attributes merely restate the package "
                            "default: %s" % (len(restated),
                                             ", ".join(restated[:6]) + " ..."),
                            "Restating a default pins the survey to today's "
                            "behaviour and defeats any default a later version "
                            "changes."))
    missing_required = []
    if ctx.spec is not None:
        for entry in ctx.spec.get("parameters", []):
            if entry.get("class") == "public-required" \
                    and entry.get("name") not in used:
                missing_required.append(entry.get("name"))
    for name in missing_required:
        out.append(error("demo_attrs",
                         "%s is public-required but the demo does not set it"
                         % name,
                         "The demo must show a designer what they must supply."))
    return out


def survey_grammar(ctx):
    """Survey-side syntax the compiler rejects."""
    out = []
    text = ctx.text.get("survey.xml")
    if not text:
        return out
    for match in BLOCK_TITLE_FORBIDDEN.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        out.append(error("survey_grammar",
                         "<block> carries a title attribute",
                         "Compile error: Extra unrecognized argument given: "
                         "title.", where="survey.xml:%d" % line))
    for body in re.findall(r"<exec[^>]*>(.*?)</exec>", text, re.S):
        for match in EXEC_BAD_VAR.finditer(body):
            out.append(error("survey_grammar",
                             "<exec> assigns to %r" % match.group(1),
                             'Compile error: "%s" is an invalid variable name '
                             'because it starts with "_".' % match.group(1)))
    if re.search(r"<row\b[^>]*\b[a-z0-9_]+:[a-z0-9_]+\s*=", text, re.I):
        out.append(error("survey_grammar",
                         "a <row> carries a namespaced attribute",
                         "Compile error: Style attribute is unknown. Stylevars "
                         "are question-scoped; per-row data goes in row text."))
    return out


def demo_requires(ctx):
    """dq:requires declarations must be satisfied by the demo itself."""
    out = []
    text = ctx.text.get("survey.xml")
    if not text:
        return out
    root = ctx.xml.get("survey.xml")
    survey_attrs = dict(root.attrib) if root is not None else {}
    static = ctx.dir / "static"
    have_static = {p.name for p in static.iterdir()} if static.is_dir() else set()

    for req in parse_requires(text):
        kind, rest = req["kind"], req["rest"]
        if kind == "survey-attr":
            parts = rest.split(None, 2)
            if len(parts) < 2:
                out.append(error("demo_requires",
                                 "malformed dq:requires survey-attr %r" % rest))
                continue
            attr = parts[0]
            found = None
            for key, value in survey_attrs.items():
                if key.split("}")[-1] == attr.split(":")[-1]:
                    found = value
            if found is None:
                out.append(error("demo_requires",
                                 "dq:requires survey-attr %s, but the demo's own "
                                 "<survey> tag does not set it" % attr,
                                 "The adopting survey will fail on an undefined "
                                 "variable, and IMPORT.md would be telling them "
                                 "something untested."))
            elif len(parts) == 3 and parts[1] == "contains" \
                    and parts[2] not in found:
                out.append(error("demo_requires",
                                 "dq:requires survey-attr %s contains %r, but the "
                                 "demo has %r" % (attr, parts[2], found)))
        elif kind == "static-asset":
            if rest not in have_static:
                out.append(error("demo_requires",
                                 "dq:requires static-asset %r, absent from static/"
                                 % rest,
                                 "The demo renders a broken asset."))
        else:
            out.append(error("demo_requires",
                             "unknown dq:requires kind %r" % kind))
    return out


def demo_assets(ctx):
    """Assets a demo row names must exist in the package."""
    out = []
    text = ctx.text.get("survey.xml")
    if not text:
        return out
    static = ctx.dir / "static"
    have = {p.name for p in static.iterdir()} if static.is_dir() else set()
    named = set(re.findall(r"[\w.-]+\.(?:png|jpe?g|gif|webp|svg|avif)", text,
                           re.I))
    for asset in sorted(named):
        if asset in have:
            continue
        out.append(error("demo_assets",
                         "the demo names %r but static/ does not contain it"
                         % asset,
                         "Renders a broken image. One package shipped a demo "
                         "naming four PNGs it did not ship."))
    return out


def row_labels(ctx):
    """Classify each question's row-label form; never let it be assumed.

    The distinction is not the first digit and not merely differing widths:
    r1..r30 legitimately has widths 1 and 2. A set is PADDED when every numeric
    suffix has the same width and at least one value would be shorter unpadded
    (e001..e300). Otherwise it is plain.

    The finding that matters is a survey using BOTH forms, because addressing
    one with the other's form raises AttributeError: Label e1 not found -- which
    happened twice in the same file.
    """
    out = []
    text = ctx.text.get("survey.xml")
    if not text:
        return out
    forms = {}
    for match in re.finditer(
            r'<(text|number|radio|checkbox|select)\b[^>]*label="([A-Za-z0-9_]+)"'
            r'[^>]*>(.*?)</\1>', text, re.S):
        label, body = match.group(2), match.group(3)
        rows = re.findall(r'<row\s+label="([^"]+)"', body)
        if len(rows) < 2:
            continue
        widths, values = set(), []
        parsed = True
        for row in rows:
            piece = re.fullmatch(r"[a-zA-Z_]*(\d+)", row)
            if not piece:
                parsed = False
                break
            widths.add(len(piece.group(1)))
            values.append(int(piece.group(1)))
        if not parsed or not values:
            continue
        if len(widths) == 1:
            width = widths.pop()
            padded = width > 1 and min(values) < 10 ** (width - 1)
            forms[label] = "padded" if padded else "plain"
        else:
            forms[label] = "plain"

    ctx.row_label_forms = forms
    if len(set(forms.values())) > 1:
        padded = sorted(k for k, v in forms.items() if v == "padded")
        plain = sorted(k for k, v in forms.items() if v == "plain")
        out.append(warn("row_labels",
                        "this survey uses both padded (%s) and unpadded (%s) "
                        "row-label forms"
                        % (", ".join(padded[:3]),
                           ", ".join(plain[:3]) +
                           (" ..." if len(plain) > 3 else "")),
                        "Record the form per field in spec.json and address it "
                        "from Python accordingly. Assuming one form raised "
                        "AttributeError: Label e1 not found."))
    return out


CHECKS = [demo_fences, demo_uses, demo_attrs, survey_grammar, demo_requires,
          demo_assets, row_labels]
