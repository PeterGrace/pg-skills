---
name: github-epic-close-out
description: "Use when every sub-issue of a GitHub epic or milestone appears done and the epic should be audited against its plan and design before it is closed, or when the user asks to \"audit and close epic N\", \"close out the milestone\", \"verify the milestone is complete\", or \"check the epic delivered everything\". Also the final step of github-epic-to-merged-prs."
---

# GitHub Epic Close-out (audit, then close)

Close an epic only when the evidence shows that it delivered what its plan and
design promised. "All sub-issues are closed" doesn't count as evidence: an
issue can close without a merged PR, a PR can merge without one of its tasks,
and a task can deliver less than the design required.

This is the third skill of the workflow in the catalog concept
`/processes/subagent-pr-workflow.md`, after `github-milestone-plan-to-issues`
and `github-epic-to-merged-prs`. It can also run on its own.

**This audit is read-only until step 6.** Change no code here. Each gap you
find is reported, not fixed.

## Two modes

Milestone PRs merge into an integration branch (`milestone/<epic>-<slug>`),
and the branch merges into `main` once. So the audit runs twice:

- **Pre-merge** (`--branch <M>`, or the epic names a milestone branch that
  hasn't merged yet): audit against `origin/<M>`. Wherever this skill says
  `main` below, read `<M>`. It decides whether the milestone is ready for
  `main`. It never closes the epic.
- **Final** (no milestone branch, or after it merged): audit against
  `origin/main`. Check also that the milestone PR is `MERGED` by a merge
  commit and that `<M>`'s head is an ancestor of `origin/main`. Every row
  that passed pre-merge only needs this ancestry check plus the gates on
  `main` (CI green, test count); don't redo the per-PR rows.

## 1. Collect the record

- **The epic:** `gh issue view <epic> --json body,comments,labels`. Note its
  In-scope list, its Decisions and the plan path it names.
- **The sub-issues:** `gh api repos/{owner}/{repo}/issues/<epic>/sub_issues`.
- **For each sub-issue, the PR that closed it.** Use GraphQL
  `closedByPullRequestsReferences`, or the issue's timeline. PRs into a
  milestone branch don't auto-close their issue, so that field is often
  empty: find the PR by its `Closes #N` body or the coordinator's close
  comment (`gh pr list --base <M> --state merged --search "<N>"`). Record the PR's
  number, its state (it must be `MERGED`), its merge commit, and whether the
  merge commit is on `origin/main`:
  `git merge-base --is-ancestor <sha> origin/main`.
- **The plan and the design section,** read from `origin/main`.
- **The milestone changelog and the per-task changelog entries.**
- **The carried-over issues** the epic named.

## 2. Check each checkpoint

Build one table. Every row is a checkpoint, with a status and the evidence.

| Checkpoint | What passes |
|---|---|
| **Sub-issue closed by a merged PR** | `MERGED`, merge commit on `main`. Closed as "not planned", or no PR at all, is a gap unless the epic records why. |
| **Review gate** | Every PR has a review from the project's reviewer, and every review comment has a reply or a fixing commit. |
| **Plan task delivered** | The task's Files exist on `main`. Its named tests exist (search for them by name) and pass. A task whose PR didn't touch its files is a gap. |
| **Design checkpoint** | Every in-scope item in the design section and the epic maps to code on `main`. Name the file and the symbol. Use the design's acceptance criteria or test-plan section, for example "at most one repeated call per crash", and find the test that asserts each one. |
| **Divergences reconciled** | Every `Corrected (issue #N)` note in the plan appears in the milestone changelog. Where a note changed the design, the design doc was updated to match. |
| **Carried-over issues closed** | Each carried-over issue is closed by a merged PR in this milestone. |
| **Gates on main** | CI is green on `origin/main`'s head: `gh run list --branch main --limit 1`. Run the project's test command locally on a fresh worktree of `origin/main`, and record the count of tests and binaries against the previous milestone's. |
| **Smoke test recorded** | The milestone changelog has the smoke test's commands and outputs. A skipped part (for example a real provider without a key) must be marked as skipped, never presented as passed. |
| **Follow-ups listed** | The changelog lists the follow-ups. Note which are already filed and which are only written down. |

Use real evidence: a command's output, a `file:line`, a PR number. A
checkpoint you couldn't verify is **unverified**, not passed.

## 3. Decide

- **Every checkpoint passes,** or each exception is recorded and justified in
  the plan or the epic: the epic validates.
- **Otherwise it does not validate.** List each gap with its evidence, and
  what would close it: a new sub-issue, a plan correction, or a missing test.

## 4. Follow-ups

List the follow-ups from the changelog, with a proposed issue title for each.
**File them only if the user says so**: filing work into the tracker is the
user's decision. If the user already said in this session to file follow-ups,
do it and include the numbers in the close-out comment.

## 5. Write the close-out comment

Write it to a scratch file. Model it on this shape:

```
## Milestone <N> audit: <all delivered | gaps found>

All <k> sub-issues are closed, each by its own PR:

| Task | Issue | PR | Delivers |
|---|---|---|---|

Each in-scope item is present on `main`:

| In scope | Where |
|---|---|

`<test command>` passes <n> tests across <b> binaries, against <m> at the end of milestone <N-1>.
<CI on main: green at <sha>.>

The smoke test <what it showed; what was skipped and why>.

The decisions taken while planning <held | changed: ...>. Divergences are recorded in `<changelog>`.

Follow-ups: <filed as #.. | listed in the changelog, not filed>.

<Closing as complete. | Already closed by <PR or event>; this audit found it complete. | Already closed by <PR or event>, but this audit found gaps: <failed checkpoints>. The epic is not complete; whether to reopen it is for the owner to decide. | Leaving open: <gaps>.>
```

## 6. Act

- **Pre-merge mode:** post the comment, headed `Milestone <N> pre-merge
  audit`, and report "ready for main" or the gaps. Never close the epic in
  this mode; the coordinator opens the milestone PR.
- **Final mode, the epic is already closed:** check first, with
  `gh issue view <epic> --json state,closedAt,closedByPullRequestsReferences`.
  If it is `CLOSED`, don't run `gh issue close` and don't write "Closing as
  complete". Post the comment with the "Already closed by ..." line instead,
  naming what closed it: the PR in `closedByPullRequestsReferences`, or, when
  that is empty, the `closed` event in the issue timeline
  (`gh api repos/<owner>/<repo>/issues/<epic>/timeline`). A PR body that said
  "closes #N" (even "doesn't close #N") closes the epic when it merges, before
  the final audit. Say so in the comment if that is what happened.
  Which line to use depends on the audit verdict from steps 2-3, not on the
  epic's state. If it validates, use "this audit found it complete". If it
  doesn't, use the already-closed-with-gaps line: list the failed checkpoints,
  don't say the epic is complete, and don't reopen the issue yourself. Post
  the comment, then ask once whether to reopen it. An epic closed early by a
  PR is exactly where gaps can still exist, and "never close an epic with an
  unexplained gap" applies to one that someone else closed too.
- **It validates, and closing is authorized:** post the comment, then run
  `gh issue close <epic> --reason completed`. Closing is authorized if the
  user asked for close-out, or if this skill was invoked as the last step of
  `github-epic-to-merged-prs` under a standing merge authorization.
- **It validates, but closing wasn't authorized:** show the comment, and ask
  once whether to post it and close.
- **It doesn't validate:** post the comment with the gaps, and leave the epic
  open. Never close an epic with an unexplained gap.

Then record the outcome in the project's catalog concept: one dated line
saying the milestone closed, plus a `log.md` entry. Put any follow-up that's
left unfiled in `/projects/things-to-fix.md` if pgrace decided not to fix it
now.

## Common mistakes

| Mistake | Fix |
|---|---|
| Closing because every sub-issue is closed | Check each one is closed by a merged PR whose merge commit is on `main` (or on `<M>` pre-merge). |
| Closing the epic after the pre-merge audit | The epic closes only once the milestone branch is on `main`. |
| Counting tests from a PR description | Run the tests on `origin/main` yourself. |
| Calling a skipped smoke-test step passed | Label it skipped, with the reason. |
| Filing follow-ups without being asked | List them, and file them only when the user says to. |
| Fixing a gap during the audit | Report the gap. A fix is new work, with its own issue and PR. |
| Ignoring the design doc | Plans drift. Audit against the design's in-scope list and acceptance criteria too. |
