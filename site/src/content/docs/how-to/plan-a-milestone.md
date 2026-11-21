---
title: Plan a milestone into an epic and sub-issues
description: Turn the next milestone of a design document into a reviewed plan, an epic and one sub-issue per task with github-milestone-plan-to-issues.
sidebar:
  order: 1
---

This guide takes a milestone from your design document to a merged plan PR, an epic
issue and one sub-issue per plan task. It uses the
[github-milestone-plan-to-issues](/pg-skills/reference/skills/github-milestone-plan-to-issues/)
skill. It assumes you have a design document that lays out milestones or phases, and
the `github-workflows` plugin installed
([install commands](/pg-skills/reference/plugins/github-workflows/)).

The plan is the single source of truth. The epic and the sub-issues give scope and
acceptance only, never code.

## Before you start

- Check the design is right. This is the part I read closely: I approve the spec and
  not the plan.
- The skill writes the plan with the `writing-plans` skill from the
  [superpowers](/pg-skills/reference/dependencies/#superpowers) plugin, so install that too.
- Have a recent plan and changelog from an earlier milestone, if there is one. The
  skill copies its conventions.

## Steps

1. In Claude Code, in the repository, ask for it by name: "Plan milestone 2 from
   `docs/DESIGN.md`." The skill works in a fresh worktree off `origin/main`.
2. Let it gather the inputs: the milestone's section and every design section it
   references, the previous plan and changelog, open follow-up issues from earlier
   milestones, and the code as it is on `origin/main`.
3. Expect it to check the facts the plan depends on. Each external API the plan uses is
   confirmed against its real source, and recorded with a file and line in a
   "Verified facts the code relies on" section.
4. Answer its design questions. It asks only about choices the design leaves open,
   at most four per call, each with a recommended option. Your answers go in the
   plan's "Decisions taken while planning" section.
5. Review the plan PR. The skill saves the plan under `docs/superpowers/plans/`,
   opens the PR on a `docs-milestone-<N>-plan` branch and waits for your reviewer.
   It addresses the review with `github-address-pr-review`.
6. Merge the plan PR, or say the skill may merge plan PRs. It doesn't merge unless
   you've authorized that. Don't file issues before the plan is on `main`,
   because the issues link to it there.
7. Let it file the epic, with the labels `epic` and `milestone-<N>`. The body is prose
   with no code: goal, in scope, decisions, what's deferred, and how to work the
   sub-issues in parallel.
8. Accept the sub-issues in plan mode. The skill runs `github-issue-to-subissues`
   with one sub-issue per plan task, titled `M<N>.<NN>: <task title>`. It nests them
   under the epic, sets blocked-by edges from the plan's dependency graph, and posts an
   index comment.
9. Read the edges back. The skill does this, and it's worth a glance:
   `gh api repos/{owner}/{repo}/issues/<N>/dependencies/blocked_by`.

The skill ends by reporting the plan path and PR, the epic URL, the sub-issue
numbers with the dependency graph, and which tasks can start now.

## What the plan must have

The skill won't skip these, but check them in the plan PR:

- a file map saying which task touches which file, because the executor uses it to
  tell which tasks can run in parallel;
- a real dependency graph rather than a linear chain;
- one task per carried-over follow-up, named with its issue number;
- the rule that the plan's code hasn't been compiled and that a divergence is fixed in
  the plan, in the same PR, with a dated note.

## Next

[Execute the epic](/pg-skills/how-to/execute-an-epic/). To see a finished example,
look at [epic #3](https://github.com/PeterGrace/pg-skills/issues/3) and its
[index comment](https://github.com/PeterGrace/pg-skills/issues/3#issuecomment-7062971780).
