# What `verify` proves, and what it cannot

`python scripts/dq.py verify <package>` runs 37 checks in six groups. It exits
non-zero on any error. Run it until clean before asking a human for anything.

## What it cannot do

Two limits, stated first so the pass line is never over-read.

**It does not execute the DQ.** No JavaScript runs. No DOM is built. No
`jsexport` payload is fed through the real pipeline. A pass means the files are
structurally sound and the contracts agree with each other — not that the thing
works. Where a JavaScript runtime is available the archetype's own unit tests can
run over the parser and state machine; on a workstation with no `node` and no
Python JS binding the evidence is structural only, and `verify` says so in its
pass line.

**It does not imply server acceptance.** That needs a compile, a respondent, the
required devices, and exported data. `verify` is what stops you spending a human
round trip discovering something a regex could have told you.

## The groups

Run one group or one check with `--only`:
`dq.py verify <pkg> --only capture` or `--only demo_attrs`.

### structure — is this a package at all

| Check | Catches |
|---|---|
| `required_files` | A missing `meta.xml`, `styles.xml`, `survey.xml`, `spec.json` or `static/` |
| `identity` | A directory that is not `<name>/vN`, or a name that is not snake_case |
| `xml_wellformed` | Malformed XML, before the compiler gets a chance to say so less clearly |
| `template_cdata` | A Builder `<template>` whose body is not valid XML, which otherwise fails only when a designer inserts the question |
| `meta_contract` | Missing declarations; a bad `state`; an open `count` paired with a fixed capture row count, which means a designer who adds a row gets refused at startup |
| `forbidden_files` | Server-owned files (`uids.bin`, pickles, logs), `code.py`, test files inside the upload unit |
| `include_targets` | A missing include, and specifically a **wrong-case** one. A case-insensitive local mount hides this and the server 404s |
| `include_cost` | More than four includes, since each is its own render-blocking request; and unreferenced payload in `static/` |

### styles — the parameter surface

| Check | Catches |
|---|---|
| `styles_top_level` | A tag other than `stylevar`, `include`, `style`, `less`; and flags `less` as unproven |
| `stylevar_shape` | An un-namespaced or duplicate stylevar, a missing type, an `enum` with no values, a missing `title`/`desc` — and a default of the literal `""`, which interpolates to four quote characters and kills the page |
| `stylevar_classification` | A stylevar not classified in `spec.json`, or a classification with no stylevar. This is what makes `IMPORT.md` trustworthy |
| `stylevar_reachability` | A declared parameter nothing reads; a template reading an undeclared one; JavaScript reading a `params` key nothing emits. Keys the adapter assigns at runtime are excluded |
| `render_defaults` | The render harness. Substitutes every default into `styles.xml` and scans the result for quadruple quotes, unresolved interpolation, empty CSS values, bare `px`, and unbalanced inline script |
| `asset_syntax` | Bracket, string, regex and comment imbalance in JavaScript; brace imbalance in CSS |

### demo — the boilerplate, which has no compile gate

`/lib/<name>/vN` is never compiled as a survey, so the packaged demo gets no
compiler feedback at all. This group is its substitute.

| Check | Catches |
|---|---|
| `demo_fences` | Missing, unterminated, unnamed, duplicate or wrongly-actioned `dq:block` fences, and a demo with no `question` block |
| `demo_uses` | A demo that does not invoke the DQ, invokes the wrong version, invokes two versions, or omits `showSource="1"` |
| `demo_attrs` | **A namespaced attribute the package does not declare** — a compile error that the packaged demo would never surface on its own. Also flags internal parameters on the question, and a pile of attributes merely restating defaults |
| `survey_grammar` | `<block title=...>`, an `<exec>` variable starting with `_`, a namespaced attribute on a `<row>` — three compile errors, caught locally |
| `demo_requires` | A `dq:requires` the demo's own `<survey>` tag or `static/` does not satisfy, so `IMPORT.md` cannot promise something untested |
| `demo_assets` | An image the demo names but the package does not ship |
| `row_labels` | A survey mixing padded and unpadded row-label forms, which is what produced `AttributeError: Label e1 not found` |

### capture — the part that loses data

| Check | Catches |
|---|---|
| `capture_contract` | Disagreement between `spec.json`, the demo's declarations and the adapter's probe list; a wrong type or row count; a `<number>` field where text is needed; a missing `row_label_form`; and a missing startup handshake altogether |
| `capture_same_page` | A `<suspend/>` between the question and the capture block. Across a page boundary the screen looks right and the export is empty |
| `generated_sync` | A generated fragment that no longer matches the demo region it came from, or one with its do-not-edit header removed |
| `capture_hash_recorded` | A `capture_block.xml` whose recorded hash does not match its source region |

### runtime — the browser

| Check | Catches |
|---|---|
| `unscoped_selectors` | A jQuery selector on a theme class (`.grid`, `.cell`, `.hidden`, `.modal`, `.close`) with no host scope. Errors when followed by `.css()` or `.eq()`, which is how an overlay ends up styling unrelated page elements and addressing the wrong one |
| `hot_selectors` | `input:text` and friends — Sizzle extensions that cannot use `querySelectorAll` |
| `script_loader` | `jQuery.getScript`, which forces `cache: false` and hides the URL from the preload scanner |
| `swallowed_rejection` | An empty `catch` on a promise. Near a `play()` call this is a blocked autoplay that is invisible in the export |
| `unsafe_evaluation` | `eval` or `new Function` over designer input |
| `instance_isolation` | A fully literal `getElementById`, or a storage key with no instance suffix |
| `strict_mode` | A JavaScript file with no strict-mode directive |
| `external_origins` | An origin not in `spec.json` `approved_origins`; any `53b` reference; a hardcoded survey id in the package |
| `call_graph` | `this.foo()` called but never defined |

### version — one declared version

| Check | Catches |
|---|---|
| `version_coherence` | A filename, include, `uses=` reference or `or 'N'` fallback disagreeing with the declared version. The `or 'N'` form is the one a token rename misses |
| `stale_version_strings` | A prior version named in a string, escalated to an error when the string is respondent- or QA-facing. A diagnostic naming the wrong version sends QA to the wrong package |
| `runtime_version_hardcoded` | A `VERSION` constant baked into a runtime file rather than emitted once |

## Legacy packages

A demo authored before the fenced convention has no `dq:block` markers.
`verify` says so once and treats the fence checks as advisory, so an existing
library does not suddenly fail its gate. Everything else still applies.

## Calibration

Every check earns its place by firing on a failure that actually happened: an
undeclared parameter in a shipped demo, mixed row-label forms behind a runtime
`AttributeError`, a demo naming assets its package did not ship, a stale version
string in a respondent-facing diagnostic, unscoped selectors reaching the survey
theme, a cache-busting script loader, a swallowed autoplay rejection, a hardcoded
survey id.

That is the standard for adding one: it must fire on a real failure and stay quiet
on a correct package. Point `verify` at your own existing library and confirm it
reports what you already know is wrong there — see **Calibrating against your own
library** in the README. A check with no test in `tests/test_verify.py` is not
finished, and a suite that passes everything proves nothing.
