---
title: Plan a feature into an issue
description: Turn a feature idea into one well-shaped GitHub issue with github-plan-to-issue, so github-issue-to-pr can implement it without re-deriving the design.
sidebar:
  order: 1
---

This guide takes a feature idea from conversation to one GitHub issue, using the
[github-plan-to-issue](/pg-skills/reference/skills/github-plan-to-issue/) skill. The
issue body is written so that
[github-issue-to-pr](/pg-skills/reference/skills/github-issue-to-pr/) can read it later
and go straight to implementation.

It fits a single feature that one PR can carry. For several tasks that run as an epic,
[plan a milestone](/pg-skills/how-to/plan-a-milestone/) instead. If the plan turns out
to be too big for one issue, the skill says so and suggests a split.

You need the `github-workflows` plugin
([install commands](/pg-skills/reference/plugins/github-workflows/)), and
[git](/pg-skills/reference/dependencies/#git) and
[gh](/pg-skills/reference/dependencies/#gh), authenticated.

## Steps

1. In Claude Code, in the repository, ask for it with a short seed: "Plan a feature:
   add caching to the config loader." The skill confirms which repository `gh`
   resolves to. If you name another repository, that one wins.
2. Let it read before it plans. It reads the files the idea touches, any pattern in
   the repository the idea refers to, and `README.md`, `CLAUDE.md` and the `justfile`
   or build file, to learn the project's validation commands. If the idea is
   ambiguous on fundamentals, it asks one or two questions first.
3. Work the plan with it in plan mode. The plan covers the problem, the proposed
   behavior, an implementation sketch that names the files and any new flags or
   config keys, the validation strategy, and what is out of scope. It adds open
   questions only if some decision is really unresolved.
4. Accept or reject the plan. A rejected plan goes back for another round, and nothing
   is filed from it. An accepted plan is the issue body: the skill doesn't ask a
   second time before it files.
5. Let it pick labels. It looks at the labels the repository has and prefers
   `enhancement`, then `feature`, then `feat`, so that `github-issue-to-pr` picks a
   `feat-` branch prefix. If none exist, it files with no label and says so. It
   doesn't create labels on its own.
6. Let it file the issue. The title is imperative and short, under about 72
   characters. The skill doesn't assign anyone and doesn't set a milestone unless you
   named one.
7. Take the issue URL from its report.

The skill never touches the working tree: it only reads code and writes to the issue
tracker.

## What the issue body contains

The sections are Problem, Proposed behavior, Implementation sketch, Validation, Out of
scope and, only when needed, Open questions. The footer names the skill and says the issue
is ready for `github-issue-to-pr`, which tells the next agent that the
implementation sketch is authoritative and not a suggestion.

## When it behaves differently

- If you say "just file it", the skill offers a lightweight issue with only the
  problem and proposed behavior. It names the cost: a thinner issue is harder to action
  later.
- If the repository has an issue template whose structure materially conflicts with
  the skill's body, the project's template wins and the skill adapts to it. If the template is a
  YAML form, the skill still files free-form markdown and mirrors the form's field names
  as headings.
- If the plan shows the feature already exists, the skill stops and tells you instead of
  filing it.

## Next

- If the issue is rough or you think it is under-specified,
  [groom it](/pg-skills/how-to/groom-an-issue/).
- If it is too big for one PR,
  [split it into sub-issues](/pg-skills/how-to/split-an-issue/).
- Otherwise, run `github-issue-to-pr` on the issue number, or label the issue
  `accepted` and let a [burndown](/pg-skills/how-to/burn-down-the-backlog/) take it.
