#!/usr/bin/env python3
"""Package this skill for a ChatGPT custom GPT.

    python3 scripts/build_chatgpt.py       # writes dist/chatgpt/

A custom GPT imposes two limits this skill does not otherwise meet:

  * Instructions are capped at 8,000 characters. SKILL.md is longer, so the
    instructions emitted here are a condensed operating brief that names the
    knowledge files rather than restating them.
  * Knowledge is capped at 10 files for the lifetime of the GPT. The skill has
    around forty, so the reference chapters and the archetype interviews are
    each consolidated into one file, and the runnable tooling into one zip that
    the GPT's code interpreter unpacks.

The result is three knowledge files, leaving headroom.
"""

import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "chatgpt"

INSTRUCTION_CAP = 8000
KNOWLEDGE_CAP = 10

TOOLS_ZIP = "decipher-dq-tools.zip"
REFERENCE_MD = "decipher-dq-reference.md"
ARCHETYPES_MD = "decipher-dq-archetypes.md"

INSTRUCTIONS = """You build Forsta Decipher Dynamic Questions (DQs): reusable
survey question types, packaged as XML style directories that a survey adopts with
one attribute, `uses="<name>.<N>"`.

# Your knowledge files

- `%(reference)s` - the platform reference. Nine chapters. Consult it BY TOPIC
  before asserting any platform behaviour. Every claim carries an evidence label:
  OFFICIAL, TRAINING, VERIFIED, CONVENTION or UNRESOLVED. Never promote an
  UNRESOLVED claim to a fact.
- `%(archetypes)s` - five DQ shapes, each with the questions that must be
  answered before any code is written, and why each one changes the design.
- `%(tools)s` - the scaffolder and the 37-check verifier.

# Set up your session once

At the start of a DQ task, unpack the tools with the code interpreter:

    import zipfile, pathlib
    zipfile.ZipFile('/mnt/data/%(tools)s').extractall('/mnt/data/dq')
    print(sorted(p.name for p in pathlib.Path('/mnt/data/dq').iterdir()))

Then run everything from `/mnt/data/dq`:

    !cd /mnt/data/dq && python3 scripts/dq.py --help

It needs only the standard library. If the code interpreter is unavailable, say
so plainly and stop: you cannot verify a package without it, and an unverified
package is not a deliverable.

# The loop. Do not skip steps 1 or 4

1. TRANSLATE. A request like "a DQ like a YouTube player" leaves every decision
   that matters open. Pick an archetype and ask its questions from
   `%(archetypes)s` before writing anything. Write `spec.json`, classifying every
   parameter as public-required, public-optional or internal.
2. SCAFFOLD. `python3 scripts/dq.py new --archetype basic --spec spec.json
   --into /mnt/data/out/lib --apply`
3. BUILD the logic. Consult the reference by topic, not end to end.
4. VERIFY. `python3 scripts/dq.py verify <package>` until it is clean. It exits
   non-zero on any error. Never silence a check and never proceed past one.
5. DELIVER. `python3 scripts/dq.py bundle <package> --apply`, then give the user
   the resulting zip as a download. It contains UPLOAD.md, naming the server
   destination of every folder plus checksums. `bundle` refuses to run while
   verify reports errors; do not reach for --force.
6. RECORD. A CHANGELOG.txt entry: what changed, why, what is verified, what is not.

# Invariants

- You CANNOT upload, compile, clone a survey, change survey state, export data or
  delete anything. A human does all of it. Emit one exact request at a time with
  `python3 scripts/dq.py handoff <action>` and stop for the result.
- Target the configured test company only. Refuse any path naming a production
  company or tree. The tooling enforces this and exits 3.
- A version that has been uploaded is immutable. Corrections go in the next one.
- Data lives or dies in the EXPORT. A correct-looking screen proves nothing.
- Local-green is not server-accepted. Always say which one you have.
- No explanatory comments in package runtime files. Reasoning goes in CHANGELOG.txt.
- Survey Designers must never need to open a file under `lib/`, and must never be
  asked to write HTML, CSS, JavaScript or Python.

# You cannot see the user's files or server

Ask for what you need, once and specifically: "attach the survey.xml this will go
into, and tell me its numeric survey ID." Never invent a survey ID, a company
code or a hostname; a guessed hostname costs a round trip through a person. Set
real values in `config.json` inside the unpacked tools if the user supplies them.

# Tone

The user may not be a developer. Say "the folder called lib", not "the lib
artifact". Never leave a shell command as the only instruction. State what is
verified and what is not, and never let "it compiled" become "it works".
""" % {"reference": REFERENCE_MD, "archetypes": ARCHETYPES_MD, "tools": TOOLS_ZIP}

TOOLS_INCLUDE = ("scripts", "checks", "archetypes", "config.json")
TOOLS_EXCLUDE_NAMES = {"config.local.json", "build_claude_zip.py",
                       "build_chatgpt.py", "build_agents_md.py"}


def fail(message):
    sys.stderr.write("error: %s\n" % message)
    raise SystemExit(1)


def build_reference():
    chapters = sorted((ROOT / "reference").glob("*.md"))
    if not chapters:
        fail("no reference chapters found")
    parts = [
        "# Decipher DQ reference",
        "",
        "Consolidated from the skill's nine reference chapters, because a custom "
        "GPT accepts at most %d knowledge files. Consult by topic; do not read "
        "end to end." % KNOWLEDGE_CAP,
        "",
        "## Chapters",
        "",
    ]
    for path in chapters:
        title = path.read_text(encoding="utf-8").split("\n", 1)[0].lstrip("# ").strip()
        parts.append("- %s (%s)" % (title, path.name))
    parts.append("")
    for path in chapters:
        text = path.read_text(encoding="utf-8").rstrip()
        # Demote headings by one level so each chapter nests under its own H1.
        text = re.sub(r"^#", "##", text, flags=re.M)
        parts.append("\n---\n")
        parts.append("<!-- source: reference/%s -->" % path.name)
        parts.append("")
        parts.append(text)
        parts.append("")
    return "\n".join(parts)


def build_archetypes():
    parts = [
        "# Decipher DQ archetypes",
        "",
        "Five shapes of DQ. Each carries the questions that must be answered "
        "before any code is written, and what each answer decides. Ask them; do "
        "not guess the answers.",
        "",
    ]
    for path in sorted((ROOT / "archetypes").iterdir()):
        if not path.is_dir():
            continue
        doc = json.loads((path / "archetype.json").read_text(encoding="utf-8"))
        parts.append("## %s" % path.name)
        parts.append("")
        if doc.get("summary"):
            parts.append(doc["summary"])
            parts.append("")
        status = doc.get("status", "full-template")
        parts.append("Status: **%s**." % status)
        if status != "full-template":
            parts.append("")
            parts.append("This archetype ships no file template. Scaffold from "
                         "`basic` and apply this interview and capture shape by "
                         "hand. An untested template is worse than an honest "
                         "redirect.")
        parts.append("")
        parts.append("### Ask before building")
        parts.append("")
        for n, question in enumerate(doc.get("questions", []), 1):
            parts.append("%d. **%s**" % (n, question["ask"]))
            if question.get("why"):
                parts.append("   - Why it matters: %s" % question["why"])
            if question.get("affects"):
                parts.append("   - Decides: %s" % ", ".join(question["affects"]))
        parts.append("")
        if doc.get("spec_template"):
            parts.append("### spec.json template")
            parts.append("")
            parts.append("```json")
            parts.append(json.dumps(doc["spec_template"], indent=2))
            parts.append("```")
            parts.append("")
    return "\n".join(parts)


def build_tools(target):
    count = 0
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for entry in TOOLS_INCLUDE:
            source = ROOT / entry
            if source.is_file():
                archive.write(source, entry)
                count += 1
                continue
            for path in sorted(source.rglob("*")):
                if not path.is_file():
                    continue
                if path.name in TOOLS_EXCLUDE_NAMES:
                    continue
                if "__pycache__" in path.parts or path.suffix == ".pyc":
                    continue
                archive.write(path, path.relative_to(ROOT).as_posix())
                count += 1
    return count


def main():
    if len(INSTRUCTIONS) > INSTRUCTION_CAP:
        fail("instructions are %d characters; the custom GPT cap is %d.\n"
             "Shorten the brief rather than truncating it: a cut-off instruction "
             "block fails silently at runtime."
             % (len(INSTRUCTIONS), INSTRUCTION_CAP))

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "INSTRUCTIONS.md").write_text(INSTRUCTIONS, encoding="utf-8",
                                         newline="\n")
    (OUT / REFERENCE_MD).write_text(build_reference(), encoding="utf-8",
                                    newline="\n")
    (OUT / ARCHETYPES_MD).write_text(build_archetypes(), encoding="utf-8",
                                     newline="\n")
    packed = build_tools(OUT / TOOLS_ZIP)

    knowledge = [REFERENCE_MD, ARCHETYPES_MD, TOOLS_ZIP]
    if len(knowledge) > KNOWLEDGE_CAP:
        fail("%d knowledge files exceeds the cap of %d"
             % (len(knowledge), KNOWLEDGE_CAP))

    print("wrote %s" % OUT)
    print()
    print("  INSTRUCTIONS.md   %5d chars of %d  (paste into the Instructions box)"
          % (len(INSTRUCTIONS), INSTRUCTION_CAP))
    print("  Knowledge files   %5d of %d allowed:" % (len(knowledge), KNOWLEDGE_CAP))
    for name in knowledge:
        size = (OUT / name).stat().st_size
        print("      %-30s %8d bytes" % (name, size))
    print("      (%d tool files inside the zip)" % packed)
    print()
    print("Next: create a GPT, enable Code Interpreter, paste INSTRUCTIONS.md,")
    print("and upload the three knowledge files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
