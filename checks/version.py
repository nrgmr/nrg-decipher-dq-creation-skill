"""Version coherence: one declared version, no stale tokens."""

import re

from .common import error, warn, local

# Sites where a version legitimately appears, and the pattern that reads it.
FILENAME_VERSION = re.compile(r"_v(\d+)\b")


def declared_version(ctx):
    """meta.xml is the one place the version is declared."""
    out = []
    root = ctx.xml.get("meta.xml")
    if root is None:
        return out, None
    declared = None
    for node in root:
        if local(node.tag) == "version":
            declared = (node.text or "").strip()
    if declared is None:
        out.append(warn("version_declared",
                        "meta.xml declares no <version>",
                        "One declared version is what stops markers drifting. "
                        "The directory name is the fallback."))
        return out, ctx.version
    if not declared.isdigit():
        out.append(error("version_declared",
                         "meta.xml <version> is %r, not an integer" % declared))
        return out, ctx.version
    if ctx.version is not None and int(declared) != ctx.version:
        out.append(error("version_declared",
                         "meta.xml declares version %s but the directory is v%d"
                         % (declared, ctx.version)))
    return out, int(declared)


def version_coherence(ctx):
    """Every version-bearing site must agree with the declared version.

    A rename that matches version-shaped tokens misses bare numerals in fallback
    expressions. v8 of one package shipped with three separate sites still
    demanding 7 for exactly that reason, each found on a separate server round
    trip.
    """
    out, version = declared_version(ctx)
    if version is None:
        return out
    tag = "v%d" % version

    for rel in sorted(ctx.text):
        if not rel.startswith("static/"):
            continue
        for match in FILENAME_VERSION.finditer(rel):
            if int(match.group(1)) != version:
                out.append(error("version_coherence",
                                 "file %s carries version v%s, declared is %s"
                                 % (rel, match.group(1), tag)))

    for href in ctx.includes():
        for match in FILENAME_VERSION.finditer(href):
            if int(match.group(1)) != version:
                out.append(error("version_coherence",
                                 "include %r carries version v%s, declared is %s"
                                 % (href, match.group(1), tag)))

    if ctx.name:
        for rel, text in sorted(ctx.text.items()):
            for match in re.finditer(
                    r"%s\.(\d+)" % re.escape(ctx.name), text):
                if int(match.group(1)) == version:
                    continue
                line = text.count("\n", 0, match.start()) + 1
                out.append(error("version_coherence",
                                 "%s.%s referenced, declared is %s.%d"
                                 % (ctx.name, match.group(1), ctx.name, version),
                                 "Two versions of one DQ in a survey is fatal.",
                                 where="%s:%d" % (rel, line)))

    # Bare numerals in fallback expressions -- the class the token rename missed.
    for rel, text in sorted(ctx.text.items()):
        for match in re.finditer(r"or\s+'(\d+)'", text):
            value = int(match.group(1))
            if value in (0, 1) or value == version:
                continue
            line = text.count("\n", 0, match.start()) + 1
            out.append(warn("version_coherence",
                            "fallback %r looks like a version marker; declared "
                            "is %d" % (match.group(0), version),
                            "This exact form survived a v7 to v8 rename three "
                            "times.", where="%s:%d" % (rel, line)))
    return out


def stale_version_strings(ctx):
    """A prior version named in a respondent- or QA-facing string.

    The rename that creates a new version is exactly what leaves the previous
    number behind in a diagnostic string, which then sends QA to the wrong
    package.
    """
    out = []
    if ctx.version is None:
        return out
    others = [n for n in range(1, ctx.version + 12) if n != ctx.version]
    pattern = re.compile(r"\bv(%s)\b" % "|".join(str(n) for n in others))
    for rel, text in sorted(ctx.text.items()):
        if rel == "CHANGELOG.txt":
            continue
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            context = text[max(0, match.start() - 90):match.end() + 60]
            facing = bool(re.search(
                r"errors\.push|console\.|<title>|<desc|<note|alert\(|"
                r"textContent|innerHTML|Simulator|not configured", context))
            severity = error if facing else warn
            out.append(severity(
                "stale_version_strings",
                "mentions v%s; this package is v%d%s"
                % (match.group(1), ctx.version,
                   " (in a user-facing string)" if facing else ""),
                "A diagnostic naming the wrong version sends QA to the wrong "
                "package.", where="%s:%d" % (rel, line)))
    return out


def runtime_version_hardcoded(ctx):
    """Runtime files should read the version, not carry it."""
    out = []
    for rel, text in sorted(ctx.js_files().items()):
        for match in re.finditer(r"var\s+(VERSION|FEATURE_LEVEL)\s*=\s*(\d+)",
                                 text):
            line = text.count("\n", 0, match.start()) + 1
            out.append(warn("runtime_version_hardcoded",
                            "%s is hardcoded to %s in a runtime file"
                            % (match.group(1), match.group(2)),
                            "Emit it once from styles.xml so a bump touches one "
                            "site.", where="%s:%d" % (rel, line)))
    return out


CHECKS = [version_coherence, stale_version_strings, runtime_version_hardcoded]
