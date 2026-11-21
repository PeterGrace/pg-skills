---
title: Why one subagent per issue
description: Why I give each sub-issue its own agent and worktree, and merge the pull requests into a milestone branch instead of main.
sidebar:
  order: 2
---

When I run an epic, each sub-issue gets its own background agent, its own git
worktree and its own PR. The PRs merge into a milestone integration branch
(`milestone/<epic>-<slug>`), and `main` gets the whole milestone in one final merge.
The coordinator, which is my main session, doesn't write the feature code. It picks
what runs next, writes each agent's brief, watches for reviews and CI, and merges.

This page is about why. The steps are in
[Execute an epic with subagents](/pg-skills/how-to/execute-an-epic/).

## A worktree and an agent per issue

A worktree per agent is table stakes, and it is first among equals. The rest of the
shared-machine rules are equally important, and each one came from an incident:

- **Logs stay in the agent's own worktree.** When agents shared a log directory,
  they reported each other's test counts.
- **Processes are killed by PID only.** An agent's `pkill -f <binary>` once killed
  other agents' test servers. A wait loop built on `pgrep -f` matched every
  session's runs, so it could wait forever.
- **Build caches go when the worktree goes.** On one of my Rust epics, each agent
  worktree left 30 to 47 GiB of build output behind, and the disk filled twice in
  a day. The coordinator runs `cargo clean` before it removes a worktree.

Two issues that edit the same files don't run in parallel. The plan's file lists tell
the coordinator which ones those are, and it serializes them.

## One agent keeps its context for the review

The agent that wrote a PR answers its review. It already holds the context: what the
issue asked, what it decided, what it ran. A fresh agent would have to rebuild
that. The one exception is an escalation to Opus, and then the new agent takes
over every later round.

The coordinator, by contrast, keeps its own context small on purpose. Every turn
re-reads the whole context, so a long run gets expensive. The skill keeps the
run's state in a file outside the tree so that a compacted or fresh session can
carry on.

## Why a milestone branch and not main

I gave three reasons in the interview:

- **`main` stays shippable.** Half a milestone never reaches `main` or a release, and
  I can still ship a hotfix while the milestone is open.
- **One final review.** Brooke and the close-out audit see the whole milestone at
  once, which catches problems that span PRs. On
  [PR #25](https://github.com/PeterGrace/pg-skills/pull/25) she found one that every
  sub-issue review had missed: the release skip could treat a large mixed change as
  docs-only. It was fixed in [#27](https://github.com/PeterGrace/pg-skills/pull/27),
  an extra sub-issue, before the merge.
- **It's easy to abandon.** If the milestone goes wrong, `main` is untouched.

The cost is bookkeeping. A closing keyword in a PR into a non-default branch doesn't
fire, so the coordinator closes each sub-issue itself after the merge. When `main`
moves, the coordinator brings it into the milestone branch through a sync PR so the
final merge stays small.

## Sonnet implements

The implementers run on Sonnet, and Opus only takes over on a recorded trigger. I do
this because of the usage limit, and to keep judgment at the top: planning, design
and coordination are where the stronger model pays off. Opus implementers had become
most of my weekly spend. In epic #3, no PR needed to escalate. That is an
observation about one small epic, not my reason. The full model policy gets its own
page later.

## What it costs

Machine load is the other thing that goes wrong. Too many agents, gates or build
caches at once will overload a workstation. The coordinator starts issues in parallel
only when they touch different files, and heavy gates run through a lock where the
project has one.
