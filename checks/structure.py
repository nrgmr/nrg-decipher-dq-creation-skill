"""Package shape, XML validity, includes."""

import re

from .common import ERROR, error, warn, local, wrap_fragment

REQUIRED = ("meta.xml", "styles.xml", "survey.xml", "spec.json")
META_TAGS = ("scope", "title", "compat", "owner", "state", "builder", "description")
STATES = ("dev", "testing", "live", "closed")
FORBIDDEN_NAMES = ("uids.bin", "original.bin", ".teststatus.pickle",
                   ".whiteboard.pickle", "progress.bin", "command.log",
                   "survey.log", "debug.log")


def required_files(ctx):
    out = []
    for name in REQUIRED:
        if name not in ctx.text:
            out.append(error("required_files", "missing %s" % name,
                             "A package without it is not adoptable."))
    if not (ctx.dir / "static").is_dir():
        out.append(error("required_files", "missing static/ directory"))
    return out


def identity(ctx):
    out = []
    if ctx.name is None or ctx.version is None:
        out.append(error("identity",
                         "package directory is not <name>/v<N>: %s" % ctx.dir,
                         "Decipher resolves a DQ by that path shape."))
        return out
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,62}", ctx.name):
        out.append(error("identity", "DQ name %r is not lowercase snake_case"
                         % ctx.name))
    return out


def xml_wellformed(ctx):
    out = []
    for rel, message in ctx.errors_reading:
        out.append(error("xml_wellformed", "%s: %s" % (rel, message),
                         "The compiler stops here before reading anything else."))
    return out


def template_cdata(ctx):
    """The Builder <template> body must itself be parseable XML.

    An unparsed template can ship broken and only fail later, when a designer
    inserts the question in Builder.
    """
    from xml.etree import ElementTree
    out = []
    root = ctx.xml.get("meta.xml")
    if root is None:
        return out
    found = False
    for node in root:
        if local(node.tag) != "template":
            continue
        found = True
        body = (node.text or "").strip()
        if not body:
            out.append(error("template_cdata", "<template> is empty",
                             "Builder would insert nothing."))
            continue
        if "__" in body or "{{" in body:
            out.append(error("template_cdata",
                             "<template> still contains an unresolved token"))
        try:
            ElementTree.fromstring(wrap_fragment(body, (ctx.name,) if ctx.name
                                                 else ()))
        except ElementTree.ParseError as exc:
            out.append(error("template_cdata",
                             "<template> body is not well-formed XML: %s" % exc,
                             "A designer inserting the question gets broken XML."))
    if not found:
        out.append(warn("template_cdata", "meta.xml declares no <template>",
                        "Builder has nothing to insert; designers hand-write XML."))
    return out


def meta_contract(ctx):
    out = []
    root = ctx.xml.get("meta.xml")
    if root is None:
        return out
    if local(root.tag) != "meta":
        out.append(error("meta_contract", "meta.xml root is <%s>, expected <meta>"
                         % local(root.tag)))
        return out
    present = {local(n.tag): (n.text or "").strip() for n in root}
    for tag in META_TAGS:
        if tag not in present:
            out.append(warn("meta_contract", "meta.xml declares no <%s>" % tag,
                            "Declare the contract explicitly."))
    state = present.get("state", "")
    if state and state not in STATES:
        out.append(error("meta_contract", "<state>%s</state> is not one of %s"
                         % (state, ", ".join(STATES))))
    elif state and state != "dev":
        out.append(warn("meta_contract", "<state> is %r, not dev" % state,
                        "A human owns server state transitions."))
    count = None
    for node in root:
        if local(node.tag) == "count" and node.get("name") == "row":
            count = (node.text or "").strip()
    if count and count.endswith("+") and ctx.spec:
        per_row = [f for f in ctx.spec.get("capture", []) if f.get("rows")]
        if per_row:
            names = ", ".join(f.get("label", "?") for f in per_row)
            out.append(warn(
                "meta_contract",
                "<count name=\"row\"> is %r (open) but %s declares a fixed row "
                "count" % (count, names),
                "A designer who adds a row past the capture size gets a refusal "
                "at startup. Either bound the count or say so in IMPORT.md."))
    return out


def forbidden_files(ctx):
    out = []
    for path in ctx.dir.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ctx.dir).as_posix()
        if path.name in FORBIDDEN_NAMES or path.suffix in (".pickle", ".log"):
            out.append(error("forbidden_files",
                             "server-owned file in the package: %s" % rel,
                             "Uploading it overwrites the server's own state."))
        if path.name == "code.py":
            out.append(error("forbidden_files",
                             "code.py is Forsta-system-only", where=rel))
        if re.search(r"(test|spec)\.(js|py|html)$", path.name):
            out.append(error("forbidden_files",
                             "test file inside the upload unit: %s" % rel,
                             "Tests live outside the package."))
        if path.name == ".DS_Store":
            out.append(warn("forbidden_files", "stray %s" % rel))
    return out


def include_targets(ctx):
    """Every include must exist, and its case must match exactly.

    Path.is_file() is case-insensitive on an NTFS mount, so a wrong-case include
    passes locally and 404s on the server. Compare against the real directory
    listing instead.
    """
    out = []
    static = ctx.dir / "static"
    if not static.is_dir():
        return out
    real = {p.name for p in static.iterdir() if p.is_file()}
    for href in ctx.includes():
        if not href:
            out.append(error("include_targets", "<include> with empty href"))
            continue
        if href.startswith("/") or ".." in href:
            out.append(error("include_targets",
                             "include href must be package-relative: %s" % href))
            continue
        if href in real:
            continue
        lowered = {n.lower(): n for n in real}
        if href.lower() in lowered:
            out.append(error("include_case",
                             "include href %r does not match the file on disk, %r"
                             % (href, lowered[href.lower()]),
                             "Passes on a case-insensitive local mount; 404s on "
                             "the server."))
        else:
            out.append(error("include_targets",
                             "include href %r has no file in static/" % href))
    return out


def include_cost(ctx):
    out = []
    includes = ctx.includes()
    if len(includes) > 4:
        out.append(warn("include_cost",
                        "%d includes means %d render-blocking requests"
                        % (len(includes), len(includes)),
                        "There is no concatenation; each include is its own "
                        "request, paid per respondent per version."))
    static = ctx.dir / "static"
    if static.is_dir():
        referenced = set(includes)
        for path in sorted(static.iterdir()):
            if not path.is_file() or path.name in referenced:
                continue
            if path.suffix.lower() in (".js", ".css", ".less", ".json"):
                out.append(warn("include_cost",
                                "static/%s is referenced by no <include>"
                                % path.name,
                                "Unreferenced payload ships in every version."))
    return out


CHECKS = [required_files, identity, xml_wellformed, template_cdata,
          meta_contract, forbidden_files, include_targets, include_cost]
