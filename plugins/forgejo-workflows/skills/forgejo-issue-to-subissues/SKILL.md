---
name: forgejo-issue-to-subissues
description: "Breaks a large Forgejo \"epic\" issue that contains a multi-phase implementation plan into a set of scoped sub-issues using the `forgejo` MCP server (raohwork/forgejo-mcp). Reads the parent issue, identifies the phases in its implementation plan, proposes a breakdown in plan mode, and — after the user accepts — files one sub-issue per phase, wires up forgejo issue dependencies so phases are ordered, and comments on the parent with an index of the sub-issues. Use this skill whenever the user asks Claude to \"break this issue into sub-issues\", \"split issue N into phases\", \"turn the plan in issue N into separate tickets\", \"create sub-issues for each phase of issue N\", \"decompose issue N\", or any similar phrasing that implies fanning one parent issue out into smaller children. This is a plan-then-commit workflow — do not create any sub-issues until the proposed breakdown has been explicitly accepted."
---

# Forgejo Issue → Sub-Issues

Plan-first workflow: read a parent Forgejo issue that contains a multi-phase implementation plan, propose a decomposition into scoped sub-issues, and — after the user accepts — file them with dependency links back to the parent and to each other. The deliverable is the list of sub-issue URLs and a comment on the parent indexing them.

This skill is the natural downstream of `forgejo-plan-to-issue`: that skill files one well-shaped epic; this skill fans it out into actionable children that `forgejo-issue-to-pr` can pick up one at a time.

## Prerequisites

Before starting, confirm:

1. **Inside a git repository.** `git rev-parse --show-toplevel` should succeed. If not, stop and tell the user.
2. **The `forgejo` MCP is connected.** Its tools show up with a `forgejo` prefix (likely `get_issue`, `create_issue`, `create_issue_comment`, `add_issue_dependency`, etc.). If they are not available, stop and tell the user the MCP is not connected.
3. **Current directory maps to a Forgejo repo**, unless the user passed a full issue URL. The remote URL parsing is covered in Step 1 — if it fails, stop and ask.

Note: a dirty working tree is fine — this skill never touches the working tree.

## Step 1: Identify the parent issue

Extract two things from the user's request: the **issue number** and the **repo** (`owner/name`). Usually the user gives only the issue number and expects the repo to be inferred from the current directory.

Infer the repo from the git remote:

```bash
git remote get-url origin
```

Parse it:
- SSH form: `git@git.example.com:myorg/myrepo.git` → host=`git.example.com`, owner=`myorg`, repo=`myrepo`
- HTTPS form: `https://git.example.com/myorg/myrepo.git` → same
- Strip the trailing `.git` if present.

If the user gave a full issue URL like `https://git.example.com/myorg/myrepo/issues/42`, parse owner/repo/index from the URL — the URL wins over the current remote.

If neither gives you owner/repo, stop and ask.

## Step 2: Fetch the parent issue

Use the `forgejo` MCP's `get_issue` tool (taking `owner`, `repo`, `index`). Also pull comments via `list_issue_comments` — sometimes the plan has been revised in a comment rather than the body.

Read:
- **title** — source of sub-issue title prefixing (e.g. parent "Add caching layer" → children like "Add caching layer: wire up redis client").
- **body** — the plan itself. This is the main input.
- **labels** — inherit sensible labels onto children (e.g. `enhancement`, `infra`). Bug-tracker labels like `bug` should usually not propagate; ask if unsure.
- **state** — if the issue is closed, stop and ask whether to proceed anyway.
- **existing sub-issues** — before proposing anything, check `list_issue_dependencies` / `list_issue_blocking` on the parent. If children already exist, this skill has probably already been run. Surface that and ask whether to add more or stop.

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

- Blocked by: #<prior-phase-number> (omit section entirely if this is Phase 1)
- Blocks: #<next-phase-number> (informational; the dependency edge is set from the next phase's side)

## Validation

- <specific test(s) or check(s) that demonstrate this phase is done>
- Standard project gates: `just fmt`, `cargo clippy --all-targets -- -D warnings`, `just test`

## Out of scope

- <anything a reviewer might expect in this phase but that is deferred to a later phase — cite the phase number>

---
_Filed via the `forgejo-issue-to-subissues` skill. Parent: #<parent-number>._
```

**Reference the plan; do not restate it.** A sub-issue should carry scope,
constraints, and acceptance in prose — not the plan's code, signatures, or SQL.
This is not a style preference. Implementations diverge from plans, and when
they do, the plan gets corrected (see Step 6a of `forgejo-issue-to-pr`). Every sub-issue that
copied a detail out of the plan is now a second place holding a stale version of
it, with nothing linking the two. Twelve thin issues take one plan edit to
reconcile; twelve fat ones take thirteen, and the ones nobody remembers to check
stay wrong until they cost somebody an afternoon.

If a phase genuinely needs a concrete API or schema pinned in the issue itself,
that is a signal the plan is the wrong place for it — or that the phase is
under-specified. Fix that, rather than duplicating.

Omit sections that don't apply rather than leaving them empty. The `Part of #N` line and footer are load-bearing: `forgejo-issue-to-pr` will read the parent link to understand context when someone picks this sub-issue up.

## Step 8: Create the sub-issues

Create them **in phase order**, because Step 9 needs the earlier issues' numbers to set dependency edges on later ones.

For each phase, in order:

1. Call the `forgejo` MCP `create_issue` tool with `owner`, `repo`, `title`, `body`, `labels`.
2. Record the returned issue number and URL.
3. If the create response omits the URL, construct it: `https://<host>/<owner>/<repo>/issues/<index>`.

Do **not** assign the sub-issues to a user automatically. Do **not** set a milestone unless the parent has one — if it does, inherit it onto the children via the MCP's `edit_issue` tool after creation (the `create_issue` schema may or may not accept `milestone` directly; pick whichever path works).

If a `create_issue` call fails partway through the list, stop and report:
- which sub-issues were filed (with numbers)
- which one failed and the error
- the remaining phases that were not attempted

Do not retry blindly — a failure here usually means something is off with the MCP or the repo state, and filing duplicates on retry would be worse.

## Step 9: Wire up dependencies

Forgejo supports issue dependencies ("this issue depends on / blocks that one"). Use them so the timeline of the epic is visible in the tracker itself.

For each consecutive pair of phases `(N, N+1)` in the ordered list: mark phase N+1 as depending on phase N. The `forgejo` MCP tool is likely `add_issue_dependency` — it takes the issue that *has* the dependency and the issue it *depends on*. Double-check the direction with the tool's description; the two directions are easy to flip.

Also mark the parent as depending on every sub-issue, so the parent closes naturally once all children are done. (This assumes the Forgejo repo has "auto-close parent when all dependencies closed" enabled; if not, it's still useful as a visible link.)

If the breakdown included parallel phases (e.g., Phases 3 and 4 both depend on Phase 2, and Phase 5 depends on both), apply those exact edges rather than forcing a linear chain.

If the MCP's dependency tools are not present or fail, **do not block the whole run** — fall back to making each sub-issue body's "Blocked by" line load-bearing and call out in the Step 10 summary that the in-tracker dependency edges were not set.

## Step 10: Index the sub-issues on the parent

Add a comment to the parent issue listing the filed sub-issues, in phase order. Use the `forgejo` MCP `create_issue_comment` tool (`owner`, `repo`, `index`, `body`).

Comment template:

```markdown
Decomposed into the following sub-issues (in order):

- [ ] #<n1> — <phase 1 short title>
- [ ] #<n2> — <phase 2 short title>
- [ ] #<n3> — <phase 3 short title>

Filed via the `forgejo-issue-to-subissues` skill. Each sub-issue can be actioned independently by `forgejo-issue-to-pr`.

<If a checked-in plan backs these issues, add: "`<plan-path>` is the source of truth for the detail — these issues carry scope and acceptance only. A change that diverges from the plan is corrected in the plan, not just in the changelog.">
```

Do **not** rewrite the parent issue body to insert this list. Editing the body risks clobbering user edits or the original plan; a comment is the safe, append-only choice.

## Step 11: Report back

End with a short summary:

- parent issue number and URL
- each sub-issue number, title, and URL (in phase order)
- whether dependency edges were wired up (yes / no / partial — per Step 9)
- a one-line pointer: the user can run `forgejo-issue-to-pr` against the first sub-issue number when ready to start implementation

Keep it tight. The sub-issue URLs are the point.

## Edge cases worth remembering

- **Parent is itself a sub-issue** (has a `Part of #M` line): re-parent onto the grandparent, or stop and ask. Nesting sub-issues under sub-issues is almost never what the user wants.
- **Plan is in a comment, not the body**: use the latest plan-shaped comment. If the body and a comment disagree, surface the conflict and ask which is authoritative — don't guess.
- **Repo has an issue template**: if `.gitea/ISSUE_TEMPLATE/` or `.forgejo/ISSUE_TEMPLATE/` exists and its structure materially conflicts with the sub-issue body template above, adapt — the project's template wins.
- **Parent has a milestone**: inherit it onto children (via `edit_issue` after creation if needed), so the milestone progress bar reflects the true unit of work.
- **Fork remote**: if `git remote -v` shows an `upstream`, the parent issue probably lives on upstream. Use upstream's owner/repo for all MCP calls; the user's fork is irrelevant here since nothing is being pushed.
- **Partial prior run**: if Step 2 finds some but not all phases already filed as sub-issues, treat the breakdown as *resumable* — propose only the missing phases and wire dependencies around what's already there. Do not re-file duplicates.
- **User wants fewer sub-issues than the plan has phases**: honor it. Merge phases in the breakdown so each sub-issue still has a coherent scope. Don't lose content — anything merged in should appear in the sub-issue body.
- **User wants more sub-issues than phases**: split a phase only when there is a clean seam (two files, two features, two tests). Splitting on an artificial seam produces sub-issues that can't be reviewed independently.
- **MCP lacks a dependency tool**: fall back gracefully (see Step 9) rather than aborting. The textual "Blocked by" line in each sub-issue body is the backup.
