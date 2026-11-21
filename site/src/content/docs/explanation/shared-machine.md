---
title: "Working on a shared machine: worktrees, caches, gate locks"
description: Why the skills give each agent its own worktree, bound and serialize heavy gates, watch the disk, and leave other sessions' processes and caches alone.
sidebar:
  order: 8
---

I run Claude Code in a terminal on one shared workstation, often for several projects
at once. Agents, my own sessions and other projects' builds all share one CPU, one
disk and one process table. The skills have a set of rules for that, and I trace each
rule after the worktree one to an incident. This page explains the rules. They sit in the [`issue-implementer`](/pg-skills/reference/agents/issue-implementer/)
agent's standing rules and in the coordinator skills.

## The worktree per agent comes first

I was asked which rule matters most to someone copying this setup. My answer, in full:
"Worktree per agent is table stakes but the rest of these are also incredibly
important, they're equally important but the worktree per agent is first among equals
for sure."

So read the rest of this page as equally important.

Each sub-issue gets its own agent, its own git worktree and its own PR. The coordinator
skills create the worktree with `git worktree add` from the base branch, and say:
"Never reuse another agent's worktree." The implementer agent works only in the
worktree its brief names, on the branch it names, and never `cd`s into the main
checkout or another worktree. Its logs go inside that worktree, for example under
`target/i<issue>-logs/`, because agents that shared a log directory reported each
other's test counts. Even the git stash is shared, so the agent never uses a bare
`git stash`: the stash stack is shared with other sessions.

## Bound and serialize the gates

A project's gates are its format, lint and test commands, and they must be green
before an agent pushes. On a shared machine they compete for the same CPU and disk.
The agent definition handles this three ways:

- If the project has a shared gates lock, every heavy gate, long test run, image build
  and kind cluster runs through it. For autobots, one of my repositories, that is
  `flock -o <lock file> nice -n 19 ionice -c3 <command>`: the lock serializes the run,
  and `nice` and `ionice` lower its CPU and I/O priority.
- A fresh worktree's first build is cold, so any cargo build the agent runs itself
  gets `--jobs 4`.
- The agent doesn't run the kind smoke test locally, because it takes about 40
  minutes. The one exception is an issue about the Helm chart, the images or cluster
  behaviour, and then only when the brief asks for it. CI runs it nightly (pgrace,
  2026-11-15).

The coordinators add their own limits. In the epic skill, parallel issues start only
when they touch different files, and the plan's Files lists say which. The burndown
skill goes further and works one issue at a time. The epic skill's brief also says
"Don't add CPU load."

One mistake in the epic skill's table comes from waiting badly. Waiting with
`until ! pgrep -f "just lint"` "matches every session's runs, so it can wait forever".
The fix is to wait for your own job's exit or its output file.

## Mind the disk

Build caches are per worktree. My cargo config sets `build-dir` so each checkout builds
in its own directory outside it, and `git worktree remove` doesn't delete that
directory. The skills record the size: 30-47 GiB per agent worktree on one of my
repositories' epics, where "the disk filled twice in a day", and 30-60 GiB in the
burndown skill and the glossary.

So before a worktree is removed, its build output is deleted. If the repository has
its own script for that, the skills use it. Otherwise, in a Rust repository, they run
`cargo clean` in the worktree first, bounded with `timeout 10m`, and then
`git worktree remove`. The implementer doesn't do this itself, since its definition
says "Don't run `cargo clean` and don't remove the worktree; the parent does that after
merge." The coordinator doesn't clean while the agent or anything else is still running
in that worktree. The
[glossary entry](/pg-skills/reference/glossary/#cargo-build-dir-and-cargo-clean-before-removing-a-worktree)
says this is harmless if you build into `target/`.

The same care covers containers. The agent leaves no container or kind cluster
running, and removes images it built that aren't needed.

## Don't touch other sessions' processes or caches

These rules protect other sessions' work:

- **Kill by PID only.** "Kill only PIDs you started; never kill by pattern." The
  skills' mistakes table records why: an agent's `pkill -f <binary>` killed other
  agents' test servers.
- **No machine-wide prunes.** The agent removes only the image and container IDs it
  created, and never runs `docker builder prune`, `docker system prune`,
  `docker image prune` or `docker volume prune`. The build cache and images are shared
  with every other session, and the agent definition records that "a builder prune once
  wiped 182 GB of shared cache."
- **Don't print process command lines.** The burndown skill's brief says never to print
  full command lines (`ps -f`, `pgrep -a`, `/proc/*/cmdline`), because on my machine a
  container tool's exec arguments carry secrets, and printing them puts them in the
  transcript. It says to use `ps -o pid,etime,comm` instead.

## Where this is written down

- The standing rules for implementers:
  [`issue-implementer`](/pg-skills/reference/agents/issue-implementer/).
- Cleanup and the brief's shared-machine section:
  [`github-epic-to-merged-prs`](/pg-skills/reference/skills/github-epic-to-merged-prs/)
  and [`github-issue-burndown`](/pg-skills/reference/skills/github-issue-burndown/).
- The worktree cleanup note for a single issue:
  [`github-issue-to-pr`](/pg-skills/reference/skills/github-issue-to-pr/).

Those skills need [git](/pg-skills/reference/dependencies/#git) and
[gh](/pg-skills/reference/dependencies/#gh). `github-issue-to-pr` also needs
[just](/pg-skills/reference/dependencies/#just) and
[claims-audit](/pg-skills/reference/dependencies/#claims-audit), and can use
[claims-mcp](/pg-skills/reference/dependencies/#claims-mcp). The coordinators need a
[review bot](/pg-skills/reference/dependencies/#review-bot), and `github-issue-burndown`
also needs [jq](/pg-skills/reference/dependencies/#jq). The glossary's entries on
[okf_mcp and autobots](/pg-skills/reference/glossary/#okf_mcp-and-autobots) say what to
do with my repositories' quirks that appear in the text.
For how to adapt these rules to your machine, see
[Adapt the skills to your setup](/pg-skills/how-to/adapt-the-skills/).
