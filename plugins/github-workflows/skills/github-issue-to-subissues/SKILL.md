---
name: github-issue-to-subissues
description: "Breaks a large GitHub \"epic\" issue that contains a multi-phase implementation plan into a set of scoped sub-issues using the `gh` CLI. Reads the parent issue, identifies the phases in its implementation plan, proposes a breakdown in plan mode, and — after the user accepts — files one sub-issue per phase, nests them under the parent with GitHub's sub-issues API and orders the phases with GitHub issue dependencies (\"blocked by\"), and comments on the parent with an index of the sub-issues. Use this skill whenever the user asks Claude to \"break this issue into sub-issues\", \"split issue N into phases\", \"turn the plan in issue N into separate tickets\", \"create sub-issues for each phase of issue N\", \"decompose issue N\", or any similar phrasing that implies fanning one parent issue out into smaller children. This is a plan-then-commit workflow — do not create any sub-issues until the proposed breakdown has been explicitly accepted."
---

# GitHub Issue → Sub-Issues

Plan-first workflow: read a parent GitHub issue that contains a multi-phase implementation plan, propose a decomposition into scoped sub-issues, and — after the user accepts — file them with dependency links back to the parent and to each other. The deliverable is the list of sub-issue URLs and a comment on the parent indexing them.

This skill is the natural downstream of `github-plan-to-issue`: that skill files one well-shaped epic; this skill fans it out into actionable children that `github-issue-to-pr` can pick up one at a time.

## Prerequisites

Before starting, confirm:

1. **Inside a git repository.** `git rev-parse --show-toplevel` should succeed. If not, stop and tell the user.
2. **The `gh` CLI is installed and authenticated.** Run `gh auth status`. If `gh` is missing or unauthenticated, stop and tell the user — suggest they run `! gh auth login` themselves, since it is interactive.
3. **Current directory maps to a GitHub repo**, unless the user passed a full issue URL. Repo resolution is covered in Step 1 — if it fails, stop and ask.

Note: a dirty working tree is fine — this skill never touches the working tree.

## Step 1: Identify the parent issue

Extract two things from the user's request: the **issue number** and the **repo** (`owner/name`). Usually the user gives only the issue number and expects the repo to be inferred from the current directory.

`gh` infers the repo from the git remote automatically, so inside the repo you can usually just use the issue number. To confirm what it resolved to:

```bash
gh repo view --json nameWithOwner -q .nameWithOwner
```

If the user gave a full issue URL like `https://github.com/myorg/myrepo/issues/42`, parse owner/repo/number from the URL — the URL wins over the current remote. Pass it explicitly with `--repo myorg/myrepo` on every `gh` call.

If neither gives you owner/repo, stop and ask.

Note: for a GitHub Enterprise host, the URL host will not be `github.com`; `gh` handles this if the host is configured (`gh auth status` shows it). If it isn't, stop and tell the user.

## Step 2: Fetch the parent issue

```bash
gh issue view <number> --json number,title,body,labels,state,url,comments,milestone
```

The `comments` field includes comments inline — sometimes the plan has been revised in a comment rather than the body. `gh issue view <number> --comments` renders them more readably.

Read:
- **title** — source of sub-issue title prefixing (e.g. parent "Add caching layer" → children like "Add caching layer: wire up redis client").
- **body** — the plan itself. This is the main input.
- **labels** — inherit sensible labels onto children (e.g. `enhancement`, `infra`). Bug-tracker labels like `bug` should usually not propagate; ask if unsure.
- **state** — if the issue is `CLOSED`, stop and ask whether to proceed anyway.
- **existing sub-issues** — before proposing anything, check for children already attached to the parent:

  ```bash
  gh api repos/{owner}/{repo}/issues/<number>/sub_issues --jq '.[] | {number, title}'
  gh api repos/{owner}/{repo}/issues/<number>/dependencies/blocking --jq '.[] | {number, title}'
  ```

  `gh api` substitutes `{owner}` and `{repo}` from the current directory's remote — write them literally, or hardcode `repos/myorg/myrepo/...` when working against a different repo. If children already exist, this skill has probably already been run. Surface that and ask whether to add more or stop.

## Step 3: Identify the phases in the plan

Scan the body (and any plan-revising comment) for structure. In priority order:

1. **Explicit phases** — headings like `## Phase 1`, `### Phase 1: Scaffolding`, numbered "Phase N" sections. This is the happy path — each phase becomes one sub-issue.
2. **Numbered implementation steps** — a numbered list under an "Implementation sketch" / "Implementation plan" section where each item is substantial enough to stand alone. Group trivially small adjacent steps; split overlong ones.
3. **Bulleted implementation sketch** — bullets under "Implementation sketch". Each bullet may or may not warrant its own issue; use judgment based on the size of the change implied.
4. **Unstructured prose plan** — no clear phasing. You will need to *propose* a decomposition; call this out in the plan mode summary so the user knows you are inferring, not transcribing.

If the plan is genuinely too small to split (one phase, a handful of files), stop and tell the user — filing a single sub-issue just duplicates the parent.

A good phase for a sub-issue is one that:
- has a clear, testable acceptance criterion
- can plausibly be one PR
- makes sense in isolation (a reviewer doesn't need to read three other open issues to understand it)

Target 2–6 sub-issues. Fewer than 2 means the split wasn't worth it; more than 6 usually means the phases are too granular and should be merged.

## Step 4: Enter plan mode

Call `EnterPlanMode` to move into plan mode explicitly. Plan mode is the right venue because:

- it signals that you are *proposing a breakdown*, not editing
- it produces a structured artifact the user can accept, reject, or edit
- the accepted plan becomes the exact set of sub-issues you file

Do not create any issues while in plan mode.

## Step 5: Shape the breakdown

Inside plan mode, present:

1. **Parent recap** — one or two sentences summarizing the parent issue, so the user can verify you read it correctly.
2. **Proposed sub-issues** — an ordered list. For each, include:
    - **Title** (the exact title you will file)
    - **One-paragraph scope** — what's in, what's not
    - **Dependency on prior phases** — yes / no (most phases depend on the one before; parallelizable phases should say so explicitly)
    - **Labels** you intend to apply
3. **Ordering / dependency graph** — if anything deviates from strict linear ordering (e.g., Phases 3 and 4 can run in parallel), show it.
4. **Anything you chose NOT to split out** — e.g., "I left validation/testing inside each phase's sub-issue rather than making it its own Phase". Prevents surprise.
5. **Open questions** (optional) — genuine ambiguities only. No padding.

Length target: short. The user should be able to eyeball the breakdown and say yes/no in under a minute.

## Step 6: Present the plan and get acceptance

Exit plan mode with `ExitPlanMode`. The user will accept, reject, or edit.

- **Rejected / revise**: iterate. Go back to Step 4 or 5. Do not file any sub-issues from a rejected breakdown.
- **Edited** (e.g., "merge phases 2 and 3, drop phase 5"): apply the edits and re-present — a small second round of acceptance is fine when the user explicitly changed the shape.
- **Accepted**: proceed to Step 7. Acceptance of the plan is acceptance of the filings — do not ask a second time before creating each issue.

## Step 7: Compose each sub-issue body

**Title convention**: `<parent-title>: <phase summary>` — keeps sub-issues recognizable when scanning the issue list. Keep under ~80 chars; shorten the parent title if needed (don't shorten the phase summary, which carries the differentiating content).

**Body template**:

```markdown
## Parent

Part of #<parent-number> — <parent title>.

<If the parent's plan lives in a checked-in document, name it and the phase:
"Implements **Phase N** of `docs/.../some-plan.md`." That line is the
provenance trail — it is how somebody reconciling a changed plan finds the
issues derived from it, and how the implementer knows which document is
authoritative.>

## Scope

<one paragraph: what this phase delivers, in user- or reviewer-facing terms>

## Implementation notes

- <specific files / modules / components to touch>
- <new types, flags, config keys introduced by this phase>
- <point at the section of the plan or parent that specifies this phase — cite it, do not copy it>

## Dependencies

- Blocked by: #<prior-phase-number> — do not start until that lands (omit section entirely if this is Phase 1)
- Blocks: #<next-phase-number> (informational; the dependency edge is set from the next phase's side)

## Validation

- <specific test(s) or check(s) that demonstrate this phase is done>
- Standard project gates: `just fmt`, `cargo clippy --all-targets -- -D warnings`, `just test`

## Out of scope

- <anything a reviewer might expect in this phase but that is deferred to a later phase — cite the phase number>

---
_Filed via the `github-issue-to-subissues` skill. Parent: #<parent-number>._
```

**Reference the plan; do not restate it.** A sub-issue should carry scope,
constraints, and acceptance in prose — not the plan's code, signatures, or SQL.
This is not a style preference. Implementations diverge from plans, and when
they do, the plan gets corrected (see Step 6a of `github-issue-to-pr`). Every sub-issue that
copied a detail out of the plan is now a second place holding a stale version of
it, with nothing linking the two. Twelve thin issues take one plan edit to
reconcile; twelve fat ones take thirteen, and the ones nobody remembers to check
stay wrong until they cost somebody an afternoon.

If a phase genuinely needs a concrete API or schema pinned in the issue itself,
that is a signal the plan is the wrong place for it — or that the phase is
under-specified. Fix that, rather than duplicating.

Omit sections that don't apply rather than leaving them empty. The `Part of #N` line and footer are load-bearing: `github-issue-to-pr` will read the parent link to understand context when someone picks this sub-issue up.

Write each body to a file in the scratchpad and pass it with `--body-file` rather than wrestling with shell quoting on a multi-line `--body`.

## Step 8: Create the sub-issues

Create them **in phase order**, because Step 9 needs the earlier issues' numbers and ids to set dependency edges on later ones. There is no bulk-create — loop, one `gh issue create` call per sub-issue.

For each phase, in order:

1. Create the issue:

   ```bash
   gh issue create --title "<title>" --body-file <path-to-body.md> \
     --label <label> --label <other-label>
   ```

   `--label` is repeatable. Add `--milestone "<name>"` here if the parent has one (see below).
2. `gh issue create` prints the new issue's URL on stdout — **capture that**. Do not construct URLs by hand; the printed URL is authoritative. The trailing path segment is the issue number.
3. Record the issue number and URL for the index comment and the dependency wiring.

Do **not** assign the sub-issues to a user automatically. Do **not** set a milestone unless the parent has one — if it does, inherit it onto the children with `--milestone "<name>"` at create time, or `gh issue edit <number> --milestone "<name>"` afterwards.

If a `gh issue create` call fails partway through the list, stop and report:
- which sub-issues were filed (with numbers)
- which one failed and the error
- the remaining phases that were not attempted

Do not retry blindly — a failure here usually means something is off with auth or the repo state, and filing duplicates on retry would be worse.

## Step 9: Wire up the parent/child and ordering relationships

GitHub has two distinct primitives here, and they do different jobs. Use both.

Neither is exposed as a first-class `gh` subcommand — both go through `gh api`. Both take an issue's **internal database id**, not its number.

### Getting an issue's database id

```bash
gh api repos/{owner}/{repo}/issues/<number> --jq .id
```

**Do not use `gh issue view <number> --json id` for this.** That returns the GraphQL node id (`I_kwDODKw3uc6h5Q2z`), not the REST database id (`2716143027`), and these endpoints will reject it. Only the `gh api ... --jq .id` form above gives you the right value.

Use `-F` (not `-f`) when passing the id, so it is sent as a JSON integer rather than a string.

### 9a: Nest each sub-issue under the parent

GitHub's native sub-issues give real parent/child nesting — the children show up in a "Sub-issues" panel on the parent with a progress bar, and closing them ticks it along.

For each sub-issue, POST its database id to the **parent's** `sub_issues` endpoint:

```bash
CHILD_ID=$(gh api repos/{owner}/{repo}/issues/<child-number> --jq .id)
gh api --method POST repos/{owner}/{repo}/issues/<parent-number>/sub_issues \
  -F sub_issue_id="$CHILD_ID"
```

This replaces the "mark the parent as depending on every sub-issue" step you'd use on a tracker with only dependency edges — nesting is the better-fitting primitive, and it drives the parent's progress bar natively.

Caveats:
- The sub-issue must belong to the same repository owner as the parent.
- Sub-issues are a relatively recent GitHub feature. They are available on github.com, but **may not be enabled on a given GitHub Enterprise Server version**. If the POST returns 404 or 410, that's the likely cause — fall back per the note at the end of this step.
- Sub-issues give nesting, **not** ordering. They say nothing about which child comes first. That's 9b's job.

### 9b: Order the phases with issue dependencies

GitHub issue dependencies ("blocked by" / "blocking") express sequencing between siblings. This is the direct analogue of the phase ordering in the plan.

For each consecutive pair of phases `(N, N+1)` in the ordered list, mark phase N+1 as **blocked by** phase N:

```bash
BLOCKER_ID=$(gh api repos/{owner}/{repo}/issues/<phase-N-number> --jq .id)
gh api --method POST repos/{owner}/{repo}/issues/<phase-N+1-number>/dependencies/blocked_by \
  -F issue_id="$BLOCKER_ID"
```

The issue **number** in the path is the one that is blocked; the `issue_id` in the body is the one doing the blocking. The two directions are easy to flip — verify by reading back with:

```bash
gh api repos/{owner}/{repo}/issues/<number>/dependencies/blocked_by --jq '.[] | {number, title}'
```

If the breakdown included parallel phases (e.g., Phases 3 and 4 both depend on Phase 2, and Phase 5 depends on both), apply those exact edges rather than forcing a linear chain — an issue can be blocked by several others.

Caveats:
- Like sub-issues, this is a recent feature (generally available on github.com since August 2025) and **its availability on GitHub Enterprise Server is version-dependent** — verify with a read-only `gh api .../dependencies/blocked_by` call before assuming the POST will work. A 200 with `[]` means the endpoint exists; a 404 means it doesn't.
- Dependencies are **advisory**. GitHub surfaces the relationship in the UI and in search (`is:blocked`, `blocked-by:`), but it does **not** prevent anyone from working on or merging a blocked issue. Nothing is enforced.
- There is a cap of 50 issues per relationship type, which no sane breakdown will hit.

### If either API is unavailable

**Do not block the whole run.** Fall back to making each sub-issue body's "Blocked by" line load-bearing — plus the ordered checklist in the Step 10 parent comment — and call out in the Step 11 summary that the in-tracker edges were not set. The textual ordering is convention-only in that case: it is a note to a human, and GitHub will not enforce it.

## Step 10: Index the sub-issues on the parent

Add a comment to the parent issue listing the filed sub-issues, in phase order.

```bash
gh issue comment <parent-number> --body-file <path-to-comment.md>
```

Comment template:

```markdown
Decomposed into the following sub-issues (in order):

- [ ] #<n1> — <phase 1 short title>
- [ ] #<n2> — <phase 2 short title>
- [ ] #<n3> — <phase 3 short title>

The order above is the intended order of work; each phase is also wired as
`blocked by` its predecessor. Note that GitHub does not enforce this — it is a
signal to whoever picks the work up, not a gate.

Filed via the `github-issue-to-subissues` skill. Each sub-issue can be actioned independently by `github-issue-to-pr`.

<If a checked-in plan backs these issues, add: "`<plan-path>` is the source of truth for the detail — these issues carry scope and acceptance only. A change that diverges from the plan is corrected in the plan, not just in the changelog.">
```

The checklist is deliberately a task list: it renders as checkboxes and gives the parent a visible, ordered ledger even where the dependency edges didn't take.

Do **not** rewrite the parent issue body to insert this list. Editing the body (`gh issue edit <parent-number> --body-file ...`) risks clobbering user edits or the original plan; a comment is the safe, append-only choice.

## Step 11: Report back

End with a short summary:

- parent issue number and URL
- each sub-issue number, title, and URL (in phase order)
- whether the sub-issue nesting and dependency edges were wired up (yes / no / partial — per Step 9), and if not, that the ordering is convention-only in the issue bodies and parent comment
- a one-line pointer: the user can run `github-issue-to-pr` against the first sub-issue number when ready to start implementation

Keep it tight. The sub-issue URLs are the point.

## Edge cases worth remembering

- **Parent is itself a sub-issue** (has a `Part of #M` line, or `gh api repos/{owner}/{repo}/issues/<number>/parent` returns one): re-parent onto the grandparent, or stop and ask. Nesting sub-issues under sub-issues is almost never what the user wants — and GitHub's own sub-issue nesting has a depth limit, so a deep chain may simply be rejected.
- **Plan is in a comment, not the body**: use the latest plan-shaped comment. If the body and a comment disagree, surface the conflict and ask which is authoritative — don't guess.
- **Repo has an issue template**: if `.github/ISSUE_TEMPLATE/` exists and its structure materially conflicts with the sub-issue body template above, adapt — the project's template wins. `gh issue create --template <name>` can start from it. Beware issue *forms* (`.yml` templates with required fields): a plain `--body-file` bypasses them, which is usually fine but will look off next to hand-filed issues.
- **Parent has a milestone**: inherit it onto children (`--milestone` at create, or `gh issue edit` after), so the milestone progress bar reflects the true unit of work.
- **Fork remote**: if `git remote -v` shows an `upstream`, the parent issue probably lives on upstream. Pass `--repo <upstream-owner>/<repo>` on every `gh issue` call and use `repos/<upstream-owner>/<repo>/...` in `gh api` paths rather than the `{owner}`/`{repo}` placeholders, which resolve to the fork. The user's fork is irrelevant here since nothing is being pushed. Confirm the topology with `gh repo view --json parent`.
- **Partial prior run**: if Step 2 finds some but not all phases already filed as sub-issues, treat the breakdown as *resumable* — propose only the missing phases and wire dependencies around what's already there. Do not re-file duplicates.
- **User wants fewer sub-issues than the plan has phases**: honor it. Merge phases in the breakdown so each sub-issue still has a coherent scope. Don't lose content — anything merged in should appear in the sub-issue body.
- **User wants more sub-issues than phases**: split a phase only when there is a clean seam (two files, two features, two tests). Splitting on an artificial seam produces sub-issues that can't be reviewed independently.
- **Sub-issue or dependency API unavailable** (GitHub Enterprise Server, or a token without `repo` write scope): fall back gracefully (see Step 9) rather than aborting. The textual "Blocked by" line in each sub-issue body and the ordered checklist on the parent are the backup.
- **Read-only token**: `gh auth status` shows token scopes. Filing issues needs `repo` (or a fine-grained token with issue write). If the scopes look read-only, stop before Step 8 rather than failing halfway through the loop.
