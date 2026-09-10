# Several developers on the same DQ library

Short by design, because most of the answer is one sentence and the rest is
premature.

## The actual blocker is that there is no version control

`.git` is an empty directory and history lives out of tree.
The ceremony that tends to grow in its absence — dated checksum baselines,
hand-curated registries, frozen release directories with revision numbers,
checksum manifests, a multi-state job ledger — is a manual reimplementation of
what Git provides, and it drifts from the
filesystem it tracked: surveys existing on disk and in no registry, a package
recorded at one revision while the disk said another, and release directories
matching no naming rule at all.

**Put `lib/` and this skill under Git.** That is the recommendation, and it
replaces all of it. Then:

- history, authorship and blame are free
- a diff between two versions is a real diff, not a checksum comparison
- reverting is a revert, not a rollback plan
- `scan` still answers "who uses this version", from the working tree

Without version control, no amount of tooling makes concurrent editing safe, and
a second developer editing the same unreleased `vN` will silently lose work.

## Until then, the minimum convention

Two rules, both cheap:

1. **One owner per unreleased version.** Put it in the `CHANGELOG.txt` header of
   that version directory — the file is already the package's provenance record
   and already travels with it. A version whose changelog names someone else is
   not yours to edit.
2. **A released `vN` is immutable, so it needs no lock.** This is already an
   invariant. It is also what makes parallel work possible at all: two people can
   work on `v4` and `v5` without coordination because neither can touch the
   other's directory.

## What not to build

**A shared web platform.** Not warranted at this scale, and it would need the
server access this skill deliberately does not have.

**A DQ registry.** The filesystem is the truth and `scan` derives dependencies
from it. A registry is a second source of truth that has already been observed
disagreeing with the first.

**A cross-version import mechanism.** Tempting when five versions share 90% of
their code, and forbidden for a good reason: closing or deleting one version
would break another. The duplication is the price of a version being safely
deletable.

## What is worth building, later

A **read-only catalogue** generated from every package's `spec.json`: name,
version, what it does, its public parameters, what it captures, which surveys use
it. That is the one thing a Survey Designer currently cannot get without reading
`lib/`, which the designer acceptance test in
[02-designer-surface.md](02-designer-surface.md) says they must never have to do.

It is a generator over files that already exist, so it cannot drift. Build it
when there are enough DQs that discovery is a real problem — not before.
