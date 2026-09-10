# The designer surface

## The acceptance test

**Two Survey Designers who have not seen the package are given `IMPORT.md`, the
demo survey and a brief. Both reach a working question with correct data, unaided,
without opening any file under `lib/`.**

A designer who opens a `lib/` file is a failure of the parameter surface, not of
the designer. This is the criterion the whole surface is designed against, and it
is the one thing `verify` cannot check.

## Classify every parameter

`spec.json` assigns each stylevar exactly one class:

| Class | Meaning |
|---|---|
| `public-required` | The designer must set it. There is no sensible default |
| `public-optional` | Has a default that is correct for most studies |
| `internal` | Machinery. Never in `IMPORT.md`, never expected on the question |

`verify` fails if a stylevar is unclassified, and `IMPORT.md` is generated from the
classification. Without it the surface degrades in two predictable ways. Adopting
questions accumulate attributes that **merely restate the package default**, which
pins that survey to today's behaviour and silently defeats any default a future
version changes. And internal machinery — private capture-variable indirections,
for instance — ends up presented to the designer in the same flat list as
`progress_color`, so nobody can tell which attributes actually need setting.

Decipher's `<stylevar>` vocabulary is only `name`, `type`, `title`, `desc`,
`values` — there is no `required` attribute. `spec.json` is where the distinction
lives; the prose in `desc` is for the human reading Builder.

## Stylevars

**OFFICIAL.** Use `namespace:name`, the namespace being the DQ directory name.
Types documented: `string`, `int`, `bool`, `enum` (with comma-separated `values`),
`res`/translatable, `color`.

Give every one a useful default, a short `title`, and a `desc` that says what it
does and what happens at the extremes. A stylevar is **public API**: changing its
name, type, meaning or default in a deployed package needs a new `vN`.

Write `desc` for a non-programmer. Compare:

- Poor: `Advance delay in ms.`
- Good: `Milliseconds to wait after the last tap before advancing. The timer
  resets on each tap, so several interactions on one video are still captured.`

## Per-row data: the delimited row-text grammar

Row-level namespaced attributes are rejected by the compiler
([00-platform.md](00-platform.md)), so per-row data goes in row **text**. That is a
hand-authored grammar in a survey file, so it needs designing, not just splitting.

Rules learned from getting this wrong twice:

1. **Fixed field order, all fields after the key optional.**
   `role :: videoId :: title :: description :: picture`
2. **Do not let a field absorb the remaining separators.** It reads as generous —
   "the description may contain `::`" — and it means you can never add a field
   later without breaking every existing row. When a field was appended after such
   a description, a stray `::` silently became a filename and rendered a broken
   image.
3. **Validate the shape of every field, not just its presence.** A field that
   should be an image name is checked as one; anything else is a hard error naming
   the row. Convert silent misreads into loud refusals.
4. **Too many fields is an error, not a truncation.**
5. **Clean once.** Strip tags and decode entities at the row level, then only trim
   per field. Cleaning twice destroys data: a description containing `&lt;now&gt;`
   decoded to `<now>` on the first pass and was then stripped as a tag on the
   second.
6. **Tell the designer in `IMPORT.md`** that this is an XML file, so `&` must be
   written `&amp;`, and give a live example row.
7. **Key metadata to the item, not the slot**, if slots can be reordered or
   rotated. Otherwise editing one row silently shifts another's data.

## `meta.xml`

**OFFICIAL.** One `<meta>` root. Tags are technically optional; declare them
anyway.

| Tag | Use |
|---|---|
| `scope` | `global`, `question`, or question tags such as `radio,checkbox`. Narrowest true scope |
| `state` | `dev` while building. A human owns server transitions |
| `compat` | Minimum such as `155`, or a range `155-160`. Omission means broad, so test deliberately |
| `supports` | Tested special features only. Training shows `open`, `noanswer`, `fused` |
| `require name="..."` | Requires a question attribute |
| `count name="row\|col\|choice"` | Count contract. State the real range, not `30+` when the true range is 30-51 |
| `rename name="row"` | Changes Builder terminology, e.g. rows shown as "videos" |
| `modifies` | Affected structures for Builder handling |
| `owner` | Accountable address |

`count` and `rename` are free error-prevention: they constrain the designer in
Builder before any code runs.

**OFFICIAL.** Builder listing: `<builder/>` permits XML/Style Editor use without
pan-menu listing; `<builder>pan</builder>` lists it for users; `pan, staff` limits
it to staff; no tag hides it. A `missing` mode is documented — UNRESOLVED here.

`<template scope="...">` wraps working question XML in CDATA and is what Builder
inserts. It must be **functional**, with `label="{x}"`, a title, enough elements to
satisfy `count`, and the `uses` reference. No client content, no survey IDs, no
unresolved tokens.

`verify` parses the `<template>` CDATA, because an unparsed template ships broken
and fails only later, when a designer inserts the question in Builder.

Note: `builder:styleManagerName` appears in Forsta documentation but in no observed
working package. Set it if documentation calls for it, and treat it as UNRESOLVED.

## Respondent-visible strings

Every label, instruction, error, status, button and accessibility name needs a
localisation strategy:

- ordinary question/row/choice text, when it is survey content;
- a translatable stylevar, when a designer configures it;
- a proven `res.xml` system override, only when replacing a system message.

Never hide English in minified JavaScript or a CSS pseudo-element.

**VERIFIED-55C 2026-09-09.** A DQ's own `res.xml` **cannot introduce new resource
labels** — it can only override resources that already exist. Referencing a new
label raises a Python `KeyError` at **runtime**, not at compile time. Do not treat
it as a compile-gate issue; that sends diagnosis to the wrong layer.

The working pattern: put the string in a stylevar with an English default, and let
a study translate it by pointing that stylevar at its own survey `<res>` label.
