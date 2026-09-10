# The Decipher dialect: which syntax is legal in which layer

Evidence labels used throughout `reference/`:

- **OFFICIAL** — stated in Forsta Surveys documentation, article IDs in
  [05-findings.md](05-findings.md).
- **TRAINING** — stated in the supplied Forsta DQ training material.
- **VERIFIED-55C** — observed through a compile or runtime experiment in 55c. The
  entry carries its date.
- **CONVENTION** — an engineering choice to reduce risk. Not a platform law.
- **UNRESOLVED** — plausible but unproven. Never promote it silently.

## How a DQ is resolved

**OFFICIAL.** A DQ is a centrally stored XML style package. An adopting question
calls it with `uses="<name>.<version>"`, for example `uses="rating.2"`. Company
packages live under `<server_root>/<company>/lib/<name>/vN/`, the two values coming
from `config.json`.

A note on the evidence labels: **VERIFIED-55C** entries were observed in a Decipher
test company whose code is `55c`. The company code is not the point — the observed
behaviour is. Your own company code will differ; set it in `config.json`.

**OFFICIAL.** Decipher resolves the first location containing the style *name*,
then looks for the requested *version* only there. A missing version does not fall
through to another location — so "version not found" and "wrong location" are one
diagnosis, not two.

**OFFICIAL.** Two versions of the same style in one survey is a fatal conflict.
When migrating, change every `uses=` and its matching `builder:styleManagerName`
in the same pass.

## Four layers, four syntaxes

The commonest authoring mistake is using one layer's syntax in another. They
execute at different times and do not interchange.

| Layer | Syntax | Runs |
|---|---|---|
| Python expression | `${...}` | Server, at survey render |
| Style flow control | escaped `\@if`, `\@else`, `\@endif`, `\@for`, `\@end` | Server, at style expansion |
| Style argument | `$(name)` | Server, from the surrounding style block |
| Inherited style | `[super]` | Server, inserts the platform style being replaced |

**VERIFIED-55C 2026-09-09.** Inside a `question.element` override, `$(text)`
resolves to the question **type string** — literally `radio` — not the row's text.
Row text must come from `${jsexport()}`. Observed row-object keys are `index`,
`rightLegend`, `uid`, `open`, `exclusive`, `text`, `label`, `openOptional`,
`amount`, `optional`. Treat anything beyond that list as UNRESOLVED.

## `styles.xml` top level

**OFFICIAL.** One `<styles>` root. Top-level children are `stylevar`, `include`,
`style` and `less`. Nothing else: no survey questions, no `<exec>`, no resources,
no arbitrary tags.

`less` is permitted but **UNRESOLVED** on this platform version until a 55c compile
proves it. `verify` warns rather than fails.

## Style overrides

`<style name="...">` **replaces** a platform style by default. `mode="before"` or
`mode="after"` extends it; `[super]` inserts the inherited style explicitly.
`cond`, `before`, `after`, `with`, `rows` and `cols` constrain application where
the target block supports them. `wrap="ready"` wraps JavaScript for jQuery-ready
execution. Labels can be reused with `copy` and `arg:*`.

**VERIFIED-55C 2026-09-10.** `<include>` has **no** `cond` facility. A survey-level
`<script>` block can be device- or feature-conditional; a DQ include cannot. A
package therefore ships every file to every respondent. If a subsystem is
feature-flagged and large, inject it from the boot script instead — and note that
`[rel ...]` resolution from inside a DQ style block is UNRESOLVED.

## Survey-side syntax a DQ has to generate or document

**VERIFIED-55C 2026-09-09.** `<block>` accepts **no** `title` attribute. Using one
fails compilation with `Extra unrecognized argument given: title`. Block titles go
in child content.

**VERIFIED-55C 2026-09-09.** Decipher rejects `<exec>` variable names beginning
with an underscore: `"_rec" is an invalid variable name because it starts with "_"`.

**VERIFIED-55C 2026-09-09.** Namespaced attributes cannot be set on a `<row>`.
Stylevars are question-scoped. Attempting a row-level one fails with
`Style attribute <ns>:<name> is unknown`. Per-row data must travel in delimited
**row text** — see [02-designer-surface.md](02-designer-surface.md) for the grammar
rules that keeps it survivable.

**VERIFIED-55C 2026-09-10.** Row labels are **not** consistently padded across
questions. One question may use `r1..r30` while a 300-row question uses
`e001..e300`. Addressing them from Python with the wrong form raises
`AttributeError: Label e1 not found in question <X>`. Read the actual labels; never
assume the form. `verify` records the form per question so the assumption is
visible.

## Escaping

- XML attributes escape `&`, `<`, `>` and quotes. Use CDATA for element content
  where the compiler supports it.
- Server-rendered values entering JavaScript use `${jsexport()}`, never quote
  concatenation.
- Runtime display uses `textContent`, or explicit HTML escaping.
- **VERIFIED-55C 2026-09-09.** A stylevar whose default is the literal two-character
  string `""` is interpolated verbatim, so the template emits four quote characters
  and the page dies with `SyntaxError: Unexpected string`. Make a genuinely empty
  default empty. `verify` renders the template with every default to catch this.
- **VERIFIED-55C 2026-09-10.** A Decipher round-trip strips `<![CDATA[]]>` from a
  `<note>` and re-escapes `&` to `&amp;`. Anything you write for a human to read
  inside a survey degrades slightly on every server cycle. Keep the authoritative
  copy in the package.

## Never

`eval`, `new Function`, or string-built code to parse designer input. Use a narrow
delimiter grammar with explicit duplicate, range, count and empty checks, and fail
closed with a scoped error. One package fell back to
`Function("return (" + text + ");")()` over configuration text; that is arbitrary
code execution driven by a survey file.
