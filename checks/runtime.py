"""Client-runtime checks: selectors, loaders, media, isolation, origins."""

import re

from .common import config, error, warn, THEME_CLASSES

APPROVED_ORIGINS_DEFAULT = ("decipherinc.com", "w3.org")


def unscoped_selectors(ctx):
    """A jQuery selector on a theme class, with no host scope.

    The theme owns .grid, .cell, .hidden, .modal and .close. An unscoped
    selector reaches hundreds of unrelated elements, and .eq(n) on one addresses
    the wrong element entirely -- which is how a watermark ended up hiding a
    question row label instead of a tile.
    """
    out = []
    pattern = re.compile(r"""\$\(\s*(['"])\s*(\.[a-zA-Z][\w-]*)\s*\1\s*\)""")
    for rel, text in sorted(ctx.js_files().items()):
        for match in pattern.finditer(text):
            klass = match.group(2)[1:]
            if klass not in THEME_CLASSES:
                continue
            line = text.count("\n", 0, match.start()) + 1
            tail = text[match.end():match.end() + 60]
            severity = error if ".eq(" in tail or ".css(" in tail else warn
            note = ("index-based selection on a theme class addresses an "
                    "unrelated element" if ".eq(" in tail else
                    "writes inline styles to every matching element on the page")
            out.append(severity("unscoped_selectors",
                                "$('.%s') is not scoped to the DQ host; %s"
                                % (klass, note),
                                "Scope it: $(host).find('.%s')." % klass,
                                where="%s:%d" % (rel, line)))
    return out


def hot_selectors(ctx):
    out = []
    for rel, text in sorted(ctx.js_files().items()):
        for match in re.finditer(r"input:(text|checkbox|radio|submit)", text):
            line = text.count("\n", 0, match.start()) + 1
            out.append(warn("hot_selectors",
                            "%r is a Sizzle extension selector" % match.group(0),
                            "querySelectorAll throws on it, so it walks the "
                            'subtree in JavaScript. Use input[type="text"].',
                            where="%s:%d" % (rel, line)))
    return out


def script_loader(ctx):
    out = []
    for rel, text in sorted(ctx.js_files().items()):
        for match in re.finditer(r"\.getScript\s*\(", text):
            line = text.count("\n", 0, match.start()) + 1
            out.append(error("script_loader",
                             "jQuery.getScript forces cache: false",
                             "A third-party bundle is re-downloaded on every "
                             "page view, and XHR hides the URL from the preload "
                             "scanner. Use a <script> element plus a preload "
                             "hint.", where="%s:%d" % (rel, line)))
    return out


def swallowed_rejection(ctx):
    """An empty catch on a media play() promise hides a blocked autoplay."""
    out = []
    empty_catch = re.compile(r"\.catch\s*\(\s*function\s*\([^)]*\)\s*\{\s*\}\s*\)")
    for rel, text in sorted(ctx.js_files().items()):
        for match in empty_catch.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            window = text[max(0, match.start() - 300):match.end()]
            media = ".play()" in window or "play()" in window
            out.append((error if media else warn)(
                "swallowed_rejection",
                "empty catch discards a rejected promise",
                "Unmuted autoplay is blocked without a user gesture. A swallowed "
                "rejection is a frozen frame with nothing logged and nothing in "
                "the export.", where="%s:%d" % (rel, line)))
    return out


def unsafe_evaluation(ctx):
    out = []
    for rel, text in sorted(ctx.text.items()):
        for match in re.finditer(r"\beval\s*\(|new\s+Function\s*\(", text):
            line = text.count("\n", 0, match.start()) + 1
            severity = error if rel.endswith(".js") else warn
            out.append(severity("unsafe_evaluation",
                                "%s over designer input" % match.group(0).strip(),
                                "One package fell back to Function(...) over "
                                "configuration text, which is code execution "
                                "driven by a survey file.",
                                where="%s:%d" % (rel, line)))
    return out


def instance_isolation(ctx):
    """Fixed ids and globals collide when two instances share a page."""
    out = []
    for rel, text in sorted(ctx.js_files().items()):
        for match in re.finditer(
                r"getElementById\s*\(\s*['\"]([\w-]+)['\"]\s*\)", text):
            line = text.count("\n", 0, match.start()) + 1
            out.append(warn("instance_isolation",
                            "getElementById(%r) is a fixed, page-global id"
                            % match.group(1),
                            "Two instances of this DQ on one page collide. Query "
                            "below the host element and suffix generated ids with "
                            "the question label.",
                            where="%s:%d" % (rel, line)))
        for match in re.finditer(r"(?:sessionStorage|localStorage)\s*\.\s*"
                                 r"(?:set|get)Item\s*\(\s*['\"]([^'\"]+)['\"]",
                                 text):
            line = text.count("\n", 0, match.start()) + 1
            out.append(warn("instance_isolation",
                            "storage key %r is not instance-scoped"
                            % match.group(1),
                            "Suffix it with the question label. And never put a "
                            "respondent identifier in client storage.",
                            where="%s:%d" % (rel, line)))
    return out


def strict_mode(ctx):
    out = []
    for rel, text in sorted(ctx.js_files().items()):
        if '"use strict"' not in text and "'use strict'" not in text:
            out.append(warn("strict_mode", "no strict-mode directive", where=rel))
    return out


def external_origins(ctx):
    """Only allowlisted third-party origins, and no production company."""
    out = []
    approved = set(APPROVED_ORIGINS_DEFAULT)
    if ctx.spec:
        approved |= set(ctx.spec.get("approved_origins", []))
    for rel, text in sorted(ctx.text.items()):
        stripped = re.sub(r"/\*.*?\*/", "", text, flags=re.S) \
            if rel.endswith((".js", ".css")) else text
        for match in re.finditer(r"https?://([A-Za-z0-9.-]+)", stripped):
            host = match.group(1)
            if any(host == a or host.endswith("." + a) for a in approved):
                continue
            line = stripped.count("\n", 0, match.start()) + 1
            out.append(error("external_origins",
                             "unapproved external origin %s" % host,
                             "Add it to spec.json approved_origins only with a "
                             "reason. Do not guess a hostname.",
                             where="%s:%d" % (rel, line)))
        cfg = config()
        for bad in cfg["forbidden_companies"]:
            if bad in text:
                out.append(error("external_origins",
                                 "reference to a forbidden company: %r" % bad,
                                 "This skill targets the test company %s only."
                                 % cfg["test_company"], where=rel))
        for match in re.finditer(r"selfserve/%s/(\d{4,})"
                                 % re.escape(cfg["test_company"]), text):
            line = text.count("\n", 0, match.start()) + 1
            out.append(error("hardcoded_survey",
                             "hardcoded survey id %s in the package"
                             % match.group(1),
                             "Every adopter would load assets from that survey. "
                             "Per-survey values belong in the adopting survey.",
                             where="%s:%d" % (rel, line)))
    return out


def call_graph(ctx):
    """Every prototype method invoked must be defined somewhere in the package."""
    out = []
    defined, called = set(), {}
    for rel, text in sorted(ctx.js_files().items()):
        defined |= set(re.findall(r"(?:\w+)\.prototype\.(\w+)\s*=", text))
        defined |= set(re.findall(r"^\s*(\w+)\s*:\s*function", text, re.M))
        for match in re.finditer(r"(?:this|self)\.(\w+)\s*\(", text):
            called.setdefault(match.group(1),
                              "%s:%d" % (rel,
                                         text.count("\n", 0, match.start()) + 1))
    if not defined:
        return out
    for name, where in sorted(called.items()):
        if name not in defined:
            out.append(error("call_graph",
                             "this.%s() is called but never defined" % name,
                             "TypeError at runtime, on a path that may only run "
                             "for some respondents.", where=where))
    return out


CHECKS = [unscoped_selectors, hot_selectors, script_loader, swallowed_rejection,
          unsafe_evaluation, instance_isolation, strict_mode, external_origins,
          call_graph]
