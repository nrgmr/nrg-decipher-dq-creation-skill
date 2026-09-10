"""stylevars, the parameter classification, and the render harness."""

import re

from .common import (error, warn, local, render_styles, js_balance,
                     css_balance, extract_blocks)

TOP_LEVEL = ("stylevar", "include", "style", "less")
CLASSES = ("public-required", "public-optional", "internal")
TYPES = ("string", "int", "bool", "enum", "color", "res")


def styles_top_level(ctx):
    out = []
    root = ctx.xml.get("styles.xml")
    if root is None:
        return out
    if local(root.tag) != "styles":
        out.append(error("styles_top_level",
                         "styles.xml root is <%s>, expected <styles>"
                         % local(root.tag)))
        return out
    for node in root:
        tag = local(node.tag)
        if tag not in TOP_LEVEL:
            out.append(error("styles_top_level",
                             "<%s> is not permitted at the styles.xml top level"
                             % tag,
                             "Only stylevar, include, style and less are."))
        if tag == "less":
            out.append(warn("styles_top_level",
                            "<less> is unproven on this platform version",
                            "Needs a compile on your own platform version "
                            "before it can be relied on."))
    return out


def stylevar_shape(ctx):
    out = []
    root = ctx.xml.get("styles.xml")
    if root is None or ctx.name is None:
        return out
    seen = set()
    for node in root:
        if local(node.tag) != "stylevar":
            continue
        full = node.get("name") or ""
        if not full.startswith(ctx.name + ":"):
            out.append(error("stylevar_shape",
                             "stylevar %r is not namespaced %s:" % (full, ctx.name),
                             "An un-namespaced stylevar collides with other DQs."))
        if full in seen:
            out.append(error("stylevar_shape", "stylevar %r declared twice" % full))
        seen.add(full)
        kind = node.get("type") or ""
        if not kind:
            out.append(error("stylevar_shape", "stylevar %r has no type" % full))
        elif kind not in TYPES:
            out.append(warn("stylevar_shape",
                            "stylevar %r has undocumented type %r" % (full, kind)))
        if kind == "enum" and not node.get("values"):
            out.append(error("stylevar_shape",
                             "enum stylevar %r declares no values" % full))
        if not node.get("title") or not node.get("desc"):
            out.append(warn("stylevar_shape",
                            "stylevar %r lacks title or desc" % full,
                            "These are what a designer reads in Builder."))
        default = (node.text or "")
        if default.strip() == '""':
            out.append(error("stylevar_default_quotes",
                             "stylevar %r default is the literal two-character "
                             'string "" ' % full,
                             'Interpolates to four quote characters: '
                             "SyntaxError: Unexpected string."))
    return out


def stylevar_classification(ctx):
    """Every stylevar must be classified in spec.json.

    Without this the designer surface degrades: one survey here sets 48
    namespaced attributes of which 40 merely restate the package default, and
    37 of 99 stylevars are private capture indirections shown to the designer
    in the same flat list as a colour.
    """
    out = []
    if ctx.spec is None:
        return out
    declared = set(ctx.stylevars())
    classified = {}
    for entry in ctx.spec.get("parameters", []):
        name = entry.get("name", "")
        klass = entry.get("class", "")
        classified[name] = klass
        if klass not in CLASSES:
            out.append(error("stylevar_classification",
                             "parameter %r has class %r; expected one of %s"
                             % (name, klass, ", ".join(CLASSES))))
    for name in sorted(declared - set(classified)):
        out.append(error("stylevar_classification",
                         "stylevar %r is declared but not classified in spec.json"
                         % name,
                         "IMPORT.md is generated from the classification, so an "
                         "unclassified parameter is invisible to designers."))
    for name in sorted(set(classified) - declared):
        out.append(error("stylevar_classification",
                         "spec.json classifies %r but styles.xml does not declare it"
                         % name))
    return out


def stylevar_reachability(ctx):
    """Declared but never read, or read but never emitted."""
    out = []
    declared = ctx.stylevars()
    if not declared:
        return out
    styles_text = ctx.text.get("styles.xml", "")
    read_in_template = set(
        re.findall(r"this\.styles\.[a-z0-9_]+\.([a-z0-9_]+)", styles_text))
    for name, info in sorted(declared.items()):
        if name in read_in_template:
            continue
        capture_ish = name.startswith("capture_")
        if capture_ish:
            continue
        out.append(warn("stylevar_reachability",
                        "stylevar %r is declared but never read in styles.xml"
                        % name,
                        "A dead parameter is a promise the package does not keep."))
    for name in sorted(read_in_template - set(declared)):
        out.append(error("stylevar_reachability",
                         "styles.xml reads %r but no stylevar declares it" % name,
                         "Renders empty, silently."))

    # params emitted to JavaScript versus params the JavaScript reads
    emitted = set()
    for body in extract_blocks(styles_text, "question.after"):
        # Only the params object literal, so CSS declarations inside the same
        # block are not mistaken for emitted keys.
        for obj in re.finditer(r"params\s*=\s*\{(.*?)\n\s*\}", body, re.S):
            emitted |= set(re.findall(r"^\s*([A-Za-z][A-Za-z0-9_]*)\s*:",
                                      obj.group(1), re.M))
    consumed = set()
    assigned = set()
    for text in ctx.js_files().values():
        consumed |= set(re.findall(r"params\.([A-Za-z][A-Za-z0-9_]*)", text))
        consumed |= set(re.findall(r"this\.params\.([A-Za-z][A-Za-z0-9_]*)", text))
        # A key the runtime sets on the params object itself is not a missing
        # emission; the adapter owns it.
        assigned |= set(re.findall(
            r"params\.([A-Za-z][A-Za-z0-9_]*)\s*=[^=]", text))
        assigned |= set(re.findall(
            r"params\[\s*['\"]([A-Za-z][A-Za-z0-9_]*)['\"]\s*\]\s*=[^=]", text))
    consumed -= assigned
    for name in sorted(consumed - emitted):
        out.append(error("stylevar_reachability",
                         "JavaScript reads params.%s but styles.xml emits no such key"
                         % name,
                         "Reads undefined at runtime."))
    for name in sorted(emitted - consumed):
        out.append(warn("stylevar_reachability",
                        "styles.xml emits params.%s but no JavaScript reads it"
                        % name))
    return out


def render_defaults(ctx):
    """Render styles.xml with every default and check the result.

    This is the harness that catches an interpolation fault before a browser
    does, and it is the reason a bad default cannot reach the server twice.
    """
    out = []
    text = ctx.text.get("styles.xml")
    if not text:
        return out
    rendered = render_styles(text, ctx.stylevars())

    if '""""' in rendered:
        out.append(error("render_defaults",
                         "rendered template contains four consecutive quotes",
                         "SyntaxError: Unexpected string."))
    leftover = re.findall(r"\$\{[^}]*\}", rendered)
    unresolved = [x for x in leftover if "gv." not in x and " if " not in x]
    for item in sorted(set(unresolved)):
        out.append(error("render_defaults",
                         "unresolved interpolation after substitution: %s" % item))

    for body in re.findall(r'<style type="text/css">(.*?)</style>', rendered, re.S):
        opens, closes = body.count("{"), body.count("}")
        if opens != closes:
            out.append(error("render_defaults",
                             "rendered inline CSS brace imbalance %d/%d"
                             % (opens, closes)))
        for match in re.finditer(r"(--[a-z-]+|background|color)\s*:\s*;", body):
            out.append(error("render_defaults",
                             "rendered CSS has an empty value: %s"
                             % match.group(0).strip(),
                             "A blank stylevar became a blank declaration."))
        for match in re.finditer(r":\s*px\b", body):
            out.append(error("render_defaults",
                             "rendered CSS has a bare px unit with no number",
                             "A blank numeric stylevar."))

    for body in re.findall(r'<script type="text/javascript">(.*?)</script>',
                           rendered, re.S):
        for line, message in js_balance(body):
            out.append(error("render_defaults",
                             "rendered inline script: %s (line %d of the block)"
                             % (message, line)))
    return out


def asset_syntax(ctx):
    out = []
    for rel, text in sorted(ctx.js_files().items()):
        for line, message in js_balance(text):
            out.append(error("js_balance", message, where="%s:%d" % (rel, line)))
    for rel, text in sorted(ctx.css_files().items()):
        for _, message in css_balance(text):
            out.append(error("css_balance", message, where=rel))
    return out


CHECKS = [styles_top_level, stylevar_shape, stylevar_classification,
          stylevar_reachability, render_defaults, asset_syntax]
