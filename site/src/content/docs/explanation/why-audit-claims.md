---
title: "Why audit claims: what gates miss"
description: Why I have a fresh subagent on a different model audit every change's claims before the pull request opens, what that finds that passing gates don't, and when I keep a committed ledger.
sidebar:
  order: 4
---

My gates are `just fmt`, a linter and the tests. When they pass, I know the code
builds and its tests pass. I don't know that it does what the issue asked, or that the
PR description is true. This page is about the check I run for those two questions, and
why I run it the way I do.

## What gates miss

I rely on the claims audit for three things that a green gate run doesn't tell me.

**The change didn't do what was asked.** The code passes, but part of the issue or the
plan was quietly dropped. Nothing in a build or a test run notices a requirement that
nobody wrote a test for.

**The PR body overclaims.** The description says things the diff doesn't support, such
as a file list that is wrong. Brooke has caught that kind of thing in reviews too.

**Self-grading bias.** The implementer can't fairly grade its own work. So the audit is done by a fresh subagent, on a different model from the one that wrote the
change.

The skill adds a fourth thing: when the project has a ledger, the audit also checks that
the change didn't break anything the ledger records as working. That isn't my main
reason for running it, but it's part of what Step 7a asks for.

## How it works, in short

[`github-issue-to-pr`](/pg-skills/reference/skills/github-issue-to-pr/) runs the audit
in its Step 7a, after the gates and the commit and before the push. It needs the
[claims-audit](/pg-skills/reference/dependencies/#claims-audit) skill. The
[how-to guide](/pg-skills/how-to/validate-a-change/) has the steps.

The implementer drafts the PR body first, because the body's statements of fact are
claims the audit checks. Then it dispatches the auditor. The auditor gets the issue,
the draft body, the repository and the commit range. It doesn't get the implementer's
plan, reasoning or summary. The `claims-audit` skill's core rule is: "a verdict is only
as good as the evidence you gathered *yourself*", and an account from the author who
wants the PR to open is the wrong evidence.

For each claim the auditor records a verdict:

- **supported**, **refuted** or **not_enough_info**.

A claim that is refuted and ours is one from the issue or the PR body, and the
implementer has to fix it before the PR opens. Then the auditor looks again. A claim
that is refuted in code the PR didn't touch is listed as pre-existing, and it doesn't
block. `not_enough_info` never blocks, and the PR body says what would decide it.

## What burned me

I tell this once, here, and the other pages that need it link to this one.

My words: "I had a software project that confidently claimed a feature was implemented
and it was not implemented, and was only found when I used claims-mcp/claims-audit to
find it."

This is the origin story for two of my checking loops: auditing claims, which this
page is about, and fact-checking generated docs.

## Ledger mode or table-only mode

The audit runs in one of two modes. The mode depends on whether the project has a
`claims.json` tracked in git.

- **Ledger mode.** `claims.json` is committed. The auditor records claims, evidence and
  verdicts in it through [claims-mcp](/pg-skills/reference/dependencies/#claims-mcp),
  and the implementer commits it on the branch. The ledger's anchors pin the branch's
  commits, so the PR should be merged with a merge commit, not squashed or rebased.
- **Table-only mode.** There is no ledger. The auditor makes no claims-mcp calls at all.
  The results go into the PR body as a table, without claim ids. The PR body says that
  the findings were not recorded.

For pull requests, claims-mcp is optional, and you need it only for ledger mode.

I keep a committed ledger for projects that are "generally long-lived, spec-driven, or
correctness-matters." Everything else stays in table-only mode.

My advice, in my words: "Sometimes I delay the committed ledger until a later date,
which spawns a raft of issues. It's better to start the ledger very early if you think
you're going to need it." Adding a ledger later means writing claims for everything
that's already built, and checking each one turns up a batch of issues at once. If you
think the project may need one, start it at the beginning.

For a real committed ledger, look at
[`claims.json` in claims-mcp's own repository](https://github.com/hypotheosis/claims-mcp/blob/main/claims.json).
It keeps retired claims and the verdict history as well as the current
verdicts. Each release also attaches an audit report as PDFs, `audit.pdf` and `audit-full.pdf`, to its
[GitHub release](https://github.com/hypotheosis/claims-mcp/releases/tag/v0.2.5).
claims-mcp's own docs have a
[browser viewer](https://hypotheosis.github.io/claims-mcp/viewer/) for any public
repository's ledger.

## What I do with the results

I leave it to Brooke, my review bot. The audit's table goes in the PR body, and Brooke
checks the body's claims against the diff. I rarely read the table myself. So before I
look at a description it has had two independent checks: the auditor's, and hers. See
[Why a review bot](/pg-skills/explanation/review-bot/#what-i-rely-on-her-for) for what
she checks. If you don't have a bot, a human reviewer reading the table against the diff
does the same job.

## What it looks like

Both of these are PRs in this repository, in table-only mode.

- [PR #34](https://github.com/PeterGrace/pg-skills/pull/34) ended at 28 supported
  claims, none refuted and one not_enough_info, which was then confirmed. The refuted
  ones along the way included a link to a dependencies anchor that didn't exist and a
  count of new tests that was off: the description said 23 and the diff added 26.
- [PR #36](https://github.com/PeterGrace/pg-skills/pull/36) is the one I'd show someone
  to explain what the audit catches. The audit refuted 7 claims on its first pass, all
  statements on the new pages about what a skill does. One said that `next-issue.sh --list`
  skips only the open-PR check, when it also skips the branch check. Another said that
  removing the `burndown-blocked` label always resumes an issue, when a left-over branch
  or open PR still makes the script skip it. All 7 were fixed before the PR opened. The
  audit also had 6 not_enough_info findings, and about 110 supported claims.

Gates passed on both PRs. They check the code, and these
were statements about it.

## Where else I use it

Outside pull requests, I use `claims-audit` on two things:

- **Generated docs.** Study guides, and the pages of this site.
- **Agent outputs.** Checking that a long agent task did everything its brief asked.

The [how-to for auditing outside a PR](/pg-skills/how-to/audit-an-artifact/) has the
steps. I don't use it for milestone audits.
[`github-epic-close-out`](/pg-skills/reference/skills/github-epic-close-out/) covers
those.

## What it doesn't do

The audit is a model reading evidence, so it can be wrong. claims-mcp doesn't run your
tests or code (it records evidence and runs read-only git queries to pin anchors), so the
auditor has to run the checks. The
skill calls `not_enough_info` an honest outcome, to use instead of guessing. The audit
is also one check among several: gates, the audit, the reviewer and, for an epic, the
[close-out audit](/pg-skills/how-to/close-out-an-epic/).
