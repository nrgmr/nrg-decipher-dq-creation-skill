#!/usr/bin/env python3
"""Package this skill as a zip that claude.ai will accept.

    python3 scripts/build_claude_zip.py

claude.ai requires the skill folder to be the root entry INSIDE the archive, not
the archive's own contents:

    decipher-dq.zip
    └── decipher-dq/
        ├── SKILL.md
        └── ...

A zip whose SKILL.md sits at the top level is rejected, so this script builds the
nesting rather than leaving it to whoever runs the zip command. It also checks the
frontmatter against the documented limits, because those failures are reported at
upload time with little detail.

Claude Code does not need this. There, the skill is a directory.
"""

import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_NAME = ROOT.name

# Personal, generated, or version-control noise. config.local.json is excluded
# deliberately: it holds one team's hostname and company code.
EXCLUDE_DIRS = {".git", "__pycache__", ".pytest_cache", "dist", ".idea", ".vscode"}
EXCLUDE_FILES = {"config.local.json", "corpus_expectations.json", ".DS_Store"}
EXCLUDE_SUFFIXES = {".pyc", ".zip", ".swp"}

NAME_PATTERN = re.compile(r"^[a-z0-9-]{1,64}$")
RESERVED = ("anthropic", "claude")
DESCRIPTION_LIMIT = 200


def fail(message):
    sys.stderr.write("error: %s\n" % message)
    raise SystemExit(1)


def check_frontmatter():
    path = ROOT / "SKILL.md"
    if not path.is_file():
        fail("no SKILL.md at %s" % ROOT)
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        fail("SKILL.md does not begin with YAML frontmatter")
    block = text.split("---", 2)[1]

    found = re.search(r"^name:\s*(.+)$", block, re.M)
    if not found:
        fail("SKILL.md frontmatter has no name")
    name = found.group(1).strip()
    if not NAME_PATTERN.match(name):
        fail("name %r must be 1-64 chars of lowercase letters, numbers and hyphens"
             % name)
    for word in RESERVED:
        if word in name:
            fail("name %r contains the reserved word %r" % (name, word))
    if name != SKILL_NAME:
        fail("name is %r but the directory is %r. claude.ai takes the skill from "
             "the folder inside the zip, so they must agree." % (name, SKILL_NAME))

    found = re.search(r"^description:\s*(.+)$", block, re.M)
    if not found:
        fail("SKILL.md frontmatter has no description")
    description = found.group(1).strip()
    if len(description) > DESCRIPTION_LIMIT:
        fail("description is %d characters; the claude.ai limit is %d.\n"
             "It has to say what the skill does AND when to use it, so shorten "
             "rather than truncate." % (len(description), DESCRIPTION_LIMIT))
    if "<" in description or ">" in description:
        fail("description contains angle brackets, which are rejected as XML")

    return name, description


def wanted(path):
    relative = path.relative_to(ROOT)
    if any(part in EXCLUDE_DIRS for part in relative.parts):
        return False
    if path.name in EXCLUDE_FILES:
        return False
    return path.suffix not in EXCLUDE_SUFFIXES


def main():
    name, description = check_frontmatter()

    out_dir = ROOT / "dist"
    out_dir.mkdir(exist_ok=True)
    target = out_dir / ("%s.zip" % name)

    files = sorted(p for p in ROOT.rglob("*") if p.is_file() and wanted(p))
    if not files:
        fail("nothing to package")

    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, "%s/%s" % (name, path.relative_to(ROOT).as_posix()))

    with zipfile.ZipFile(target) as archive:
        names = archive.namelist()
    expected = "%s/SKILL.md" % name
    if expected not in names:
        fail("built archive has no %s" % expected)
    if any("/" not in entry for entry in names):
        fail("built archive has an entry at its root; claude.ai rejects that")

    print("wrote %s" % target)
    print("  %d files, %d bytes" % (len(names), target.stat().st_size))
    print("  root entry: %s/" % name)
    print("  description: %d/%d characters" % (len(description), DESCRIPTION_LIMIT))
    print()
    print("Upload it in claude.ai: Settings > Capabilities, turn on code execution,")
    print("then Skills > Create skill, and choose this file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
