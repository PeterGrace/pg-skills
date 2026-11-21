---
name: github-groom-issue
description: "Push-through workflow that turns a thin, vague, or under-specified GitHub issue into a well-formed, ready-to-implement work-item using the `gh` CLI. Reads the issue, investigates it against the actual codebase, archives the original title and description as a comment, then overwrites the body with a structured work-item (templated by issue type — bug / feature / chore) that `github-issue-to-pr` can action without re-deriving the design. Hands off to `github-issue-to-subissues` when the work is too big for one PR. Use this skill whenever the user asks Claude to \"groom issue N\", \"clean up issue N\", \"flesh out issue N\", \"make issue N ready to work on\", \"turn issue N into a proper work-item\", \"investigate issue N and write it up\", \"tidy up <github-issue-url>\", or any similar phrasing that implies taking a rough issue and shaping it into something implementable. This is a push-through workflow — the normal path investigates and rewrites the body without an acceptance gate."
---

# GitHub Groom Issue

Push-through workflow: read a rough GitHub issue, investigate it against the real codebase, archive the original title and description as a comment, then overwrite the body with a well-formed work-item. The deliverable is an issue whose body is rich enough that `github-issue-to-pr` can go straight to implementation without re-deriving anything.

This skill sits between filing and implementation. `github-plan-to-issue` files a well-shaped issue from scratch; this skill *upgrades an existing rough one*. The groomed body is intentionally shaped to match what `github-issue-to-pr` expects to read.

The normal path has **no acceptance gate** — investigate and rewrite directly. It stops to ask only in the clear cases called out in the steps and edge cases below (issue closed, already groomed, premise false or already fixed, fundamentally ambiguous ask, body/comment conflict). For work that's too big for one PR, it hands off to `github-issue-to-subissues`; that skill runs its own plan-mode acceptance before any sub-issue is filed.

## Prerequisites

Before starting, confirm:

1. **Inside a git repository.** `git rev-parse --show-toplevel` should succeed — you need the code locally to investigate. If not, stop and tell the user.
2. **The `gh` CLI is installed and authenticated.** Run `gh auth status`. If `gh` is missing or unauthenticated, stop and tell the user — suggest they run `! gh auth login` themselves, since it is interactive.
3. **Current directory maps to a GitHub repo**, unless the user passed a full issue URL. `gh` resolves this from the git remote — confirming it is covered in Step 1. If it fails, stop and ask.

Note: a dirty working tree is fine — this skill never touches the working tree. It only reads code and edits the issue tracker.

## Step 1: Identify the target issue

Extract two things from the user's request: the **issue number** and the **repo** (`owner/name`). Usually the user gives only the issue number and expects the repo to be inferred from the current directory.

`gh` infers the repo from the git remote automatically, so inside the repo you can usually just use the issue number. To confirm what it resolved to:

```bash
gh repo view --json nameWithOwner,defaultBranchRef -q '.nameWithOwner, .defaultBranchRef.name'
```

If the user gave a full issue URL like `https://github.com/myorg/myrepo/issues/42`, parse owner/repo/number from the URL — the URL wins over the current remote. Pass it explicitly with `--repo myorg/myrepo` on every `gh` call.

If neither gives you owner/repo, stop and ask.

Note: for a GitHub Enterprise host, the URL host will not be `github.com`; `gh` handles this if the host is configured (`gh auth status` shows it). If it isn't, stop and tell the user.

## Step 2: Fetch the issue

```bash
gh issue view <number> --json number,title,body,labels,state,url,comments
```

The `comments` field carries the discussion — context, prior discussion, or a partial spec often lives in a comment rather than the body. `gh issue view <number> --comments` renders them more readably if you want a second look.

Read:
- **title** — you may sharpen it in Step 8, but don't rename wholesale; the user needs to still recognize it. **Capture the exact original title now** — it's archived alongside the body in Step 5.
- **body** — the raw ask. This is what you're grooming. **Capture the exact, verbatim original now** — you will archive it in Step 5.
- **labels** — first signal for the issue-type classification in Step 4.
- **comments** — read them all. If a comment already contains a partial spec, diagnosis, or correction, fold it into the groomed body (and attribute it — see Step 6).
- **state** — if the issue is already `CLOSED`, stop and ask the user whether to proceed anyway.
- **url** — keep it; you'll cite it in the final report.

### Detect an already-groomed issue

Before investigating, check whether this issue has already been groomed:
- Does the body already end with the `github-groom-issue` footer (see Step 6)?
- Is there an existing archive comment from a prior run? It begins with `🗄️ **Original description** — archived by \`github-groom-issue\``.

If either is true, this skill has likely already run. Surface that and ask whether to re-groom (which will archive the *current* groomed body as a new snapshot) or stop. Do not silently double-groom.

## Step 3: Investigate the codebase (the core of this skill)

This is the work that makes the difference between a tidy-looking issue and an *actionable* one. The point is to replace vague language with concrete, verified facts.

Investigate enough to answer:
- **Where does this land?** Name the real files, modules, or components the change touches. Read them — don't guess from filenames.
- **What is the current behavior?** Confirm what the code actually does today, so "X is broken" becomes "X does A; it should do B."
- **What's the seam?** Identify the specific function/type/config where the change goes, and any obvious ripple (callers, tests, docs).
- **Is the premise even true?** Sometimes investigation reveals the issue is already fixed, is a duplicate, or rests on a misunderstanding. If so, stop and report to the user rather than grooming a non-issue (see Edge cases).

Also skim the project's conventions so the groomed body points the implementer at the right bar: `README.md`, `CLAUDE.md`, `justfile`, `Cargo.toml` (toolchain, validation commands, style). **Note the project's real validation commands here** — you'll bake them into the body in Step 6.

Keep the investigation proportional. A one-line typo fix doesn't need a subsystem tour; a vague "make it faster" does. For a **performance issue** ("slow", "takes forever"), you can usually confirm the *mechanism* from reading code (e.g. an N+1 query, an O(n²) loop) even when you can't produce a hard latency number without a benchmark harness — capture the mechanism and keep the magnitude qualitative if that's all you can verify honestly.

If after honest investigation the ask is genuinely ambiguous on **fundamentals** (not just details you can reasonably decide), stop and ask one or two focused questions — a well-formed work-item is the entire point, and guessing wrong here poisons the downstream PR.

## Step 4: Classify the issue type

Pick exactly one type; it selects the body template in Step 6.

Decision order:
1. **Labels first.** `bug` → bug. `enhancement` / `feature` / `feat` → feature. `chore` / `refactor` / `docs` / `tech-debt` → chore.
2. **Body content second**, if labels are absent or unhelpful:
   - **bug** — describes something broken, wrong output, a crash, a regression, "doesn't work". **Performance/slowness reports also classify as bug** (degraded behavior the user is reporting); the Bug template's "Root cause" section is the right home for the diagnosis.
   - **feature** — asks for new behavior or capability that doesn't exist yet.
   - **chore** — refactor, cleanup, dependency bump, doc update, tooling, test-only work. No user-facing behavior change *and* not user-reported (a proactive perf refactor nobody reported as broken can be a chore; a user complaint about slowness is a bug).
3. When genuinely split (e.g. "fix the bug and also add a flag"), pick the **dominant** type and note the secondary work inside the body. Don't try to make one issue be two types.

## Step 5: Archive the original (always, before editing)

This is the safety net for the push-through overwrite. **Always do this, even for a minor groom**, and **always before** the `gh issue edit` in Step 8.

Write the archive comment to a file in the scratchpad and post it — use `--body-file` rather than wrestling with shell quoting on a multi-line `--body`:

```bash
gh issue comment <number> --body-file <path-to-archive.md>
```

```markdown
🗄️ **Original description** — archived by `github-groom-issue` before grooming.

**Original title:** <the exact original title from Step 2>

<the verbatim original body captured in Step 2, fenced or quoted exactly as-is>
```

Archiving the title too means the overwrite in Step 8 (which may also sharpen the title) is fully reversible from this one comment. If the original body was empty, say so explicitly (`_(Issue had no description.)_`) rather than posting an empty archive — the audit trail should record that there was nothing to preserve.

`gh issue comment` prints the comment URL on success — record it; you'll cite it in the final report.

## Step 6: Compose the groomed body

Use the template for the type chosen in Step 4. Fill every section with **concrete, investigated facts** — real file paths, real function names, real commands. A section you can only fill with vague restatement of the original is a signal you didn't investigate enough (go back to Step 3); the one allowed exception is a qualitative magnitude on a performance issue with no benchmark harness (see Step 3).

If you folded in a diagnosis or spec from someone's comment (Step 2), attribute it inline (e.g. "as @user noted") so the credit and provenance aren't lost when the body is rewritten.

**Validation lines:** the templates below show the Rust/`just` gates as the common case. Replace that line with the **real gates you confirmed in Step 3** for this project (e.g. `npm test` / `npm run lint`, `make check`, `pytest`). Don't prescribe a toolchain the repo doesn't use.

All three templates end with the same load-bearing footer, which tells `github-issue-to-pr` the body is authoritative.

**Bug:** (also used for performance issues — see notes in brackets)

```markdown
## Summary

<one paragraph: what's broken or degraded, in user-facing terms>

## Steps to reproduce

1. <concrete step>
2. <concrete step>
   [For a performance issue: the conditions that trigger the slowness, e.g.
   "apply N filters that reference related entities", rather than a crash repro.]

## Expected vs actual

- **Expected:** <what should happen>
- **Actual:** <what happens today — confirmed against the code. For a perf
  issue this may be qualitative ("latency grows linearly with filter count")
  if no benchmark number is available.>

## Root cause

<what the investigation found — the specific code path / condition responsible.
If not fully pinned down, say what's known and what's still suspected.>

## Fix sketch

- <real file / function where the fix lands>
- <ripple: callers, tests, docs to update>

## Validation

- <specific test that should pass / be added to prove the fix>
- Standard project gates: `just fmt`, `cargo clippy --all-targets -- -D warnings`, `just test`

## Out of scope

- <related things this issue deliberately does not fix>

---
_Groomed via the `github-groom-issue` skill. Ready to be actioned by `github-issue-to-pr`._
```

**Feature:** (mirrors `github-plan-to-issue` so the two compose identically)

```markdown
## Problem

<one paragraph — what's missing today and why it matters>

## Proposed behavior

<user-facing description. Golden path plus the obvious edge cases.>

## Implementation sketch

- <real file / module / component to touch or create>
- <new dependency, public type, CLI flag, config key, or env var>

## Validation

- <specific test or check that should pass>
- Standard project gates: `just fmt`, `cargo clippy --all-targets -- -D warnings`, `just test`

## Out of scope

- <thing this issue will not address>

---
_Groomed via the `github-groom-issue` skill. Ready to be actioned by `github-issue-to-pr`._
```

**Chore:**

```markdown
## Goal

<one paragraph — what improves and why it's worth doing now>

## Scope

- <files / areas / modules in scope>

## Steps

1. <concrete step grounded in the investigation>
2. <concrete step>

## Validation

- <how we know nothing regressed — usually the existing test suite stays green>
- Standard project gates: `just fmt`, `cargo clippy --all-targets -- -D warnings`, `just test`

## Out of scope

- <related cleanup deliberately deferred>

---
_Groomed via the `github-groom-issue` skill. Ready to be actioned by `github-issue-to-pr`._
```

Omit any section that genuinely doesn't apply rather than padding it. If the project ships an issue template under `.github/ISSUE_TEMPLATE/` whose structure materially conflicts with these, adapt to the project's template — but keep the footer.

## Step 7: Size check → decompose if too big

Before overwriting, judge whether the groomed item is realistically **one pull request**.

It is **too big** (→ decompose) when any of these hold:
- it spans multiple subsystems that would each be reviewed separately
- the implementation sketch naturally falls into ordered phases
- a single reviewer couldn't reasonably review the whole change in one sitting

It is **fine as one item** (→ skip to Step 8) when it's a coherent, single-PR change — most grooming lands here.

If too big:
1. Shape the body (Step 6) **with explicit phases** — e.g. a numbered "Implementation plan" with `## Phase 1`, `## Phase 2`, … — so the decomposition has clean seams to cut on.
2. Archive (Step 5) and overwrite the body (Step 8) **on this path too** — don't skip them because you're decomposing. (The archive happens once, at Step 5, as on every run; this is a reminder, not a second archive.) The parent issue should carry the full groomed plan before it's fanned out.
3. Then **invoke the `github-issue-to-subissues` skill** against this issue to fan the phases out into sub-issues. Do not reimplement decomposition here — hand off so the two skills stay in sync. That skill presents the breakdown in plan mode and waits for the user to accept before filing anything; "auto-decompose" means you *initiate the handoff automatically*, not that sub-issues get created without the user seeing the breakdown.

If `github-issue-to-subissues` is unavailable, don't block: leave the phased body in place and tell the user in the final report that decomposition is recommended and which skill to run.

## Step 8: Overwrite the issue body

Write the groomed body from Step 6 to a file in the scratchpad and replace the issue body with it:

```bash
gh issue edit <number> --body-file <path-to-groomed-body.md>
```

- The original is already safe in the Step 5 archive comment — this overwrite is intentional and reversible via that comment (which now holds the original title and body).
- Optionally sharpen the **title** in the same `gh issue edit` call (add `--title "<new title>"`) if it was vague (e.g. `it's broken` → `fix: panic on empty config`). Keep the leading subject word recognizable to the user — sharpen and prefix, don't replace the topic. Don't touch the title if it was already fine.
- **Labels:** if the type detected in Step 4 has no corresponding label on the issue and the repo actually has that label (check with `gh label list`), add it with `gh issue edit <number> --add-label <label>`. For a feature, prefer in order: `enhancement` > `feature` > `feat` (mirrors `github-plan-to-issue`). Don't invent labels that don't exist; note the gap in the report instead. (`--remove-label` is the counterpart if you need to drop a label the user asked you to drop — grooming does not remove labels on its own.)
- Do **not** assign a user or set a milestone unless the user asked.

## Step 9: Report back

End with a short summary:
- issue number and URL (the `url` field from the Step 2 `gh issue view --json` output)
- detected issue type (and any type label added, or a note that the matching label doesn't exist in the repo)
- a link to the archived-original comment (the undo path — restores both title and body)
- whether it was decomposed (and if so, a pointer to the sub-issues / the subissues run)
- a one-line pointer that the user can now run `github-issue-to-pr` against this issue number

Keep it tight. A groomed, ready-to-action issue is the point.

## Edge cases worth remembering

- **Investigation reveals it's already done / duplicate / false premise**: stop and report. Don't groom a non-issue into looking actionable. For a duplicate, point at the original issue.
- **Issue is closed**: stop and ask before grooming — reopening intent should be explicit.
- **Already groomed** (footer or prior archive comment present): ask before re-grooming; don't silently double-archive. See Step 2.
- **Original body is empty**: there's nothing to preserve — note that in the archive comment, and lean harder on investigation since the user gave you nothing to start from.
- **Spec or diagnosis lives in a comment, not the body**: fold the comment's content into the groomed body and attribute it. If body and comment disagree, surface the conflict and ask which is authoritative rather than guessing.
- **Repo has an issue template**: if `.github/ISSUE_TEMPLATE/` exists and materially conflicts with the Step 6 templates, the project's template wins — adapt, but keep the footer. Note that a GitHub *issue form* (`.yml` with `body:` fields) renders as a fixed set of headings in the filed body; if the original was filed from one, preserve those headings and slot the groomed content under them rather than replacing the structure wholesale.
- **Type label doesn't exist in the repo**: add nothing and note it in the report; don't create labels silently (mirrors `github-plan-to-issue`). `gh label create <name>` exists if the user explicitly asks for it — and note that label creation needs write access to the repo, which read-only collaborators won't have.
- **Insufficient permissions to edit the issue**: `gh issue edit` fails with a 403 if you only have read/triage access on the repo. Don't retry blindly — the archive comment may already be posted (commenting needs less permission than editing), so tell the user the original is preserved in the comment and hand them the groomed body to paste, or ask them to grant access.
- **GitHub Enterprise host**: if the issue lives on a GHE instance, confirm the host is authenticated (`gh auth status` lists configured hosts) and pass `--repo <host>/<owner>/<repo>` or set `GH_HOST`. If the host isn't configured, stop — `gh auth login --hostname <host>` is interactive and the user must run it.
- **Fork remote**: if `git remote -v` shows an `upstream`, the issue probably lives on upstream. Pass `--repo <upstream-owner>/<repo>` on every `gh` call; nothing is being pushed so the fork is irrelevant.
- **Issue is in a different repo than the code**: pass `--repo` on the `gh issue view` / `gh issue comment` / `gh issue edit` calls for the issue's repo, while investigating the code in the current directory. Say so in the report.
- **Genuinely ambiguous fundamentals**: ask one or two focused questions before composing — never guess on the core of what's being asked.
- **Non-Rust project**: the validation lines in the templates reference `just`/`cargo`; swap them for the project's real gates (confirmed in Step 3 — e.g. `npm test`, `make check`, `pytest`). Don't prescribe a toolchain the repo doesn't use.
