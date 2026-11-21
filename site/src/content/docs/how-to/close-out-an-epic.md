---
title: Close out an epic
description: Audit an epic against its plan and design before and after the milestone merge with github-epic-close-out, and avoid closing keywords in the milestone PR.
sidebar:
  order: 4
---

This guide audits a finished epic and closes it, using
[github-epic-close-out](/pg-skills/reference/skills/github-epic-close-out/). "All
sub-issues are closed" isn't evidence: an issue can close without a merged PR, a PR can
merge without one of its tasks, and a task can deliver less than the design required.
The audit changes no code. It reports gaps and doesn't fix them. It posts its comment on
the epic and, in the final mode, closes the epic. If you keep a [knowledge catalog](/pg-skills/reference/dependencies/#telekin), it
also records the outcome there: a dated line in the project's concept and a `log.md`
entry, plus any follow-up left unfiled in `/projects/things-to-fix.md` if you decided
not to fix it now. The catalog is optional.

## The two modes

Run it twice for a milestone branch.

- **Pre-merge:** `github-epic-close-out <epic> --branch <milestone branch>`. It audits
  against `origin/<milestone branch>` and decides whether the milestone is ready for
  `main`. It never closes the epic.
- **Final:** `github-epic-close-out <epic>`, after the milestone PR has merged. It audits
  against `origin/main`. It also checks that the milestone PR was merged by a merge
  commit and that the milestone branch's head is an ancestor of `main`, and it re-checks
  the gates on `main` (CI green, test count). It doesn't redo the per-PR rows.

If the epic has no milestone branch, run only the final mode.

## Steps

1. Run the pre-merge mode: "Close out epic 3 on branch `milestone/3-workflow-site`."
2. Let it collect the record: the epic, its sub-issues, the PR that closed each, the
   plan and design from `origin/main`, the changelog, and the carried-over issues. PRs
   into a milestone branch don't auto-close their issue, so it finds the PR from its
   body or the coordinator's close comment.
3. Read the checkpoint table. A row passes only on evidence: a command's output, a
   `file:line` or a PR number. A row it couldn't verify is unverified, not passed. The
   rows are:
   - sub-issue closed by a merged PR;
   - review gate;
   - plan task delivered;
   - design checkpoint;
   - divergences reconciled;
   - carried-over issues closed;
   - gates on main;
   - smoke test recorded;
   - follow-ups listed.
4. Decide. If every row passes, or each exception is justified in the plan or the epic,
   the milestone validates. Otherwise it doesn't, and the comment lists each gap and
   what would close it: a new sub-issue, a plan correction or a missing test.
5. It posts a comment headed `Milestone <N> pre-merge audit` on the epic and reports
   "ready for main" or the gaps. See the real one on
   [epic #3](https://github.com/PeterGrace/pg-skills/issues/3#issuecomment-7063515563).
6. Fix any gaps with new issues and PRs, then open the milestone PR (see the next
   section) and merge it with a merge commit.
7. Run the final mode. If it validates and closing is authorized, it posts the comment
   and runs `gh issue close <epic> --reason completed`. See the
   [final audit on epic #3](https://github.com/PeterGrace/pg-skills/issues/3#issuecomment-7063711827).
   If it doesn't validate, it posts the gaps and leaves the epic open.

Follow-ups it finds are listed with proposed titles. It files them only if you say so, or said so earlier in the session.

## The closing-keyword trap

Never write "close #N", "closes #N" or "fixes #N" for the epic or its sub-issues in the
milestone PR body. A closing keyword fires when the PR merges into the default branch.
It would close the epic at the merge, before the final audit has run, and the final
audit is what closes it.

List the sub-issues and their PRs in a table instead, link the pre-merge audit
comment, and say the PR doesn't close the epic. [PR #25](https://github.com/PeterGrace/pg-skills/pull/25)
has no closing keyword. Its body says only that the epic stays open until the post-merge audit completes.

The sub-issue PRs go the other way. Their `Closes #N` does nothing on a non-default
base, so the coordinator closes each sub-issue after the merge.

## What the audit has found

Gaps after every PR passed review: divergences nobody documented, and acceptance
criteria with no test. On epic #3 the audit found no gaps, and listed two follow-ups it
didn't file. On the milestone PR itself, review caught a real bug that the pre-merge audit hadn't: see
[Why a review bot](/pg-skills/explanation/review-bot/).
