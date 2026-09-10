---
name: decipher-dq
description: Design, build, verify and hand off Forsta Decipher Dynamic Questions in a test company. Use when asked to create a new reusable question type ("a DQ that looks like a YouTube player"), to iterate an existing DQ version, or to prepare a DQ package and its boilerplate survey for upload. Not for ordinary survey programming and never for a production company.
metadata:
  short-description: Decipher DQ prototyping, from a client sentence to an upload-ready package
---

# Decipher DQ

A Dynamic Question is a reusable question type: an XML style package under
`<server_root>/<company>/lib/<name>/vN/` that a survey adopts with
`uses="<name>.<N>"`. Survey Designers configure it with parameters and row text.
They must never have to open a file in `lib/`.

You cannot upload, compile, clone or run anything. A human does that. Your job is
to produce a package that survives first contact with the server, and to ask for
each human action in a form that cannot be misread.

## Environment

Read `config.json` at the skill root before emitting any path, URL or company
code. It holds the Decipher host, the server root, the test company, the
companies that are forbidden, and the local working root. Nothing else in this
skill hardcodes them, and neither should you. If a value there is still the
placeholder `<your-decipher-host>`, ask for it once rather than guessing —
a guessed hostname is a wasted round trip.

## Invariants

- The configured **test company only**. Refuse every company listed in
  `forbidden_companies`, and refuse any path naming a production tree.
- Never upload, compile, clone, change survey state, export or delete. Emit the
  exact request with `dq.py handoff` and stop for the result.
- A `vN` that has been uploaded is immutable. Corrections go in `vN+1`.
- Never edit anything under `incoming/`. It is untouched server evidence.
- Data lives or dies in the **export**. A correct DOM proves nothing.
- Local-green is not server-accepted. Say which you have.
- No explanatory comments in package runtime files; reasoning goes in
  `CHANGELOG.txt`.

## The loop

Six steps. Do not skip 1 or 4.

**1. Translate.** A request like "a DQ that looks like a YouTube player" does not
determine the things that matter. Pick an archetype, then ask its questions —
`archetypes/<name>/archetype.json` holds them, so the interview is data, not
improvisation. Write `spec.json`. It declares every parameter as
`public-required`, `public-optional` or `internal`, and every capture field.
Read [reference/02-designer-surface.md](reference/02-designer-surface.md) first.

**2. Scaffold.** `dq.py new --archetype <a> --spec spec.json --into <dir>`. What
comes out already has a fenced demo survey, a capture field with its startup
handshake, an invalid-configuration fixture and a two-instance question, because
those are the four things that otherwise fail first on the server.

**3. Build.** Write the logic. Consult `reference/` by topic, not end to end.
Before asserting any platform behaviour, check
[reference/05-findings.md](reference/05-findings.md) for its evidence class.

**4. Verify.** `dq.py verify <package>` until clean. Every check exists because a
real package reached the server broken. `dq.py extract` regenerates
`capture_block.xml` and `IMPORT.md` from the demo; never hand-edit those.

**5. Hand off.** `dq.py handoff <action>` — one action, exact paths, and the
artifact you need back. See [reference/07-handoff.md](reference/07-handoff.md).

**6. Record.** A `CHANGELOG.txt` entry: what changed, why, what is verified and
what is not. Then stop and say which evidence you actually have.

## Routing

| Need | Read |
|---|---|
| Which syntax is legal in which layer | [reference/00-platform.md](reference/00-platform.md) |
| Package layout, naming, version isolation | [reference/01-package.md](reference/01-package.md) |
| Parameters, Builder, what a designer may be asked to do | [reference/02-designer-surface.md](reference/02-designer-surface.md) |
| Capturing data so it reaches the export | [reference/03-capture.md](reference/03-capture.md) |
| CSS cascade, selectors, loaders, media policy | [reference/04-client-runtime.md](reference/04-client-runtime.md) |
| Whether a claim is proven | [reference/05-findings.md](reference/05-findings.md) |
| What a check proves, and what it cannot | [reference/06-verify.md](reference/06-verify.md) |
| Asking the human for something | [reference/07-handoff.md](reference/07-handoff.md) |
| Several developers on one library | [reference/08-collaboration.md](reference/08-collaboration.md) |

## Tools

`python scripts/dq.py <command> --help`

| Command | Does |
|---|---|
| `new` | Scaffold a package from an archetype and a spec |
| `verify` | Run every local check. The centre of gravity |
| `extract` | Regenerate `capture_block.xml` and `IMPORT.md` from the fenced demo |
| `bump` | Fork `vN` to `vN+1`, rewriting only enumerated version sites |
| `handoff` | Emit one exact human action |
| `scan` | Find which local surveys reference a DQ version |

`verify` exits non-zero on any error. Do not proceed past it and do not silence a
check. If a check is wrong, fix the check and add a test in `tests/test_verify.py`
that breaks exactly that one thing -- a check with no test can be disabled by a
refactor without anyone noticing.

## Version discipline

One declared version, in `meta.xml`. Runtime files never hardcode it — `styles.xml`
emits it as a single constant, and `dq.py bump` rewrites only anchored, enumerated
sites and lists anything ambiguous rather than guessing.

There is no hand-typed capture-block version. On disk, `capture_block.xml` records
a hash of its own declarations and `verify` fails if it drifts from the demo. At
runtime, the startup handshake checks structure, which is what actually catches a
stale block. Nothing to forget to bump.

A `vN` directory is a completed, verified increment, not a save point. Iterate
freely inside a version while it is `state=dev`; cut the next version when the
increment is done. The failure mode to avoid is a library of near-identical
megabyte version trees whose entire recorded evolution is one small edit and its
reversion.

## Reporting

At every pause, state: what changed, what `verify` proved, what it could not, the
next single human action, and the rollback. Keep verified facts and assumptions
apart. If you did not run a check, do not imply you did.
