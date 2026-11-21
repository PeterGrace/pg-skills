---
title: The knowledge catalog as long-term memory
description: Why I keep a shared, reviewed knowledge catalog beside CLAUDE.md and built-in memory, what the skills read from it and write to it, and what you can do without one.
sidebar:
  order: 7
---

Beside the skills in this repository, I keep a knowledge catalog: notes about my
systems, projects, people and processes, in Open Knowledge Format, served to agents
over MCP by [Telekin](/pg-skills/reference/dependencies/#telekin). I use it as my
agents' long-term memory. This page says why, and what the skills do with it. You
can't read my catalog, and the skills work around that.

## Why I don't stop at CLAUDE.md and built-in memory

The catalog gives me four things those two don't. In my words: "It enriches essentially every interaction I have
with an LLM these days."

- **Shared across projects.** Every session and project reads the same place.
- **Reviewed and versioned.** Writes go through changesets, and there is history and
  revert. I can audit what an agent wrote and undo it.
- **Lessons compound.** A failure in one project becomes a rule that later sessions
  see, in every project.
- **Works beyond Claude Code.** Any MCP harness can read and write it, even one without
  a filesystem.

## What the skills do with it

Four skills in `github-workflows` point at the catalog. Each one lists it as
optional in `catalog.yaml`.

- [`github-milestone-plan-to-issues`](/pg-skills/reference/skills/github-milestone-plan-to-issues/)
  and [`github-epic-to-merged-prs`](/pg-skills/reference/skills/github-epic-to-merged-prs/)
  tell the session to read the catalog's write-up of the subagent PR workflow, and the
  project's own concept, before starting. The epic skill takes the reviewer, gates and
  quirks of a project from the project's concept, and it records the merge
  authorization you gave there.
- [`github-issue-burndown`](/pg-skills/reference/skills/github-issue-burndown/)
  has the same background reading. It notes the run in the project's concept, and keeps
  a security weakness found in a public repository out of the public issue tracker and
  in the catalog.
- [`github-epic-close-out`](/pg-skills/reference/skills/github-epic-close-out/)
  records the outcome as one dated line in the project's concept, with a log entry.

At the end of an epic the coordinator records what it learned: flakes, root causes,
decisions and the reviewer's quirks, and it puts anything left unfixed in the
catalog's list of things to fix. The coordinator skills batch catalog updates into one
changeset per checkpoint, not one per PR.

## What this looks like on a real epic

Brooke, my review bot, has habits that cost time until someone writes them down. She
skips a branch that is behind its base. She doesn't re-review a head that hasn't
changed. I had learned both on earlier projects, and both were already in the catalog
when epic [#3](https://github.com/PeterGrace/pg-skills/issues/3) ran. The skills now carry the same two rules in
their own text: the epic skill says to read the bot's issue comments when no review
arrives, and the burndown skill treats an explain-only round on an unchanged head as a
disagreement, because she can't re-review it.

## Telekin and okf_mcp

Telekin serves catalogs like mine over MCP. It is built on
[hypotheosis/okf_mcp](https://github.com/hypotheosis/okf_mcp), an open-source server
you can host yourself. The
[dependencies page entry](/pg-skills/reference/dependencies/#telekin) says what each
is. The catalog the skills point to is mine and private. The skills name some of its
concepts, such as a workflow write-up, so you will see paths in their text that you
can't open.

## If you don't have one

Skip those pointers, or point them at your own notes. The
[glossary entry](/pg-skills/reference/glossary/#the-knowledge-catalog-telekin-okf)
says the same. [Adapt the skills to your setup](/pg-skills/how-to/adapt-the-skills/#decide-what-to-do-about-the-knowledge-catalog)
has the steps.

## What the skills here need

What each skill needs is on the [dependencies page](/pg-skills/reference/dependencies/).
