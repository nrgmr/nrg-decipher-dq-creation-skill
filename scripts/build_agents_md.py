#!/usr/bin/env python3
"""Generate AGENTS.md for OpenAI Codex from SKILL.md.

    python3 scripts/build_agents_md.py            # write it
    python3 scripts/build_agents_md.py --check    # fail if it is stale

Codex reads AGENTS.md automatically; it does not know about SKILL.md or its YAML
frontmatter. Rather than maintain the same guidance twice and let the copies
drift -- the exact failure this skill's own checks exist to catch -- AGENTS.md is
generated, and a test asserts it is in sync.

Codex concatenates instruction files with a 32 KiB total cap, so this stays a
single small file and leaves the bulk in reference/, which Codex reads on demand.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "SKILL.md"
AGENTS = ROOT / "AGENTS.md"
CODEX_CAP = 32 * 1024

BANNER = """<!-- GENERATED from SKILL.md by scripts/build_agents_md.py. Do not edit.
     Edit SKILL.md and regenerate, or the two will disagree. -->

# Decipher DQ

You are working with a skill for building Forsta Decipher Dynamic Questions. The
guidance below is authoritative for any task in this repository that creates,
changes, verifies or packages a DQ.

Run the tooling with `python3 scripts/dq.py <command> --help`. It needs Python
3.10 or newer and nothing else. Before asking a human for anything, `verify` must
be clean.

"""


def build():
    text = SKILL.read_text(encoding="utf-8")
    if not text.startswith("---"):
        sys.stderr.write("error: SKILL.md has no frontmatter\n")
        raise SystemExit(1)
    # Drop the frontmatter: Codex has no use for name/description metadata, and
    # a stray YAML block at the top of AGENTS.md just burns the instruction cap.
    body = text.split("---", 2)[2].lstrip()
    # The H1 is replaced by the banner's own.
    if body.startswith("# "):
        body = body.split("\n", 1)[1].lstrip()
    return BANNER + body


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if AGENTS.md does not match SKILL.md")
    args = parser.parse_args()

    wanted = build()
    size = len(wanted.encode("utf-8"))
    if size > CODEX_CAP:
        sys.stderr.write(
            "error: %d bytes exceeds the %d byte Codex instruction cap.\n"
            "Move detail into reference/ and link to it instead.\n"
            % (size, CODEX_CAP))
        raise SystemExit(1)

    if args.check:
        current = AGENTS.read_text(encoding="utf-8") if AGENTS.is_file() else ""
        if current != wanted:
            sys.stderr.write(
                "error: AGENTS.md is stale.\n"
                "Run: python3 scripts/build_agents_md.py\n")
            raise SystemExit(1)
        print("AGENTS.md is in sync with SKILL.md (%d bytes, cap %d)"
              % (size, CODEX_CAP))
        return 0

    AGENTS.write_text(wanted, encoding="utf-8", newline="\n")
    print("wrote %s" % AGENTS)
    print("  %d bytes of a %d byte Codex instruction budget (%.0f%%)"
          % (size, CODEX_CAP, 100.0 * size / CODEX_CAP))
    return 0


if __name__ == "__main__":
    sys.exit(main())
