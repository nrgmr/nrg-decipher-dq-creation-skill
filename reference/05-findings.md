# Findings register

Last reviewed 2026-09-10. Context: Decipher TEST company 55c, survey compat
observed around 155. Revalidate after a material platform or compiler change.

Every claim in `reference/` carries an evidence label. This file is where the
labels are justified. **Check here before asserting a platform behaviour.**

A finding needs a **check** in `checks/` and a fixture in `tests/invalid/`, or it
will recur. The `Check` column names it; `—` means nothing automated catches it and
the discipline is human.

## Documentary findings

| Finding | Evidence | Decision |
|---|---|---|
| DQ packages use `meta.xml`, `styles.xml`, static assets, optional `res.xml`; `code.py` is Forsta-system-only | OFFICIAL | Reject a company `code.py` |
| Company DQs live under `selfserve/<company>/lib/<name>/vN` | OFFICIAL | Hardcode only the 55c root |
| First style-name location wins; a missing `vN` there does not fall through | OFFICIAL | Diagnose location and version together |
| Two versions of one DQ in a survey is fatal | OFFICIAL | Migrate every `uses` and `builder:styleManagerName` together |
| An active package `survey.xml` with `showSource` examples is recommended | OFFICIAL | Keep a demo in every package |
| `styles.xml` top level is `stylevar`, `include`, `style`, `less` | OFFICIAL | Permit `less` behind a server compile gate |
| Static filenames are package-relative; Builder icon names and sizes are fixed | TRAINING | Validate name, dimension and case |
| DQ state values are `dev`, `testing`, `live`, `closed` | OFFICIAL | A human owns server transitions |

Documents checked in 2026: article 4409469898139 *How to Create a Dynamic Question*;
4409476992795 *DQ Style Configuration (meta.xml)*; 4409461393051 *DQ Styles
(styles.xml)*; 4409461374491 *XML Style System*; 4409476993691 *Dynamic Question
Versioning*; plus supplied training transcripts and `exampledq.zip`.

## Verified 55c findings

| Date | Finding | Failure text or symptom | Check |
|---|---|---|---|
| 2026-09-09 | Namespaced attributes are rejected on `<row>`; stylevars are question-scoped | `Style attribute <ns>:<name> is unknown` | `demo_attrs` |
| 2026-09-09 | `<block>` accepts no `title` attribute | `Extra unrecognized argument given: title` | `survey_grammar` |
| 2026-09-09 | `<exec>` variable names may not begin with `_` | `"_rec" is an invalid variable name because it starts with "_"` | `survey_grammar` |
| 2026-09-09 | A DQ cannot declare adopting-survey variables | Export empty, DOM correct | `capture_contract` |
| 2026-09-09 | Fabricated hidden DOM inputs are not dataset fields | Export empty, DOM correct | `capture_contract` |
| 2026-09-09 | Capture adapters can only write fields rendered on the same page | Export empty when a `<suspend/>` precedes the block | `capture_same_page` |
| 2026-09-09 | `<number>` renders `input type="number"` and silently discards a non-numeric write | `Capture variable is present but not writable` from a probe using a text sentinel | `capture_contract` |
| 2026-09-09 | A stylevar default of the literal `""` interpolates to four quote characters | `SyntaxError: Unexpected string` | `render_defaults` |
| 2026-09-09 | Text fields preserve delimiters, leading zeroes and sentinels; numeric coerces | Values altered in export | `capture_contract` |
| 2026-09-09 | `$(text)` in a `question.element` override yields the type string, not row text | Overlay shows the literal word `radio` | — |
| 2026-09-10 | `/lib/<dq>/vN` is not compiled as a standalone survey project | Packaged demo has no compile gate | `demo_attrs` |
| 2026-09-10 | Row labels are not consistently padded across questions | `AttributeError: Label e1 not found in question EVENT_LOG` | `row_labels` |
| 2026-09-10 | A version marker duplicated across sites drifts; token renames miss bare numerals in `or 'N'` | `Capture block version must be 7; found 8`, three separate sites | `version_coherence` |
| 2026-09-10 | `<include>` has no `cond`; a package ships every file to every respondent | 6.9 KB shipped to all respondents for a feature off by default | — |
| 2026-09-10 | Each `<include>` is a separate HTTP request; no concatenation | Five includes, five render-blocking requests | — |
| 2026-09-10 | The theme owns `.grid`, `.cell`, `.hidden`, `.modal`, `.close`; unscoped selectors reach hundreds of elements and `.eq(n)` mis-targets | Watermark showed nine tiles instead of three | `unscoped_selectors` |
| 2026-09-10 | Inherited `!important` plus ID selectors cannot be overridden by class selectors | Four consecutive specificity passes, two regressions | — |
| 2026-09-10 | `input:text` is a Sizzle extension and cannot use `querySelectorAll` | ~10,000 subtree traversals per respondent | `hot_selectors` |
| 2026-09-10 | `jQuery.getScript` forces `cache: false` and is invisible to the preload scanner | Third-party bundle re-downloaded every page view | `script_loader` |
| 2026-09-10 | Unmuted autoplay is blocked without a gesture; a swallowed rejection is invisible in the export | Frozen first frame, nothing logged, nothing captured | `swallowed_rejection` |
| 2026-09-10 | A Decipher round-trip strips `<![CDATA[]]>` from `<note>` and re-escapes `&` | In-survey documentation degrades each cycle | — |
| 2026-09-10 | A wrong-case `include href` passes on a case-insensitive local mount and 404s on the server | Include 404 | `include_case` |
| 2026-09-10 | A packaged demo can reference an undeclared namespaced attribute for three consecutive releases | an undeclared parameter in three consecutive shipped demos | `demo_attrs` |

## Unresolved

Never promote one of these to fact without an experiment.

- **UNRESOLVED:** current 55c compiler and Builder behaviour for every documented
  stylevar type and for `<less>`. Use a disposable package spike.
- **UNRESOLVED:** exact Builder id and normalisation rewrites across save paths.
  Compare a pre/post redownload and add only normalisers you understand.
- **UNRESOLVED:** whether `[rel <file>]` resolves from inside a DQ style block, which
  is what conditional loading of a package script would need.
- **UNRESOLVED:** whether `builder:styleManagerName` is required. Documented, and
  present in zero real packages here.
- **UNRESOLVED:** whether `\@if` can wrap an `<include>`, the other candidate for
  conditional loading.
- **UNRESOLVED:** state-transition side effects for package demos versus numeric
  surveys beyond the observed testing and export behaviour.
- **UNRESOLVED:** approved removal behaviour for closed unused company DQs. Keep
  deletion human-approved and dependency-blocked.
- **UNRESOLVED:** whether two player instances inflate a vendor's own view counts.
  Confirm with the account owner before fielding.

## Corrections to an earlier knowledge base

Recorded because a wrong entry is worse than a missing one, and both of these
pointed diagnosis at the wrong layer.

- Unknown `res.xml` resource names were classified as "a compile-gate issue, not a
  browser-test issue". Observed: a Python **`KeyError` at runtime**. See
  [02-designer-surface.md](02-designer-surface.md).
- The `meta.xml` example showed `r1`/`r2` row labels with no caveat, reinforcing
  exactly the assumption that produced `Label e1 not found`. Row-label form must be
  read, never assumed.

## Adding a finding

Record the date, the fixture that reproduces it, the exact compiler or runtime
text, the affected `compat`, whether it supersedes an older entry, and the check
you added. One project incident is not a universal rule until it is reproduced or
documented — but it is enough to justify a check.
