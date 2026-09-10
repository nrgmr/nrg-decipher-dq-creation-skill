"""The verify suite.

Every check here exists because a real package reached the server broken. The
`prevents` field on a Finding names the failure, so a report explains itself
without anyone reading this file.

Checks are grouped into topical modules. Each check is an individually named
function returning a list of Findings; the grouping is for maintenance only.
"""

from . import capture, demo, runtime, structure, styles, version
from .common import Ctx, ERROR, WARN, Finding, error, warn

MODULES = (structure, styles, demo, capture, runtime, version)


def all_checks():
    out = []
    for module in MODULES:
        for func in module.CHECKS:
            out.append((module.__name__.rsplit(".", 1)[-1], func))
    return out


def run(package, only=None, skip=()):
    """Run every check against a package directory.

    Returns (ctx, findings). A findings list containing no ERROR is a pass.
    """
    ctx = Ctx(package)
    findings = []
    for group, func in all_checks():
        name = func.__name__
        if only and name not in only and group not in only:
            continue
        if name in skip or group in skip:
            continue
        try:
            findings.extend(func(ctx) or [])
        except Exception as exc:                                # noqa: BLE001
            findings.append(error(
                "check_crashed",
                "check %s.%s raised %s: %s"
                % (group, name, type(exc).__name__, exc),
                "A crashed check proves nothing. Fix the check."))
    return ctx, findings


def summarise(findings):
    errors = [f for f in findings if f.severity == ERROR]
    warnings = [f for f in findings if f.severity == WARN]
    return {"ok": not errors, "errors": len(errors), "warnings": len(warnings)}
