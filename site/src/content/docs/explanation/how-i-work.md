---
title: How I work
description: How I take work from an idea to merged pull requests, how I choose between one issue, an epic and a burndown, and where I stay in the loop.
sidebar:
  order: 1
---

This page describes the whole lifecycle once, in the order I do it. The other pages
in this section go deeper on single decisions. The how-to guides have the steps.

## Where work starts

Usually with an idea that I brainstorm with the agent. The brainstorm produces a
spec, and the spec produces a plan.

Sometimes I write an `IDEA.md` first and paste it in at the start of the
conversation. It holds the problem, the goal, and prior art with links. It
doesn't hold constraints or a rough design. The design comes out of the
brainstorm, and the file only frames the problem and points at related work.

## How I choose a workflow

Once there's a spec, I pick by size and shape:

- **A single change** goes from one issue to one PR, with `github-issue-to-pr`.
- **Planned work in several tasks** becomes an epic, run by subagents. I use
  `github-milestone-plan-to-issues` to write the plan and file the issues, and
  `github-epic-to-merged-prs` to run them.
- **Independent items in the backlog** get burned down one at a time with
  `github-issue-burndown`.

I explain burndown [in its own section](#how-i-burn-down-a-backlog) below. This
page only touches on the claims audit that
[`github-issue-to-pr`](/pg-skills/reference/skills/github-issue-to-pr/) runs before it
opens a PR ([why I audit](/pg-skills/explanation/why-audit-claims/), [how to run
it](/pg-skills/how-to/validate-a-change/); it needs
[claims-audit](/pg-skills/reference/dependencies/#claims-audit) and, for ledger mode
only, [claims-mcp](/pg-skills/reference/dependencies/#claims-mcp)), the
[study guides](/pg-skills/reference/plugins/study-guides/) and the supporting setup (the
[knowledge catalog](/pg-skills/reference/dependencies/#telekin), model policy and
machine rules).

## What I read and what I approve

I approve the spec and not the plan. Once the spec is right I don't read the plan.
Two things catch plan problems for me: Brooke's review of the plan PR, and the
gates that every sub-issue has to pass.

Accepting the sub-issue breakdown in plan mode is a step I don't use as much
anymore. When I did, I usually just trusted it. `github-milestone-plan-to-issues` files one
sub-issue per plan task, so the breakdown it shows in plan mode follows the plan one to
one, and there is little left to review.
`github-issue-to-subissues` still runs inside it. On its own it's for an epic
that has no checked-in plan.

## My checkpoints

When I let the coordinator run an epic, I stay in four places:

1. accepting the spec;
2. accepting the sub-issue breakdown, if it asks;
3. real design questions that the design leaves open;
4. the final merge into `main`.

Under a standing merge authorization the rest runs on its own: implementing,
answering Brooke, and merging sub-issue PRs into the milestone branch. The
[execute-an-epic guide](/pg-skills/how-to/execute-an-epic/) says what that
authorization covers.

## When I curate instead

It depends on the project. Sometimes I use those checkpoints as listed. Other
times I curate the process issue by issue with `github-issue-to-pr`: I run it on
one issue, look at the PR, and only then start the next one.

I curate when the project is new or risky, or when the design is still moving. The
skills don't describe this as a mode. It's a choice I make, and you can make it
too. The
[tutorial](/pg-skills/tutorials/first-issue-to-merged-pr/) is one pass of it.

## How I burn down a backlog

A burndown is for independent items in the backlog.
[`github-issue-burndown`](/pg-skills/reference/skills/github-issue-burndown/) takes the
open issues labelled `accepted`, highest priority first, and carries each one to a
merged PR. I run it during unattended stretches, and when the backlog piles up. The
[how-to guide](/pg-skills/how-to/burn-down-the-backlog/) has the steps.

**Why `accepted` is my gate.** In my words: "Sometimes I make an issue, sometimes an
agent makes an issue, either way I read, groom if needed, then apply the label." The
issue might come from me, from an implementer or from a review bot's follow-up. Nothing
enters the queue until I have read it. If the burndown could label its own follow-ups,
it would feed itself, so the skill files them without `accepted` and I decide which
ones to take. I [groom](/pg-skills/how-to/groom-an-issue/) an issue only when it is too
vague for an agent to implement unattended.

**How it works serially.** The skill's rule is one issue at a time, start to merge, and
it carries a note that it is mine. Each PR targets the default branch, with no
milestone branch, and the next worktree is cut from the default branch after the last
merge. The coordinator also asks for the next issue again after every merge, so an issue
I label `P0` while it runs goes next.

**What I do with blocked issues.** The skill stops at a `burndown-blocked` label and a
comment. After that I do this: "I usually ask claude in a separate session to work
interactively with me on the issue so we can get it either fixed for resume, or pushed
manually." The how-to guide has that step under
[taking a blocked issue to an interactive session](/pg-skills/how-to/burn-down-the-backlog/#take-a-blocked-issue-to-an-interactive-session).

For the planning side that feeds a backlog, see
[plan a feature](/pg-skills/how-to/plan-a-feature/),
[split an issue](/pg-skills/how-to/split-an-issue/) and
[plan a milestone](/pg-skills/how-to/plan-a-milestone/).

## How the work gets reviewed and finished

Each PR gets a review. For me that's Brooke, my review bot. I explain what she
checks, and what to use if you don't have one, in
[Why a review bot](/pg-skills/explanation/review-bot/). An epic's PRs merge into a
milestone branch, one agent per issue, for reasons I give in
[Why one subagent per issue](/pg-skills/explanation/one-subagent-per-issue/).

When every sub-issue has merged, I run `github-epic-close-out` before the
milestone goes to `main`, and again after. It checks the epic against its plan and
design, because "all sub-issues are closed" isn't evidence that the work was
delivered.

## A worked example

This repository's own first milestone, [epic #3](https://github.com/PeterGrace/pg-skills/issues/3),
took the epic path on this page. It had ten sub-issues, one PR each, merged into
`milestone/3-workflow-site`, then the milestone PR
[#25](https://github.com/PeterGrace/pg-skills/pull/25) into `main`. The
[pre-merge audit](https://github.com/PeterGrace/pg-skills/issues/3#issuecomment-7063515563)
and the [final audit](https://github.com/PeterGrace/pg-skills/issues/3#issuecomment-7063711827)
are comments on the epic.

## Where I run it

On one shared workstation, in Claude Code in a terminal, often on several projects
at once. That is why the skills have rules about worktrees, build caches, gate locks
and killing processes by PID only.
