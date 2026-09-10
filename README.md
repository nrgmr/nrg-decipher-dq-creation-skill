<div align="center">

# `decipher-dq`

**From a sentence to an upload-ready Forsta Decipher Dynamic Question.**

Works in **Claude Code, the Claude app, OpenAI Codex and ChatGPT**. Turns *"build me
a question that behaves like a video feed"* into a complete, verified DQ package —
with a boilerplate survey that doubles as the Survey Designer's manual.

**[Set up in five minutes ↓](#set-up)**

`37 local checks` · `5 archetypes` · `7 commands` · `4 surfaces` · `zero dependencies`

</div>

---

## Contents

- [Set up](#set-up)
- [Without a terminal: what the conversation looks like](#without-a-terminal-what-the-conversation-looks-like)
- [What this is](#what-this-is)
- [Why it exists](#why-it-exists)
- [The developer workflow](#the-developer-workflow)
- [The loop](#the-loop)
- [What a scaffold contains](#what-a-scaffold-contains)
- [Archetypes](#archetypes)
- [Verification](#verification)
- [The designer surface](#the-designer-surface)
- [Versioning](#versioning)
- [The human boundary](#the-human-boundary)
- [Safety invariants](#safety-invariants)
- [Configuration reference](#configuration-reference)
- [Reference library](#reference-library)
- [Calibrating against your own library](#calibrating-against-your-own-library)
- [Repository layout](#repository-layout)
- [Development](#development)
- [Limits](#limits)

---

## Set up

Four surfaces, two vendors. **Nothing syncs between them** — set up each place you
want to use it. Everything the skill needs is Python 3.10+ and the standard library.

| Surface | For | Setup | You get back |
|---|---|---|---|
| **[A. Claude app](#a-claude-app-or-claudeai--no-terminal)** | Anyone. No terminal | Upload one `.zip` | A `.zip` to download |
| **[B. Claude Code](#b-claude-code)** | Developers | Clone one folder | Files in your project |
| **[C. Codex](#c-openai-codex)** | Developers | Clone, plus one `AGENTS.md` line | Files in your project |
| **[D. ChatGPT](#d-chatgpt-custom-gpt)** | Anyone. No terminal | Paste instructions, upload 3 files | A `.zip` to download |

---

### A. Claude app or claude.ai — no terminal

**1. Get `decipher-dq.zip`.** Ask whoever set this up, or build it:

```bash
python3 scripts/build_claude_zip.py     # writes dist/decipher-dq.zip
```

**2. Turn on code execution.** **Settings → Capabilities → code execution.** Nothing
works without it: the skill runs Python to verify what it builds.

**3. Add the skill.** **Settings → Capabilities → Skills**, press **+**, then
**Create skill**, and choose the zip.

**4. Start a new chat** and say what you want in plain language:

> *Create a Dynamic Question that shows nine product images and asks the respondent
> to pick their top three, in order.*

The skill loads itself, interviews you before writing anything, and finishes by
giving you a `.zip` to download. See
[what the conversation looks like](#without-a-terminal-what-the-conversation-looks-like).

---

### B. Claude Code

**1. Clone it.** The target directory must be named `decipher-dq`: the skill name
comes from the folder, not the repository, and the two differ here.

```bash
# personal — available in every project
git clone https://github.com/lyle-nrg/nrg-decipher-dq-creation-skill.git \
  ~/.claude/skills/decipher-dq

# or per project — checked in and shared with the team
git clone https://github.com/lyle-nrg/nrg-decipher-dq-creation-skill.git \
  .claude/skills/decipher-dq
```

**2. Confirm it works.**

```bash
cd ~/.claude/skills/decipher-dq
python3 scripts/dq.py --help
python3 tests/test_verify.py        # 61 tests, about 3 seconds
```

**3. Ask for a DQ** in natural language — *"create a DQ that works like an image
gallery"* — and the skill loads itself. Or drive the tooling directly; see
[the developer workflow](#the-developer-workflow).

---

### C. OpenAI Codex

Codex reads **`AGENTS.md`**, not `SKILL.md`. This repository ships one, generated
from `SKILL.md` so the two cannot drift, and a test asserts it stays in sync.

**Working inside this repository** — nothing to do. Codex loads `AGENTS.md`
automatically.

**Working in your own survey project**, pick one:

```bash
# 1. Clone it in, then point your project's AGENTS.md at it
git clone https://github.com/lyle-nrg/nrg-decipher-dq-creation-skill.git \
  tools/decipher-dq

cat >> AGENTS.md <<'EOF'

## Decipher Dynamic Questions
For any task that creates, changes, verifies or packages a DQ, follow
tools/decipher-dq/AGENTS.md and use tools/decipher-dq/scripts/dq.py.
EOF
```

```bash
# 2. Or make it a personal default across every repository
mkdir -p ~/.codex
cat ~/skills/decipher-dq/AGENTS.md >> ~/.codex/AGENTS.md
```

Codex merges instruction files from your working directory upwards, with the
closest winning, and caps the total at 32 KiB. `AGENTS.md` here is about 8.6 KiB,
roughly a quarter of that, leaving room for your own project rules. Regenerate it
after editing `SKILL.md`:

```bash
python3 scripts/build_agents_md.py            # write it
python3 scripts/build_agents_md.py --check    # fail if stale
```

---

### D. ChatGPT (custom GPT)

A custom GPT caps instructions at **8,000 characters** and knowledge at **10 files**.
This skill is larger than both, so it is repackaged: one condensed operating brief,
and three knowledge files instead of forty.

**1. Build the package.**

```bash
python3 scripts/build_chatgpt.py        # writes dist/chatgpt/
```

```
dist/chatgpt/
├── INSTRUCTIONS.md              3,761 of 8,000 characters
├── decipher-dq-reference.md     the nine reference chapters, consolidated
├── decipher-dq-archetypes.md    the five interviews and spec templates
└── decipher-dq-tools.zip        the scaffolder and the 37-check verifier
```

**2. Create the GPT.** ChatGPT → **Explore GPTs → Create**, then the **Configure**
tab.

**3. Paste `INSTRUCTIONS.md`** into the **Instructions** box.

**4. Enable Code Interpreter** under Capabilities. Without it the GPT can describe a
package but cannot verify one, and an unverified package is not a deliverable.

**5. Upload the three knowledge files** under Knowledge. Leave the other seven slots
free: the 10-file cap is for the lifetime of the GPT, not per edit.

**6. Ask for a DQ** in plain language. The GPT unpacks the tools into its sandbox on
first use, then runs the same scaffolder and the same 37 checks as every other
surface, and hands you a `.zip` with `UPLOAD.md` inside.

---

### Set your environment, once

One file, and only the keys you are changing:

```bash
cp config.local.example.json config.local.json
```

For most teams that means a single value, `host`. `config.local.json` is gitignored,
so an internal hostname never reaches the repository and `git pull` never conflicts
with it. Full key list: [Configuration reference](#configuration-reference).

Leaving `host` unset is safe. The skill asks for it once when it first needs a URL
and refuses to guess, because a guessed hostname costs a round trip through a person.

On the two upload-based surfaces the file is deliberately **not** shipped, so set the
values inside the sandbox when asked, or commit them to `config.json` first — which
publishes them to anyone who clones the repository.

---

### What is actually the same everywhere

The parts that matter are one implementation, not four:

| | Claude Code | Claude app | Codex | ChatGPT |
|---|---|---|---|---|
| The 37 checks | ✅ | ✅ | ✅ | ✅ |
| Scaffolder and archetype interviews | ✅ | ✅ | ✅ | ✅ |
| `bundle` with `UPLOAD.md` | ✅ | ✅ | ✅ | ✅ |
| Full reference library | ✅ | ✅ | ✅ | consolidated to one file |
| Reads your project from disk | ✅ | attach files | ✅ | attach files |
| Instruction source | `SKILL.md` | `SKILL.md` | `AGENTS.md`, generated | pasted brief |

The verifier is plain Python with no dependencies, which is why it runs unchanged in
all four. Confirmed by a test that unpacks the ChatGPT tools zip into a bare
directory — no `reference/`, no `tests/`, no `SKILL.md` — and runs a scaffold and a
full verify inside it.

---

### Worth knowing before you hand this to a team

- **Per person on claude.ai and ChatGPT.** Each teammate installs it themselves.
  Claude Team and Enterprise administrators can publish org-wide through
  organisation settings; a custom GPT can be shared by link or within a workspace.
- **Updating.** In Claude Code or Codex, `git pull` and re-run the tests — the suite
  *is* the upgrade check. On the two upload-based surfaces, rebuild and re-upload;
  neither updates in place.
- **On WSL, clone into your Linux home directory,** not under `/mnt/c`. That mount
  refuses `chmod`, so `git init` fails outright there, and file access is several
  times slower.

> [!IMPORTANT]
> Keep this repository on its own. Do **not** run `git init` in a directory that also
> holds survey exports, respondent files or client packages. A Decipher survey
> directory contains client content and respondent data, and publishing it is not
> recoverable. The bundled `.gitignore` refuses the obvious cases; directory
> discipline covers the rest.

## Without a terminal: what the conversation looks like

The whole flow in the Claude app, for someone who will never run a command. Nothing
below is typed into a shell.

**You:**

> Create a Dynamic Question that shows nine product images in a grid and asks the
> respondent to pick their top three, in order.

**Claude** loads the skill and asks the questions the archetype says must be answered
first — because a request like that leaves the decisions that matter open:

> Before I build anything, five things:
>
> 1. Nine images always, or does it vary by respondent?
> 2. Must all three picks be made before continuing, or may they pick fewer?
> 3. Do you need the **order** of the three picks recorded, or only which three?
> 4. Should the images be the same for everyone, or rotated?
> 5. Which devices — phone only, or desktop too?

You answer in plain language. It writes the specification, scaffolds the package,
builds the logic, and runs its own 37 checks until they are clean. Then:

> Done, and `verify` is clean. Two things I need from you:
>
> **1.** Attach the `survey.xml` of the survey this question will live in, and tell me
> its numeric survey ID. I cannot see your Decipher server, so I will not guess either.
>
> **2.** Here is the package: **`product_grid_v1.zip`** *(download)*
>
> Open `UPLOAD.md` inside it. It tells you which folder goes where, with checksums to
> compare after uploading.

Inside that zip:

```
product_grid_v1.zip
├── UPLOAD.md                          ← read this first
└── lib/
    └── product_grid/
        └── v1/                        ← upload this whole folder
            ├── meta.xml
            ├── styles.xml
            ├── survey.xml             ← the demo, and your instructions
            ├── IMPORT.md              ← how to add it to a survey
            ├── spec.json
            ├── capture_block.xml
            ├── CHANGELOG.txt
            └── static/
```

And `UPLOAD.md` reads:

```markdown
# Where these files go

This archive mirrors the server. Upload each folder to the matching path, as a
whole folder rather than file by file.

## 1. The Dynamic Question package

    from this archive   lib/product_grid/v1/
    to the server       /home/hermes/v2/selfserve/55c/lib/product_grid/v1/

## Do not

- Do not create a `lib` directory under any company other than `55c`.
- Do not upload `uids.bin`, `original.bin`, any `.pickle` or any `.log`. Those
  belong to the server. This archive does not contain them.
- Do not rename anything. The version number is part of how a survey finds this
  package.
```

Three properties of this flow are deliberate:

- **The instructions outlive the conversation.** `UPLOAD.md` is in the zip. A chat scrolls
  away; a file in a folder does not.
- **A red gate blocks the download.** `bundle` refuses to produce a zip while any check
  is failing, so a broken package cannot quietly become an upload.
- **Nothing is invented.** No survey ID, company code or hostname is guessed. If the
  skill does not have one, it asks, once, and says why.

---

## What this is

A **Dynamic Question** (DQ) in Forsta Decipher is a reusable question type: an XML
style package stored centrally under `<server_root>/<company>/lib/<name>/vN/`, which
any survey adopts with a single attribute.

```xml
<radio label="Q1" uses="choice_cards.1" choice_cards:accent="#2bbdb9">
  <title>Which of these appeals to you most?</title>
  <row label="r1">The first option</row>
  <row label="r2">The second option</row>
</radio>
```

That one line is the entire contract. Everything else — the markup, the styling, the
interaction, the data capture — lives in the package, is written once, and is reused by
every study that wants it.

This skill is the workflow around building one. It gives an AI agent four things it
otherwise has to improvise:

| | |
|---|---|
| **A bounded interview** | Five archetypes, each carrying the questions that must be answered before any code is written, with the reason each one changes the design |
| **A complete scaffold** | A package whose demo survey already captures data, already demonstrates two instances on one page, and already demonstrates its own failure path |
| **37 executable checks** | Platform traps encoded as checks that fail the build, rather than as prose nobody rereads |
| **Engineered handoffs** | Exact, single-action requests for the things only a human can do, each naming the artifact it needs back |

---

## Why it exists

A DQ package is unusually easy to get almost right. It compiles. The screen looks
correct. The export is empty.

The reasons are structural, and they repeat:

- **The package is never compiled.** `lib/<name>/vN/` is not a survey. The demo survey
  inside the package — the exact file every adopter copies from — gets no compiler
  feedback at all. A namespaced attribute the package never declared will sit in that
  demo indefinitely and fail for the first designer who copies it.
- **A DQ cannot declare survey variables.** Data capture requires a block the designer
  pastes into their own survey, on the same page, in the right order. Every part of that
  sentence is a way to lose a study's data silently.
- **The survey theme owns the page.** A DQ renders inside someone else's CSS and
  someone else's jQuery. An unscoped selector on a class the theme already uses reaches
  hundreds of elements that are not yours.
- **The browser is the real gate.** Blocked autoplay, a swallowed promise rejection, a
  cache-busting script loader, a selector engine extension that cannot delegate to
  `querySelectorAll` — none of these are visible in any XML.

Each of those has a check in this repository. That is the design premise: **a platform
behaviour written down is a behaviour that will be forgotten; a platform behaviour with
a check is a behaviour that cannot ship broken.**

---

## The developer workflow

Driving the tooling by hand, end to end. In a conversation the skill does this for
you; this is what it is doing.

**1. Run the interview.** The archetype supplies the questions, so they are the same
every time and nothing important is skipped.

```bash
python3 scripts/dq.py new --archetype media-player --questions
```

```
Interview for archetype 'media-player'.
Answer these before scaffolding; the answers become spec.json.

1. One stimulus per question, or a feed of several? If a feed, how many, and is
   the order fixed, rotated, or randomised?
   why it matters: A feed needs a manifest in row text, a rotation rule, and
   per-slot capture keyed to the item rather than the slot. A single stimulus
   needs none of that. Building the feed machinery for a single stimulus is the
   commonest overreach.
   decides: the row-text grammar, capture row counts, whether a rotation rule
   is needed

2. Is sound required for the data to be valid?
   why it matters: Browsers block unmuted autoplay without a user gesture, and a
   swallowed rejection is a frozen frame that is invisible in the export. If
   sound matters, the feed must open behind a tap-to-start gate.
   decides: the start gate, capture fields, the compile handoff wording
   ...
```

**2. Write `spec.json`** from the answers. This is the load-bearing document: every
parameter is classified `public-required`, `public-optional` or `internal`, and every
captured field is declared with its type and row count.

**3. Scaffold.**

```bash
python3 scripts/dq.py new --archetype basic --spec spec.json \
  --into test_environment/lib --apply
```

```
created test_environment/lib/choice_cards/v1
generated capture_block.xml, IMPORT.md

Now run: python scripts/dq.py verify test_environment/lib/choice_cards/v1
```

**4. Build the logic,** consulting [`reference/`](#reference-library) by topic.

**5. Verify, until clean.**

```bash
python3 scripts/dq.py verify test_environment/lib/choice_cards/v1
```

```
verify test_environment/lib/choice_cards/v1  (choice_cards.1)

0 error(s), 0 warning(s)

PASS -- structural only. This does not execute the DQ and does not imply
server acceptance.
```

**6. Hand off.** One action, exact paths, checksums, and the artifact needed back.

```bash
python3 scripts/dq.py handoff upload-package \
  --package test_environment/lib/choice_cards/v1 --step "1 of 2"
```

```
ACTION NEEDED (1 of 2)

Upload as a whole directory, not file by file:
    local   test_environment/lib/choice_cards/v1/
    server  /home/hermes/v2/selfserve/55c/lib/choice_cards/v1/

9 files, 22713 bytes. Checksums below -- compare after upload.
Do not create a lib directory under 53b.

Send back: confirmation, or any error text verbatim.

    CHANGELOG.txt                        1750  456033e596bd107a
    IMPORT.md                            2143  4c269c82a04cfac2
    capture_block.xml                     627  633fcb184d2e430d
    meta.xml                             1151  287b553dffaac10a
    spec.json                            1378  542c51eb5859e307
    static/choice_cards_v1.css           1772  9b8900a9e64b22e0
    static/choice_cards_v1.js            8376  2c0ef2eb7b881fca
    styles.xml                           1654  ae0213336fd0f281
    survey.xml                           3862  8ecfaad7e3b8c685
```

---

## The loop

Six steps. The first and the fourth are the ones that pay for themselves.

```
    ┌──────────────┐
    │ 1. TRANSLATE │  archetype match + bounded interview  ──▶  spec.json
    └──────┬───────┘
           ▼
    ┌──────────────┐
    │ 2. SCAFFOLD  │  a package whose demo already captures data
    └──────┬───────┘
           ▼
    ┌──────────────┐
    │ 3. BUILD     │  the logic, with reference/ consulted by topic
    └──────┬───────┘
           ▼
    ┌──────────────┐
    │ 4. VERIFY    │  37 checks. Non-zero exit stops the loop  ◀─┐
    └──────┬───────┘                                            │
           ▼                                                    │
    ┌──────────────┐                                            │
    │ 5. HAND OFF  │  one exact human action, artifact named  ───┘
    └──────┬───────┘     (server result may send you back)
           ▼
    ┌──────────────┐
    │ 6. RECORD    │  CHANGELOG.txt: what is verified, what is not
    └──────────────┘
```

Step 1 exists because a request like *"a DQ that looks like a YouTube player"* leaves
every consequential decision open — what is captured, what a designer configures,
whether sound is required for validity, whether the respondent can skip. Guessing those
produces a package that has to be rebuilt. Step 4 exists because the alternative to a
local check is a human round trip.

### Commands

```
python3 scripts/dq.py <command> --help
```

| Command | Purpose |
|---|---|
| `new` | Run an archetype's interview, or scaffold a package from an archetype and a spec |
| `verify` | Run every local check. The centre of gravity |
| `extract` | Regenerate `capture_block.xml` and `IMPORT.md` from the fenced demo survey |
| `bump` | Fork `vN` to `vN+1`, rewriting only anchored, enumerated version sites |
| `handoff` | Emit one exact human action |
| `scan` | Find which local surveys reference a DQ version, before changing it |
| `bundle` | Zip a finished package for download, with `UPLOAD.md` naming every destination |

Exit codes: `0` clean · `1` usage error · `2` verification failed · `3` refused on a
safety invariant.

---

## What a scaffold contains

Completeness is the point. A scaffold whose demo cannot capture data defers the riskiest
subsystem to the server, which is the most expensive place to discover it is wrong.

```
choice_cards/v1/
├── meta.xml               scope, compat, count and rename contracts,
│                          plus a functional Builder <template>
├── styles.xml             classified stylevars, includes, the question
│                          override, and the one place the version is emitted
├── survey.xml             THE DEMO — fenced, and the single source of truth
├── static/
│   ├── choice_cards_v1.js   the runtime, instance-scoped, strict mode
│   └── choice_cards_v1.css  scoped to the host class, no theme collisions
├── spec.json              parameter classification + the capture contract
├── capture_block.xml      GENERATED from survey.xml, with a content hash
├── IMPORT.md              GENERATED from survey.xml — the designer's manual
└── CHANGELOG.txt          what changed, why, and what is actually verified
```

The demo survey is not a sample. It is the artifact, and four things are in it from the
first commit because each is a way a package fails on first contact with the server:

1. **A capture field with its startup handshake** — so the data path is exercised before
   anything is uploaded.
2. **A two-instance question** — two of the same DQ on one page, which is how a
   singleton global or a fixed element id is caught.
3. **An invalid-configuration fixture** — so the failure path is demonstrable rather
   than theoretical, and fails loudly rather than rendering something wrong.
4. **Machine-readable fences** — every copyable region is delimited and labelled.

```xml
<!-- dq:requires survey-attr extraVariables contains record -->

<!-- dq:block id="question" action="edit" title="The question you configure" -->
  ...
<!-- dq:endblock -->

<!-- dq:block id="capture" action="copy-verbatim" title="Data capture. Never edit." -->
  ...
<!-- dq:endblock -->
```

`dq.py extract` generates `capture_block.xml` and `IMPORT.md` **from** those fences.
Generated files carry a do-not-edit header and a content hash, and `verify` fails if
either drifts from its source. What a designer copies is therefore byte-identical to
what was compiled and tested — drift becomes impossible rather than merely detectable.

---

## Archetypes

An archetype is not a code generator. It is the set of decisions a shape of DQ forces,
captured as an interview, plus a `spec.json` template.

| Archetype | Shape | Ships |
|---|---|---|
| **`basic`** | A choice question the DQ restyles, with interaction capture. The reference structure every other archetype inherits | Interview, spec template, **full template** |
| **`media-player`** | Video or audio stimulus with an overlay, timed capture and a controlled start | Interview, spec template |
| **`grid-select`** | A grid or gallery of images or cards, single or multiple selection | Interview |
| **`ranking`** | Drag-to-order or click-to-rank | Interview |
| **`timed-exposure`** | Show a stimulus for a controlled duration, then hide it and ask | Interview |

Only `basic` ships a full file template, and that is deliberate rather than unfinished.
A template is a promise that the code inside it has been compiled and run; four
half-verified templates would be four sources of confident, untested output. The other
archetypes contribute what is genuinely reusable — the questions and the capture shape —
and `dq.py new` says so plainly and redirects you to `basic`:

```
error: archetype 'media-player' has no template in this release
       (status: interview-and-spec-only).
Scaffold from 'basic', which is the reference structure every archetype
inherits, then apply this archetype's questions and capture shape by hand.
```

Adding a full template for an archetype is the natural first contribution.

---

## Verification

```bash
python3 scripts/dq.py verify <package>            # everything
python3 scripts/dq.py verify <package> --only capture
python3 scripts/dq.py verify <package> --only demo_attrs
python3 scripts/dq.py verify <package> --json     # for a pipeline
```

**37 checks in six groups.** Every finding names the failure it prevents, because a
check that only says "invalid" gets suppressed.

<table>
<tr><th align="left">Group</th><th align="left">Checks</th><th align="left">Defends</th></tr>
<tr>
<td><b><code>structure</code></b><br><i>8</i></td>
<td><code>required_files</code> <code>identity</code> <code>xml_wellformed</code> <code>template_cdata</code> <code>meta_contract</code> <code>forbidden_files</code> <code>include_targets</code> <code>include_cost</code></td>
<td>Is this a package at all. Includes a <b>case-sensitivity</b> check on include paths, because a case-insensitive local filesystem hides a wrong-case include that returns 404 only on the server</td>
</tr>
<tr>
<td><b><code>styles</code></b><br><i>6</i></td>
<td><code>styles_top_level</code> <code>stylevar_shape</code> <code>stylevar_classification</code> <code>stylevar_reachability</code> <code>render_defaults</code> <code>asset_syntax</code></td>
<td>The parameter surface. <code>render_defaults</code> substitutes every default into the template and scans the result, which is how a default of the literal <code>""</code> is caught before it emits four quote characters and kills the page</td>
</tr>
<tr>
<td><b><code>demo</code></b><br><i>7</i></td>
<td><code>demo_fences</code> <code>demo_uses</code> <code>demo_attrs</code> <code>survey_grammar</code> <code>demo_requires</code> <code>demo_assets</code> <code>row_labels</code></td>
<td>The boilerplate survey, which has <b>no compile gate of its own</b>. This group is its substitute: undeclared attributes, block grammar errors, assets the demo names but the package does not ship, and row-label forms recorded rather than assumed</td>
</tr>
<tr>
<td><b><code>capture</code></b><br><i>4</i></td>
<td><code>capture_contract</code> <code>capture_same_page</code> <code>generated_sync</code> <code>capture_hash_recorded</code></td>
<td>The part that loses data. Cross-checks <code>spec.json</code> against the demo's declarations against the runtime's probe list, and fails on a <code>&lt;suspend/&gt;</code> between the question and its capture block</td>
</tr>
<tr>
<td><b><code>runtime</code></b><br><i>9</i></td>
<td><code>unscoped_selectors</code> <code>hot_selectors</code> <code>script_loader</code> <code>swallowed_rejection</code> <code>unsafe_evaluation</code> <code>instance_isolation</code> <code>strict_mode</code> <code>external_origins</code> <code>call_graph</code></td>
<td>The browser. Theme-class collisions, selector-engine extensions, cache-busting loaders, swallowed autoplay rejections, singleton globals, unapproved origins, and methods called but never defined</td>
</tr>
<tr>
<td><b><code>version</code></b><br><i>3</i></td>
<td><code>version_coherence</code> <code>stale_version_strings</code> <code>runtime_version_hardcoded</code></td>
<td>One declared version, everywhere. Including the <code>or 'N'</code> numeric fallback that a token-shaped rename does not match, and a prior version left behind in a respondent- or QA-facing string</td>
</tr>
</table>

Full descriptions: [`reference/06-verify.md`](reference/06-verify.md).

### What `verify` does not prove

Stated first in the reference chapter, and stated again here, so the pass line is never
over-read:

> **It does not execute the DQ.** No JavaScript runs, no DOM is built, no payload goes
> through the real pipeline. A pass means the files are structurally sound and the
> contracts agree with each other.
>
> **It does not imply server acceptance.** That needs a compile, a respondent, the
> required devices, and **exported data**. A correct screen does not prove a correct
> dataset; hidden inputs can look right and still be discarded on submit.

`verify` prints that caveat in its own pass line rather than leaving it to be
remembered. Its value is narrow and real: it stops you spending a human round trip on
something a regex could have told you.

---

## The designer surface

The acceptance test the whole parameter surface is designed against:

> **Two Survey Designers who have not seen the package are given `IMPORT.md`, the demo
> survey and a brief. Both reach a working question with correct data, unaided, without
> opening any file under `lib/`.**

No HTML, no CSS, no JavaScript, no Python. A designer who has to open a `lib/` file is a
failure of the parameter surface, not a failure of the designer.

`IMPORT.md` is generated from the fenced demo and the classification in `spec.json`, so
it cannot drift from what was tested:

```markdown
# Using choice_cards.1

You never need to write HTML, CSS, JavaScript or Python for this question, and
you never need to open a file under `lib/`.

## What to copy, in order

| # | Block                                     | What to do              |
|---|-------------------------------------------|-------------------------|
| 1 | `question` — The question you configure   | **EDIT THIS**           |
| 2 | `capture` — Data capture. Never edit.     | copy as-is — never edit |

The question block and the capture block must end up on the same page, in that
order, with no `<suspend/>` between them. A DQ can only write fields that are
rendered, so across a page boundary the screen looks right and the export is empty.

## Settings you may change

Every one of these has a default that is correct for most studies. **Leave them
out unless you mean to change one.** Restating a default pins your survey to
today's behaviour.
```

That last instruction matters more than it looks. A survey that restates twenty defaults
is pinned to today's behaviour and silently defeats every default a future version
improves. `spec.json`'s three-way classification is what makes the distinction
expressible at all, since Decipher's own `<stylevar>` vocabulary has no notion of
"required" or "internal".

---

## Versioning

A version is a **completed, verified increment**, not a save point. Iterate freely
inside a version while it is `state=dev`; cut the next one when the increment is done.
A published `vN` is immutable — corrections go in `vN+1`.

Two structural decisions remove the usual class of version bugs.

**One declared version.** `meta.xml` holds it. `styles.xml` emits it to JavaScript as a
single constant, and no runtime file hardcodes it. Filenames keep `<name>_vN` for
cache-busting, but they are produced by `dq.py bump`, which rewrites only anchored,
enumerated sites and **refuses on anything ambiguous** rather than guessing:

```bash
python3 scripts/dq.py bump test_environment/lib/choice_cards/v1 --apply
```

An unanchored search-and-replace across a package is the failure mode this replaces: it
matches `v1` in a comment and misses `or '1'` in an expression. `version_coherence`
then reads every version site independently and reports disagreement.

**No hand-typed capture-block version.** On disk, `capture_block.xml` records a hash of
its own declarations, and `verify` fails if it drifts from the demo. At runtime, the
startup handshake checks labels, row counts and writability, which is what actually
catches a stale block: if the declarations changed, the shape differs and the handshake
says so. There is nothing to remember to increment.

---

## The human boundary

The skill **cannot** upload, compile, clone a survey, change survey state, export data or
delete anything. That boundary is deliberate and it is not going to move. What the skill
does instead is make each crossing cost as little as possible.

```bash
python3 scripts/dq.py handoff clone --source 990001
python3 scripts/dq.py handoff upload-package --package <dir> --step "1 of 2"
python3 scripts/dq.py handoff upload-survey --survey 990002 --step "2 of 2"
python3 scripts/dq.py handoff compile --survey 990002 --media
python3 scripts/dq.py handoff state   --survey 990002
python3 scripts/dq.py handoff export  --survey 990002 --fixture "..."
```

Seven rules are baked into the templates, each answering a specific way a request fails:

1. **One action per request.** A person given three tasks does two.
2. **Name the artifact needed back.** Otherwise the reply is "done" and you still cannot
   proceed.
3. **Ask for error text verbatim.** A paraphrased compiler message costs another round
   trip — the compiler names the exact element and attribute it rejected.
4. **State the reason in one line.** A person who understands the constraint stops
   working around it.
5. **Say what not to touch**, when something adjacent is tempting.
6. **Absolute local paths and absolute server paths.** Never "the lib folder".
7. **Never ask for a judgement that was yours to make.**

`handoff compile --media` adds one line that is easy to omit and expensive to omit:

```
    Please use a fresh profile or a private window. A browser that has already
    played media on this origin is allowed to autoplay with sound, so it will
    hide the very failure this checks for.
```

Templates and rationale: [`reference/07-handoff.md`](reference/07-handoff.md).

---

## Safety invariants

Enforced in code, not left to attention. A violation exits `3` and no work is done.

| Invariant | Enforcement |
|---|---|
| The configured **test company only** | `guard_path()` refuses any path naming a `forbidden_companies` code or a production tree |
| Production references never ship | `external_origins` fails on a forbidden company code anywhere in a package |
| No hardcoded survey ids | `hardcoded_survey` fails on a numeric survey path in package code — it does not survive a survey copy, and every adopter would load assets from someone else's survey |
| No guessed hostnames | `external_origins` fails on any origin absent from `spec.json` `approved_origins` |
| A published `vN` is immutable | `new` and `bump` refuse an existing target directory |
| Server-owned files stay on the server | `forbidden_files` fails on `uids.bin`, pickles and logs inside an upload unit |
| No code execution over designer input | `unsafe_evaluation` fails on `eval` and `new Function` |
| Untouched server evidence stays untouched | Directories holding downloaded survey material are never edited |

---

## Configuration reference

Nothing in this skill hardcodes a hostname, a company code or a server path. Setting
them is one step, covered under [Set up](#set-up); this is the full key list.

All five keys, of which you only need the ones you are changing:

| Key | Meaning |
|---|---|
| `host` | Your Decipher hostname. Used only to render respondent URLs in handoff requests |
| `server_root` | The path above the company directories on the survey server |
| `test_company` | The company code this skill is allowed to target |
| `forbidden_companies` | Company codes that are refused outright, production first among them |
| `local_root` | Where packages and surveys live in your working tree |

`config.json` holds the committed defaults. `config.local.json` is read after it and
wins key by key, and it is **gitignored** — so an internal hostname stays out of the
repository, your working tree stays clean, and a `git pull` never conflicts with your
environment. Editing `config.json` directly also works, at the cost of a permanently
modified tracked file.

Both the tooling and the 37 checks read the merged result. `forbidden_companies` is a
hard refusal rather than a warning: a path naming one of those codes exits `3` and no
work is done.

---

## Reference library

Nine chapters, written to be **consulted by topic rather than read end to end**.
`SKILL.md` routes to them; each is short enough to load whole.

Every claim carries an evidence label, so an observation is never mistaken for an
inference:

| Label | Means |
|---|---|
| `OFFICIAL` | Stated in Forsta Surveys documentation |
| `TRAINING` | Stated in supplied Forsta training material |
| `VERIFIED-*` | Observed through a compile or runtime experiment, with the date |
| `CONVENTION` | An engineering choice to reduce risk. Not a platform law |
| `UNRESOLVED` | Plausible but unproven. Never to be promoted silently |

| Chapter | Covers |
|---|---|
| [`00-platform.md`](reference/00-platform.md) | The Decipher dialect: which of the four syntax layers is legal where, and the survey-side grammar a DQ must generate or document |
| [`01-package.md`](reference/01-package.md) | Package anatomy, naming, version isolation, what belongs in an upload unit |
| [`02-designer-surface.md`](reference/02-designer-surface.md) | Parameter classification, `meta.xml` and Builder, the delimited row-text grammar, localisation |
| [`03-capture.md`](reference/03-capture.md) | Why a DQ cannot declare variables, the paste-once block, the same-page rule, the startup handshake, the exported-data rule |
| [`04-client-runtime.md`](reference/04-client-runtime.md) | CSS cascade and specificity, theme class collisions, selector engines, script loaders, media autoplay policy, instance isolation |
| [`05-findings.md`](reference/05-findings.md) | The dated findings register, each entry naming the failure text and the check that now catches it |
| [`06-verify.md`](reference/06-verify.md) | What each check proves, and the two things none of them prove |
| [`07-handoff.md`](reference/07-handoff.md) | The human-action request templates and the rules behind them |
| [`08-collaboration.md`](reference/08-collaboration.md) | Several developers on one library, and what not to build |

A finding with no check is a finding that will recur. That is the standard the register
is held to.

---

## Calibrating against your own library

A check suite that only ever runs against its own fixtures measures itself. Point it at
a library whose defects you already know and it measures the suite instead.

```bash
export DECIPHER_DQ_CORPUS=/path/to/your/lib
cp tests/corpus_expectations.example.json tests/corpus_expectations.json
# edit it to name packages, checks and expected substrings
python3 tests/test_verify.py
```

```json
{
  "example_player/v3": [
    { "check": "demo_attrs", "contains": "clip_length" },
    { "check": "unscoped_selectors", "contains": ".cell" }
  ],
  "example_player/v4": [
    { "check": "stale_version_strings", "contains": "v3" }
  ]
}
```

Two assertions come out of this, and they are the ones that matter:

- **No check may crash on real input.** Real packages contain shapes no fixture
  anticipates, and a check that raises is a check that has silently stopped defending
  anything. This assertion needs no expectations file.
- **Every defect you know about must be reported.** If `verify` cannot find something you
  know is there, the check is wrong — not the library.

`corpus_expectations.json` is gitignored. It describes your packages, not this skill.

---

## Repository layout

```
decipher-dq/
├── SKILL.md                     the router: invariants, the six-step loop,
│                                routing table, version discipline
├── config.json                  committed defaults
├── config.local.json            your environment, gitignored (from .example)
├── README.md
│
├── reference/                   nine chapters, consulted by topic
│   └── 00-platform.md ... 08-collaboration.md
│
├── archetypes/
│   ├── basic/
│   │   ├── archetype.json       interview + spec template
│   │   └── template/            the full, verified file template
│   ├── media-player/            interview + spec template
│   ├── grid-select/             interview
│   ├── ranking/                 interview
│   └── timed-exposure/          interview
│
├── AGENTS.md                    generated from SKILL.md, for OpenAI Codex
│
├── scripts/
│   ├── dq.py                    seven commands, no dependencies
│   ├── build_claude_zip.py      packages this skill for claude.ai upload
│   ├── build_agents_md.py       regenerates AGENTS.md; --check asserts sync
│   └── build_chatgpt.py         packages it for a ChatGPT custom GPT
│
├── checks/                      37 checks in six topical modules
│   ├── common.py                shared scanners, config, the renderer
│   ├── structure.py  styles.py  demo.py
│   └── capture.py    runtime.py version.py
│
└── tests/
    ├── test_verify.py           61 tests: one mutation per check, every
    │                            packaging path, plus the opt-in corpus class
    └── corpus_expectations.example.json
```

Roughly 4,600 lines, of which about 1,100 are reference prose and about 1,700 are
checks. There is nothing to install and nothing to build.

---

## Development

```bash
python3 tests/test_verify.py             # all 61
python3 tests/test_verify.py Scaffolded  # the 39 mutation tests only
python3 tests/test_verify.py Bundle      # the download path
python3 tests/test_verify.py ClaudeZip   # the claude.ai archive
python3 tests/test_verify.py OpenAiTargets  # AGENTS.md sync + the ChatGPT package
python3 tests/test_verify.py Corpus      # requires DECIPHER_DQ_CORPUS
```

The mutation tests work one way round, and the direction is the point: scaffold a clean
package, **break exactly one thing**, and assert that the check which owns that failure
fires. One fixture per check means a refactor cannot quietly disable part of the safety
net while the suite still reports green.

### Adding a check

Two conditions, both required:

1. **It must fire on a real failure.** Not a hypothetical one. Record the failure in
   [`reference/05-findings.md`](reference/05-findings.md) with its evidence label, its
   error text, and the check that now catches it.
2. **It must stay quiet on a correct package.** Add the mutation test that breaks
   exactly that one thing.

A check with no test is not finished. A suite that passes everything proves nothing.

### Adding an archetype

1. `archetypes/<name>/archetype.json` — the questions, each with an `ask`, a `why` and
   the decisions it `affects`, plus a `spec_template`.
2. Optionally `template/` — but only once its code has been compiled and run through a
   respondent. Until then, declare the archetype interview-only and let `dq.py new`
   redirect to `basic`. Untested confident output is worse than an honest redirect.

---

## Limits

Stated plainly, because a tool that overstates itself is worse than one that does less.

- **Local verification is structural.** No JavaScript is executed and no DOM is built.
  Where a JavaScript runtime is available, an archetype's own unit tests can run over its
  parser and state machine; where one is not, `verify` says so in its pass line.
- **Server acceptance is a separate state.** A compile, a respondent, the required
  devices, and exported data. `verify` passing means one thing; the export being correct
  means another. Both are reported separately, always.
- **The human boundary stays.** Upload, compile, clone, state changes, exports and
  deletions belong to a person. The loop gets faster by wasting fewer round trips, not by
  removing the person.
- **`basic` is the only full template.** By design, until another archetype's code has
  been through a respondent.
- **`less` in `styles.xml` is unproven** on the platform version this was built against.
  `verify` warns rather than fails, and the reference marks it `UNRESOLVED`.

---

<div align="center">

**Built for Forsta Decipher survey engineering.**

Contributions welcome: a check with a real failure behind it, an archetype template that
has been through a respondent, or a finding with its evidence label attached.

</div>
