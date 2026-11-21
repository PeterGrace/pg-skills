---
title: Burn down the accepted backlog
description: Work the open issues labelled accepted to merged pull requests one at a time with github-issue-burndown, and take blocked issues to an interactive session.
sidebar:
  order: 6
---

This guide works through a repository's open issues labelled `accepted`, one at a
time, highest priority first, to merged PRs. It uses the
[github-issue-burndown](/pg-skills/reference/skills/github-issue-burndown/) skill. You
coordinate; an [issue-implementer](/pg-skills/reference/agents/issue-implementer/)
subagent implements each issue in its own worktree, and the review bot reviews each PR.

For why it is built this way, read
[How I work](/pg-skills/explanation/how-i-work/#how-i-burn-down-a-backlog).

## When a burndown fits

Use it for independent items in a backlog, and in two situations: you will be away for
a stretch and want the queue to keep moving, or the backlog has piled up. For planned
work in several tasks, [execute an epic](/pg-skills/how-to/execute-an-epic/) instead.

## What you need

- The `github-workflows` plugin
  ([install commands](/pg-skills/reference/plugins/github-workflows/)).
- [gh](/pg-skills/reference/dependencies/#gh),
  [just](/pg-skills/reference/dependencies/#just) and
  [jq](/pg-skills/reference/dependencies/#jq). The skill's scripts parse GitHub API
  JSON with `jq`.
- A [review bot](/pg-skills/reference/dependencies/#review-bot) that reviews the
  repository's PRs. The scripts are written for my bot, Brooke, so with another
  reviewer you will need to adapt them.
- The [`claims-audit`](/pg-skills/reference/dependencies/#claims-audit) skill, which the
  implementers' `github-issue-to-pr` runs for its audit step.
- The `accepted` label, and issues that carry it.

## Prepare the queue

The burndown works what you have labelled `accepted`, and nothing else. The label is
your decision, whoever filed the issue: you, an implementer's follow-up or a review
bot's suggestion.

1. Read each issue before you label it.
2. If an issue is too vague for an agent to implement unattended,
   [groom it](/pg-skills/how-to/groom-an-issue/) first.
3. Add `accepted`.
4. Optionally set a priority. The skill ranks by GitHub's `Priority` issue field
   (Urgent, High, Medium, Low) and by priority labels such as `P0`, `P1` and
   `priority: high`. The higher of the two wins. An issue with no priority ranks as
   Medium, and ties go to the oldest.

An issue titled "Decide: ..." is workable only after you have commented a decision.
Without one, the skill marks it stuck: it labels the issue `burndown-blocked`,
comments with the question and takes the next issue.

## Steps

1. Ask for it by name: "Burn down the accepted issues." The skill takes a repository
   (default: the current checkout's), a label (default `accepted`) and an optional
   `--max N` to cap the issues in this run.
2. Understand what invoking it authorizes. It may merge its own PRs into the default
   branch once its merge script passes. It doesn't authorize merging anything else, or
   bypassing the script.
3. Let it check the repository. It stops and asks if the review bot hasn't reviewed a
   recent PR, because merging unreviewed isn't the deal. It finds the lint and test
   commands, checks whether PRs get CI, and reads the branch rules. If the
   rules require review threads to be resolved, a PR stays blocked until they are.
   It creates the `burndown-blocked` label if it doesn't exist.
4. Check the queue, if you like, before you start. The skill's `next-issue.sh --list`
   shows every candidate in pick order with its rank. It skips the open-PR and
   branch checks, so it can list an issue that a real run would skip. An issue is eligible if it
   carries the label, doesn't carry `burndown-blocked`, isn't an epic, isn't assigned
   to someone else and has no open PR closing it. It also skips an issue that already
   has a branch or worktree, because another session is on it.
5. The skill picks the first issue, self-assigns it and creates a worktree from the
   default branch. It starts one implementer on Sonnet, which runs
   [github-issue-to-pr](/pg-skills/reference/skills/github-issue-to-pr/) on the issue.
6. It checks the PR itself: the base is the default branch, and the body names the
   issue it closes with a closing keyword. Then it waits for the bot's review of the current head.
7. It reads the review. A review is clean only when the latest review on the current
   head has no inline comments and doesn't ask for changes. There is no exception for
   nits. If it isn't clean, the same agent runs
   [github-address-pr-review](/pg-skills/how-to/answer-review-comments/), replies in
   every thread and pushes, and the skill asks for a re-review of the new head.
8. It merges through its merge script and not through a bare `gh pr merge`. The script
   refuses unless the head matches the branch tip, the review is clean, every review
   thread the bot opened has a reply, CI is green and the PR is clean to merge. It merges with a merge
   commit by default and pins the merge to that head.
9. It confirms the issue closed, files any follow-ups, removes the worktree, and
   picks the next issue. It asks `next-issue.sh` again each time and doesn't work from
   the first listing, so an issue you label `P0` mid-run goes next.
10. When nothing is left, or `--max` is reached, it checks the queue once more and
    reports a table: issue, PR, review rounds, final score, model, merged or stuck.

## One issue at a time

The skill starts the next implementer only after the current PR has merged or got
stuck. It doesn't prepare the next issue while a PR is open. Each PR targets the
default branch, with no epic and no milestone branch.

## When Opus takes over

Implementers start on Sonnet. Opus takes over a PR only on a recorded trigger:

- the review's security section has a blocking item and the score is under 80;
- two address rounds are done and the review is still not clean;
- two CI fixes have failed.

An implementer that reports the issue as ambiguous or too big isn't a trigger. That
issue is stuck.

## When it stops on an issue

The skill doesn't stop the whole run for one issue. It marks the issue stuck, cleans
up and takes the next one. It does this when:

- the implementer says the issue is ambiguous or too big;
- the review bot doesn't review after the skill asks three times;
- an address round changes no code, so you and the bot disagree on the same head;
- the review is still not clean at the round cap, which is reached at round 5 for a PR that has
  been on Opus;
- CI keeps failing after the fix attempts.

For a stuck issue the skill:

1. leaves the PR, if there is one, open with its branch in place;
2. adds `burndown-blocked` to the issue and removes its own assignment, so later runs
   skip it until a person removes the label;
3. comments on the issue with why it stopped, the PR link, the review's unresolved
   points and what a person needs to decide;
4. files any verified follow-ups.

## Take a blocked issue to an interactive session

The skill stops at the label. The next step is yours. Start a separate Claude Code
session and work through the issue with it interactively. I do this, and the session
ends one of two ways:

- **Fixed for resume.** You answer the decision, or make the small fix the comment
  asks for, and remove `burndown-blocked`. The next burndown picks the issue up again,
  provided no branch or open PR for it is left: the skill skips an issue that has one.
  When the stop left a PR open, close it and delete its branch first, or finish by hand.
- **Finished and pushed by hand.** You and the agent complete the work and push it
  yourselves, without the burndown.

Start from the issue's blocking comment: it says what the burndown found and what it
needs from you.

## Follow-ups don't enter the queue

The skill files a follow-up only when:

- the implementer or the review says something real is wrong or missing and out of
  scope for this PR;
- the skill checked it against the code and it is a concrete defect or gap, not a style
  preference;
- a search shows no existing issue for it;
- it isn't a security weakness in a public repository, which goes to private tracking
  and not to a public issue.

It doesn't add `accepted` to a follow-up. Accepting work is your call, and leaving the
label off keeps the burndown from feeding itself. Read the follow-ups in the report,
and label the ones you want.

## Keep the context small

A long burndown grows the coordinator's context, and every turn re-reads it. The skill
keeps its run state in a file under the repository's git directory, and after each issue
it ends its message with a `/compact` line for you to paste. It can't run `/compact`
itself. The compact loses nothing, because `next-issue.sh` rebuilds the queue from
GitHub.

## A worked example

[hypotheosis/okf_mcp](https://github.com/hypotheosis/okf_mcp) is a public repository
with 43 closed issues labelled `accepted`, and I can point to two of them and to one
blocked issue.

- [#266](https://github.com/hypotheosis/okf_mcp/issues/266) is labelled `accepted`.
  [PR #641](https://github.com/hypotheosis/okf_mcp/pull/641) fixed it and carried
  a closing reference to #266. The bot
  [reviewed it once](https://github.com/hypotheosis/okf_mcp/pull/641#pullrequestreview-5959114610)
  on the head, with a score of 96 and no inline comments. The PR merged with a merge
  commit less than a minute later.
- [#658](https://github.com/hypotheosis/okf_mcp/issues/658) went the same way through
  [PR #660](https://github.com/hypotheosis/okf_mcp/pull/660): one
  [review](https://github.com/hypotheosis/okf_mcp/pull/660#pullrequestreview-5966350107),
  a score of 94, no inline comments, then a merge commit.
- [#759](https://github.com/hypotheosis/okf_mcp/issues/759) is the blocked one, and it
  was blocked twice. The first
  [stop comment](https://github.com/hypotheosis/okf_mcp/issues/759#issuecomment-7031795111)
  says the burndown stopped before coding because the issue needed decisions it
  couldn't make. A
  [decision comment](https://github.com/hypotheosis/okf_mcp/issues/759#issuecomment-7043295277)
  came next, then `burndown-blocked` was removed, and
  [PR #806](https://github.com/hypotheosis/okf_mcp/pull/806) followed. The second
  [stop comment](https://github.com/hypotheosis/okf_mcp/issues/759#issuecomment-7045610519)
  says it stopped after three address rounds, with the PR left open and one review
  point unresolved. (That run used an earlier round cap; the current skill allows two
  Sonnet and two Opus rounds.) At the time of writing the issue still carries `burndown-blocked` and PR
  #806 is open.

The second stop shows what a good blocking comment holds: what the PR delivers, the
remaining point with its file, a suggested fix and what a human has to decide.
