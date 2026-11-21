---
title: Groom a vague issue
description: Turn a thin or under-specified GitHub issue into a ready-to-implement work item with github-groom-issue, and decide when grooming is worth the effort.
sidebar:
  order: 3
---

This guide upgrades a rough issue into a work item that an agent can implement without
asking you anything, using the
[github-groom-issue](/pg-skills/reference/skills/github-groom-issue/) skill. The
skill investigates the issue against the real code, archives the original text as a
comment, and overwrites the issue body with a structured one.

It differs from [planning a feature](/pg-skills/how-to/plan-a-feature/) in where it
starts: that skill files a new issue from a plan, and this one improves an issue that
already exists.

You need the `github-workflows` plugin
([install commands](/pg-skills/reference/plugins/github-workflows/)),
[gh](/pg-skills/reference/dependencies/#gh), and a local checkout of the repository.
The skill reads code to investigate, so the checkout has to be there.

## When it is worth doing

I groom an issue only when it is too vague for an agent to implement unattended.
Whoever filed the issue, I read it first and groom if needed. Then I decide whether it
is ready to be worked.

Grooming costs an investigation pass and an overwrite of the issue body. The skill
keeps the original, so the overwrite can be undone, but you still have to read the
result.

## Steps

1. Ask for it by name: "Groom issue 42." Give a full issue URL if the issue is in
   another repository.
2. Let it read the issue and every comment. A diagnosis or partial spec in a comment is
   folded into the new body, with credit given to its author.
3. Expect it to stop and ask in a few cases: the issue is closed; the issue was already
   groomed (the body ends with the skill's footer, or an archive comment exists); the
   investigation shows the issue is a duplicate, already fixed or rests on a false
   premise; the ask is ambiguous on fundamentals. A body and a comment that disagree
   also stop it.
4. Let it investigate. It names the real files and functions the change touches,
   confirms what the code does today, and notes the project's real validation
   commands. For a performance report it can usually confirm the mechanism from the
   code and leaves the magnitude qualitative.
5. It classifies the issue as a bug, a feature or a chore, labels first and body
   content second. Performance reports count as bugs.
6. It posts the archive comment before it changes anything. The comment holds the
   original title and body, or says there was no description. This is the undo path.
7. It composes the body from the template for that type, with concrete paths and
   commands. Each template ends with a footer saying the body is authoritative for
   `github-issue-to-pr`.
8. It judges whether the item is one PR. If it isn't, it shapes the body with explicit
   phases, so the split has clean seams.
9. It overwrites the body with `gh issue edit`, on this path too. It may sharpen a vague
   title, and adds a type label if the repository already has one. It doesn't assign
   anyone or set a milestone unless you asked. If the item was too big, it then hands
   off to [`github-issue-to-subissues`](/pg-skills/how-to/split-an-issue/), which shows
   you the breakdown in plan mode before it files anything.
10. Read the result. The report links the archive comment. If the groomed body is wrong,
    the original is there to restore.

## After grooming

The skill's normal path has no acceptance gate. It rewrites the body directly and
leaves the review to you, so your read of the result is the gate. When you are
satisfied, run
[github-issue-to-pr](/pg-skills/reference/skills/github-issue-to-pr/) on it. Or, for a
repository that runs a [burndown](/pg-skills/how-to/burn-down-the-backlog/), apply the
`accepted` label yourself: the label is your decision, and grooming doesn't add it.

## If you can't edit the issue

`gh issue edit` fails with a 403 when you have only read or triage access. The archive
comment may already be posted by then. The skill tells you the original is preserved
and hands you the groomed body to paste.
