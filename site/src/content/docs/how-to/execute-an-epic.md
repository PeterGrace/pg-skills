---
title: Execute an epic with subagents
description: Run github-epic-to-merged-prs to carry an epic's sub-issues to merged pull requests on a milestone branch, and avoid the failures that happen most often.
sidebar:
  order: 5
---

This guide runs an epic's sub-issues to merged PRs with the
[github-epic-to-merged-prs](/pg-skills/reference/skills/github-epic-to-merged-prs/)
skill. You are the coordinator's user: the skill coordinates, and an
[issue-implementer](/pg-skills/reference/agents/issue-implementer/) subagent
implements each issue. You need an epic whose sub-issues exist and are linked by
blocked-by edges, and a [review bot or a human reviewer](/pg-skills/reference/dependencies/#review-bot)
for the PRs. If you don't have an epic,
[plan a milestone](/pg-skills/how-to/plan-a-milestone/) first.

For the reasoning, read
[Why one subagent per issue](/pg-skills/explanation/one-subagent-per-issue/).

## Steps

1. Ask for it in Claude Code: "Execute epic 3." The skill first checks that the
   sub-issues exist, who reviews, what the gates are, and whether you've authorized
   merging.
2. Name your reviewer if the skill can't find one. It looks at recently merged PRs
   for the reviewer's login. A bot's login ends in `[bot]`. With no reviewer it asks
   whether to merge without a review.
3. Decide on merge authorization. A standing authorization covers merging sub-issue
   PRs into the milestone branch. The final merge into `main` needs your go-ahead at
   that time, unless you've said the standing authorization covers it. Without any
   authorization the skill runs each PR up to "review addressed, CI green" and reports
   it ready for you to merge.
4. Let it cut the milestone branch, `milestone/<epic>-<slug>`, from `origin/main` after
   the plan PR has merged. It posts the name on the epic and puts it in every brief.
5. Check CI and the reviewer. CI must run on PRs into a branch other than the default,
   and the reviewer must review them. If a workflow's `pull_request.branches` lists
   only `main`, the skill stops and asks you, because changing CI config is a repo
   change.
6. Let the loop run. For each ready issue, whose blockers have all merged, the skill:
   - creates a worktree from the milestone branch;
   - starts an `issue-implementer` in the background, on Sonnet;
   - waits for the review;
   - tells the same agent to run `github-address-pr-review`;
   - checks the base, CI on the new head, the review and the replies, and merges
     with a merge commit;
   - closes the sub-issue itself, and cleans up the worktree.
7. Keep your context small. The skill keeps a state file under the repository's git
   directory, `coordinator/epic-<epic>.md`. At each checkpoint it ends its message
   with a line like this for you to paste:
   `/compact Continue github-epic-to-merged-prs <epic> from <state file>. Keep agent ids, open PRs and their next actions.`
   The checkpoints are the end of planning, every third merge, and before the
   close-out. It can't run `/compact` itself.
8. When the last sub-issue merges, the skill removes leftover worktrees and runs
   [`github-epic-close-out` in pre-merge mode](/pg-skills/how-to/close-out-an-epic/).
   It opens the milestone PR from the milestone branch into `main` only if the audit
   validates.
9. Give the go-ahead for the final merge, and the skill merges with a merge commit,
   never a squash or a rebase. It then re-runs the close-out against `main`, which closes
   the epic, and deletes the milestone branch.

## Start on Sonnet

Leave the model off. Implementers start on Sonnet. Opus only takes over a PR on a
recorded trigger:

- the reviewer marks a security problem blocking and the score drops under 80;
- two Sonnet address rounds are done and the review on the new head is still
  blocking;
- the agent has failed twice to get CI or the gates green on its own changes.

An agent that reports a sub-issue as ambiguous isn't a trigger. That comes to you.

## What goes wrong most often

I named four. Each one has a recorded incident, and most have a rule in the skill.

- **Cost and context.** Opus implementers and large coordinator contexts use up the
  weekly limit. Start on Sonnet, use the state file, and compact at the checkpoints.
- **Stalled reviews.** The reviewer skips a stale branch or misses a request, and the PR
  sits. Read the bot's issue comments on the PR first, because a skip is usually
  explained there. For a stale branch, have the PR's agent run
  `git merge origin/<milestone branch>` (never rebase) and push. If the bot has a
  re-trigger command, use it when no review shows up. Don't use it on an unchanged
  head: Brooke won't re-review one (see
  [Answer review comments](/pg-skills/how-to/answer-review-comments/)).
- **Machine overload.** Too many agents, gates or build caches at once. Start
  parallel issues only when they touch different files. Run heavy gates through a
  lock if the project has one, and run `cargo clean` in a worktree before you remove
  it.
- **Scope creep.** Follow-ups and audit findings grow the epic past the plan. Decide which
  follow-ups belong in the epic, and ask once, in a batch. The close-out lists
  follow-ups and files them only when you say so, or said so earlier in the session.

## A worked example

Epic [#3](https://github.com/PeterGrace/pg-skills/issues/3) ran this way: ten
sub-issues, each merged into `milestone/3-workflow-site` by its own PR, then the
milestone PR [#25](https://github.com/PeterGrace/pg-skills/pull/25) into `main` with
a merge commit.
