# Package anatomy, naming and version isolation

## Layout

```text
<server_root>/<company>/lib/<name>/vN/
|-- meta.xml            applicability, state, Builder contract, the version
|-- styles.xml          stylevars, includes, style overrides
|-- survey.xml          the fenced demo. AUTHORED. The single source of truth
|-- spec.json           parameter classification and capture contract. AUTHORED
|-- capture_block.xml   GENERATED from survey.xml by `dq.py extract`
|-- IMPORT.md           GENERATED. The adopter's manual
|-- res.xml             optional, only for valid system-resource overrides
|-- CHANGELOG.txt       behaviour and provenance record
`-- static/             package-private JS, CSS, images, Builder icons
```

**OFFICIAL.** `meta.xml`, `styles.xml` and package-private static assets form the
normal DQ. An active `survey.xml` demo exercising options with `showSource="1"` is
recommended. `res.xml` is optional. `code.py` is limited to Forsta-created system
DQs — a company package must not contain one.

`CHANGELOG.txt`, `spec.json`, `IMPORT.md` and the demo fences are **CONVENTION**.
They are in the package because an operator needs version behaviour without access
to the conversation that produced it.

Generated files carry a do-not-edit header. `verify` fails if a generated file no
longer matches the region of `survey.xml` it came from.

## What must not ship

Tests, build scripts, fixture exports, internal notes. And never any
server-owned project file: `uids.bin`, `original.bin`, `.teststatus.pickle`,
`.whiteboard.pickle`, `*.log`, compiled CSS, caches. For a numeric survey release,
normally only the reviewed `survey.xml`.

## Static resolution

**TRAINING/OFFICIAL.** Files in `static/` are referenced from `styles.xml` by
package-relative filename — `<include href="widget.js"/>`. Decipher resolves the
DQ's static folder.

Two rules that bite:

- **Preserve exact filename case.** A wrong-case include 404s on the server and
  passes locally, because the usual Windows/NTFS mount is case-insensitive.
  `verify` checks case explicitly rather than relying on `is_file()`.
- **Never hardcode a numeric survey path or company URL.** A parameter default
  containing a survey id means every adopter of the package loads that asset from
  someone else's survey, and the value does not survive a survey copy. Per-survey
  values belong in the adopting survey, and `IMPORT.md` must say so.

Anything a demo row references must exist in the package's own `static/`. A demo
that names an image the package does not ship renders a broken image, and a
designer copying that demo inherits the fault.

**TRAINING.** Optional Survey Editor icons: `builder-pan-menu-<scope>.png` at
exactly 25x25, and `builder-tree-<scope>.png` at exactly 16x16. Other formats are
UNRESOLVED.

## Includes cost a request each

**VERIFIED-55C 2026-09-10.** There is no concatenation. Five includes are five HTTP
requests, in the order written, all render-blocking. Order is load order and is
expressed only by line position.

Consequences worth weighing before adding a file: a vendored third-party stylesheet
is paid for on every page view by every respondent, and paid for again in every
version, because packages are self-contained. Audit before you carry one forward.
It is common to find that a few rules of a large framework are actually used, that
all of them are already overridden locally, and that its relative font references
resolve to nothing.

## Version isolation

Each `vN` is complete. **Never** import JS or CSS from another version: closing or
deleting one version would break the other.

Namespace everything:

- stylevars as `<name>:<setting>`
- JavaScript under one versioned object, e.g. `window.YoutubePlayerV1`
- CSS below a host class, e.g. `.yp-v1-host`
- every DOM query below the adopting question's host element
- generated ids, storage keys and globals suffixed with the question label

Two instances of one DQ on a page must not share mutable state. Fixed ids and
globals are the reason they do. A package whose host id, global object and
generated field names are all fixed literals cannot be placed twice on one page;
the second instance silently drives the first.

## The demo is not compiled where it lives

**VERIFIED-55C 2026-09-10.** In this filesystem workflow `/lib/<name>/vN` is *not*
a standalone survey project and is not compiled there. The demo is compiled by
copying it into a fresh sibling **numeric** survey that references the DQ version.

That has a consequence worth stating plainly: the packaged demo gets **no compile
gate at all**. It is entirely possible for consecutive releases to ship a demo
that sets a parameter the package does not declare — in the very file adopters are
told to copy — and for nobody to notice, because only the numeric survey is ever
compiled.

`verify` compensates: it checks the demo's namespaced attributes against the
declared stylevar set, and every other structural property a compile would have
caught. That check is the reason the packaged demo can be trusted.
