# Capture: getting data into the export

The highest-consequence subject in this skill. Everything else can be fixed in the
next version; data not recorded during fieldwork is gone.

## A DQ cannot declare survey variables

**VERIFIED-55C 2026-09-09.** A DQ package cannot create dataset variables in an
adopting survey. The variables must exist as real survey questions.

**VERIFIED-55C 2026-09-09.** Appending hidden `<input>` elements to the DOM does
**not** create exportable fields. The values are discarded on submit. Fabricating
hundreds of inputs for undeclared variables produces a DOM that looks perfect and
a dataset that stays empty.

**So: assert on exported data, never on the DOM.** A DOM-level check is precisely
how this failure produces a false pass: the page looks complete and the dataset is
empty. A `sessionStorage` mirror of the values is not a fix; it is a sign that
whoever wrote it did not trust the inputs either.

## The same-page rule

**VERIFIED-55C 2026-09-09.** A browser adapter can only write inputs that are
rendered. The DQ and every field it writes must be on the **same survey page**. No
`<suspend/>` or other page boundary between them.

Hide the fields with supported styles; do not remove them from rendering. Test the
generated HTML, not just XML adjacency.

## The capture block, and where it comes from

The adopting survey needs a block of variable declarations. In this skill that
block is **generated from the demo survey**, not maintained alongside it:

```xml
<!-- dq:block id="capture" action="copy-verbatim" title="Data capture. Never edit." -->
  ... declarations ...
<!-- dq:endblock -->
```

`dq.py extract` writes `capture_block.xml` from that region. `verify` fails if the
generated file and the region differ.

This exists because the alternative decays. Keeping a `capture_block.xml` and an
inlined copy in the demo, both hand-maintained, is stable only while somebody
remembers. In practice the two drift first in formatting — one copy re-indented,
rows packed differently — which floods `diff` with noise and destroys the cheapest
detector you have. Encoding drifts next, when one copy makes a server round trip
and the other does not. By the time the variable declarations themselves diverge,
nothing is watching.

## No hand-typed block version

**CONVENTION.** There is no
`capture_block_version` to maintain. Two mechanisms replace it, and the split
between them matters:

- **On disk, a content hash.** `dq.py extract` writes a hash of the block's own
  declarations into `capture_block.xml`, and `verify` fails if it no longer
  matches the demo region. That is what stops the generated fragment and its
  source diverging.
- **At runtime, structural verification.** The handshake below checks labels, row
  counts and writability. That is what actually catches a stale block: if a
  version changed the declarations, the shape differs and the handshake says so.
  If a version changed nothing structural, there is nothing to catch.

The hash is deliberately *not* sent to the browser. Computing it at runtime would
mean a second implementation that has to agree with the first, which is the class
of problem this whole convention exists to remove.

The alternative — a hand-typed version number — fails predictably. It ends up in
several places at once, and a rename that matches version-shaped tokens such as
`v7` misses bare numerals in fallback expressions such as `or '7'`. Each surviving
site is then discovered separately, on its own server round trip.

## The startup handshake

Before showing anything that looks like it is working, verify:

1. every required variable exists on this page;
2. each has at least the required number of rows;
3. a written value **round-trips** — write a sentinel, read it back, restore it.

On failure: do not start. Show the missing variable names and the required XML
under QA, and fail to a survey-owned error route when live.

Step 3 is not optional, and its sentinel matters. **VERIFIED-55C 2026-09-09:** a
`<number>` question renders as `input type="number"`, which **silently discards** a
non-numeric value written by JavaScript. A probe using a non-numeric sentinel
therefore reports a writable field as broken — or worse, a broken field as
writable. Use a numeric sentinel, or capture as `text`.

**Prefer `text` over `number`** whenever exact delimiters, leading zeroes, epoch
strings or sentinel formats must survive. Numeric coercion is a silent data
transform.

Every variable the runtime writes must also appear in the adapter's probe list. A
variable missing from that list is never verified and can fail silently — which is
exactly what the handshake exists to prevent. `verify` cross-checks `spec.json`,
the demo declarations and the probe list.

## Designing the fields

- Declare per field: label, Decipher type, row count, **exact row-label form**,
  serialised format, empty behaviour, sentinel, units and time origin, maximum
  length.
- Include the identity needed to interpret an array — position **and** item ID, not
  a UI index. A position-indexed array assumes the declared rows, the returned
  items and the capture rows are the same length *and* order; an async catalogue
  call legitimately returns fewer items when something is unpublished, expired or
  geo-restricted.
- Capture **before** navigation, and make duplicate event handling idempotent.
- Persist anything needed to survive refresh or resume in real capture variables.
  State kept only in memory changes assignment on refresh.
- Make overflow explicit: a capacity, a count, and an overflow flag.
- Keep any QA review screen default-off, enabled by a documented setting, and
  escape everything it displays. A debug screen with a "remove before go-live"
  comment on it will reach production; make it impossible instead of intended.

## Row-label forms

**VERIFIED-55C 2026-09-10.** Padding is not consistent. `r1..r30` in one question,
`e001..e300` in another, in the same survey. Addressing the wrong form from Python
raises `AttributeError: Label e1 not found in question <X>`. Record the form per
field in `spec.json` and let `verify` confirm the demo matches. Reading the labels
costs nothing; assuming them costs a round trip.

## Acceptance

A capture contract is proven when a respondent has gone through a numeric survey in
`testing` state and the **exported data** matches expectation, field by field,
including empty and sentinel cases and a refresh. Values embedding timestamps
cannot be byte-compared: normalise both sides identically, and state the origin —
wall clock, seconds since load, or player time — because changing it breaks
downstream analysis even when the shape matches.
