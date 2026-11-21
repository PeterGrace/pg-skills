---
name: codebase-study-guide
description: >-
  Generate grounded study documentation for an existing codebase — an architecture
  overview, per-module deep dives, a glossary, and Anki-ready flashcards — written as
  markdown into the repository's docs/ folder. Use this skill whenever the user wants to
  study, learn, onboard onto, document, or "make sense of" a codebase; asks for a study
  guide, onboarding guide, architecture doc, code walkthrough, glossary, or flashcards for
  a repo; or wants to help a team talk more knowledgeably about how a system works. Trigger
  this even when the user only says they want to "document the codebase" or "understand"
  an unfamiliar repo, and even if they don't use the words "study guide," "flashcards," or
  "skill."
---

# Codebase Study Guide

This skill produces a consistent set of study documents for an existing codebase by reading
the actual code and writing markdown into the repository's `docs/` folder. It is designed
for a mixed technical audience: detailed enough for engineers, readable enough for support
and ops staff who need to reason about the system without living in the code.

The output is four artifact types: an **architecture overview**, **per-module deep dives**,
a **glossary**, and **Anki-ready flashcards** derived from the prose.

## Core principle: stay grounded

LLM-written documentation fails in one specific way — it produces confident, fluent prose
that describes code that doesn't exist or behavior that's subtly wrong. For study material
meant to train a team, a plausible-but-wrong doc is worse than no doc, because people trust
it. Every rule below exists to prevent that.

- **Read before writing.** Never describe a file, function, or flow you have not opened.
  Work from the repository on disk, not from memory or from the filename alone.
- **Cite sources.** Every non-obvious claim names the file (and where useful, the symbol or
  line range) it came from, e.g. `(src/auth/session.py: refresh_token)`. This lets a human
  reviewer verify in seconds and makes staleness detectable later.
- **Separate *what* from *why*.** What the code does is verifiable — state it plainly. Why
  it was built that way usually is not knowable from the code, so do not invent a rationale.
  Mark inferences explicitly: "Appears to…", "Likely…", or place it under *Open questions*.
- **Flag unknowns instead of smoothing them over.** If a flow is unclear, a name is
  cryptic, or two parts seem to contradict, say so in an *Open questions / verify with an
  SME* section. These flags are where a reviewer's time is best spent.
- **Record provenance.** Put a header on every generated doc with the generation date and
  the commit hash (`git rev-parse --short HEAD`) so readers can tell when it's gone stale.

## Workflow

Follow these phases in order. For a large codebase, the early phases keep the work scoped
and reviewable rather than producing one giant unverifiable pass.

### Phase 1 — Reconnaissance

Before writing anything, build a factual picture of the repo:

- Detect languages, the build system, and the dependency manifest(s) (`package.json`,
  `pyproject.toml`, `go.mod`, `pom.xml`, etc.).
- Find the entry points: `main`, server bootstrap, CLI definitions, route registrations,
  job/worker schedulers, lambda handlers.
- Map the top-level directory layout and identify candidate **modules/subsystems** (a
  module is a coherent unit of responsibility — often a top-level package or service dir).
- Note testing setup, config files, and any existing docs to avoid duplicating them.

Use fast tools to orient: list the tree, read the manifest, grep for entry points. Do not
read every file yet.

### Phase 2 — Plan and scope

Produce a short **module inventory**: a list of the modules you found, each with a one-line
guess at its responsibility and its path. If the codebase is large (say, more than ~10–15
modules), present this inventory to the user and ask which areas to prioritize, or proceed
entry-point-first (cover the core request/data paths before peripheral utilities). Confirm
the scope before generating deep dives so effort lands where it's useful.

### Phase 3 — Architecture overview

Write the top-down document first; it anchors everything else. Read
`references/architecture-overview.md` for the template and fill it from what you actually
trace through the code. The centerpiece is a real end-to-end walk of one primary path
(e.g. an incoming request to its response), grounded with file references at each hop.

### Phase 4 — Module deep dives

For each in-scope module, read its key files and write one deep-dive doc using the template
in `references/module-deep-dive.md`. Work module by module — finishing and grounding one
before starting the next keeps each pass small enough to actually verify, and stops errors
from compounding across the whole guide.

### Phase 5 — Glossary

As you go, collect domain terms, internal jargon, acronyms, and named code constructs that
a newcomer wouldn't recognize. After the deep dives, consolidate them using
`references/glossary.md`. Distinguish business/domain terms from code constructs, and point
each to where it appears.

### Phase 6 — Flashcards

Derive flashcards **from the documents you just wrote**, not as a separate invention — this
keeps the cards consistent with the verified prose. Follow `references/flashcards.md` for
the Anki-ready format. Favor cards that test understanding ("What does the session service
do when a refresh token is expired?") over trivia ("What line is X on?").

### Phase 7 — Index and verification checklist

Write `docs/study-guide/README.md` as the entry point: what's here, suggested reading order,
and how to import the flashcards. Then collect every *Open questions / verify with an SME*
item from all docs into a single checklist at the bottom of the README, so a subject-matter
expert has one place to review and correct before the team relies on the material. This
review pass is the human-in-the-loop that makes the whole thing trustworthy.

## Output location and structure

Write everything under `docs/study-guide/` in the repository:

```
docs/study-guide/
├── README.md                     # index, reading order, SME verification checklist
├── 00-architecture-overview.md
├── modules/
│   ├── <module-name>.md          # one per module
│   └── ...
├── glossary.md
└── flashcards/
    └── <module-or-topic>.txt     # tab-separated, Anki-ready
```

Create directories as needed. If `docs/` already holds project documentation, nest under
`docs/study-guide/` as shown rather than scattering files at the top level. Re-running the
skill should overwrite these generated files cleanly; do not hand-edit them outside the
skill, since the SME corrections belong in the verification checklist (which feeds the next
regeneration) rather than in the generated prose.

## Templates

Read the relevant reference file before writing each artifact — they contain the exact
structure to follow and worked guidance:

- `references/architecture-overview.md` — system overview + grounded lifecycle walk
- `references/module-deep-dive.md` — per-module structure
- `references/glossary.md` — term entry format
- `references/flashcards.md` — Anki TSV format and import steps
