---
title: Split an issue into sub-issues
description: Break a large epic issue that holds a multi-phase plan into nested, ordered sub-issues with github-issue-to-subissues, when there is no checked-in plan.
sidebar:
  order: 4
---

This guide fans one large issue out into sub-issues, using the
[github-issue-to-subissues](/pg-skills/reference/skills/github-issue-to-subissues/)
skill. Use it on its own for an epic whose plan lives in the issue body, with no
checked-in plan document.

If you have a design document with milestones, don't use it directly. Follow
[plan a milestone](/pg-skills/how-to/plan-a-milestone/): the
[github-milestone-plan-to-issues](/pg-skills/reference/skills/github-milestone-plan-to-issues/)
skill writes the plan, files the epic and runs `github-issue-to-subissues` for you,
with one sub-issue per plan task.

You need the `github-workflows` plugin
([install commands](/pg-skills/reference/plugins/github-workflows/)),
[git](/pg-skills/reference/dependencies/#git) and
[gh](/pg-skills/reference/dependencies/#gh) with a token that can write issues.

## Before you start

The parent issue should contain a plan with phases. Explicit `## Phase 1` headings
are the easy case. A numbered or bulleted implementation sketch works, and with an
unstructured prose plan the skill proposes a decomposition and says it is inferring.

If the parent is rough rather than phased,
[groom it](/pg-skills/how-to/groom-an-issue/) first. Grooming shapes a too-big body
with explicit phases and hands off to this skill.

## Steps

1. Ask for it by name: "Break issue 12 into sub-issues." Give a full URL if the issue
   is in another repository.
2. The skill reads the parent, its comments and any sub-issues it already has. If
   children exist, it assumes it has run before and asks whether to add more or stop.
   If some phases are filed and some aren't, it proposes only the missing ones.
3. Review the breakdown in plan mode. It shows a recap of the parent, an ordered list
   of sub-issues with exact titles, scope, labels and whether each depends on the
   previous one, the dependency graph if it isn't a straight line, and anything it chose
   not to split out. It aims for 2 to 6 sub-issues, and stops if the plan is too small
   to split.
4. Accept, reject or edit the breakdown. If you edit it, for example by merging two
   phases, it shows the result again. Nothing is filed until you accept.
5. Let it file the sub-issues in phase order. Titles follow `<parent title>: <phase
   summary>`. Each body links to the parent with a `Part of #N` line, carries scope,
   validation and out-of-scope sections, and points at the plan rather than copying
   from it. Labels and the milestone are inherited from the parent where that
   makes sense. Nobody is assigned.
6. It nests each sub-issue under the parent with GitHub's sub-issues API, so the parent
   shows a progress bar.
7. It orders the phases with "blocked by" dependencies, applying the plan's real
   graph and not forcing a chain when phases can run in parallel.
8. It posts an index comment on the parent: a checklist of the sub-issues in order. It
   doesn't edit the parent's body.
9. Read the edges back to check them:
   `gh api repos/{owner}/{repo}/issues/<N>/dependencies/blocked_by`. The direction is
   easy to flip: the issue in the path is the blocked one.

## What to know about the ordering

GitHub dependencies are advisory. The tracker shows the relationship and lets you
search for blocked issues, but it doesn't stop anyone from working on or merging a
blocked one. The skill says so in the index comment.

If the sub-issues or dependencies API isn't available, for example on an older
GitHub Enterprise Server, the skill doesn't stop. It makes the "Blocked by" line in
each sub-issue and the checklist on the parent carry the order, and says in its report
that the edges weren't set.

## Next

The skill reports the sub-issue numbers and the nesting and dependency status. Run
`github-issue-to-pr` on the first sub-issue, or hand the epic to
[execute an epic with subagents](/pg-skills/how-to/execute-an-epic/).
