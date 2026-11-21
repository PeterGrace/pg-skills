---
name: forgejo-issue-to-pr
description: "End-to-end workflow that turns a Forgejo issue into a pull request using the `forgejo` MCP server (raohwork/forgejo-mcp). Reads the target issue, creates a feature branch, implements a fix, runs `just fmt`, `cargo clippy`, and `just test` to validate, has a fresh subagent on a different model audit the change's claims with claims-mcp (updating the repo's `claims.json` ledger when it has one), commits and pushes, opens a PR, and links the PR back to the issue as a comment. Use this skill whenever the user asks Claude to \"fix issue N\", \"work on issue N\", \"look at issue N and open a PR\", \"take a look at <forgejo-issue-url>\", \"implement the fix for that issue\", or any similar phrasing that implies turning a Forgejo issue into a ready-for-review PR. This is a push-through workflow — do not stop for confirmation between steps unless validation fails or the issue is genuinely ambiguous."
---

# Forgejo Issue → PR

Push-through workflow: read an issue on a Forgejo instance, implement a fix, validate it, push a branch, open a PR, and comment back on the issue. No mid-flight check-ins unless a validation step fails or the problem is genuinely unclear.

## Who does the work

**If you are a subagent** (for example the `issue-implementer` agent), skip this section: you are the implementer, so run the steps below yourself, shell commands included.

**If you are the parent (top-level) session, delegate.** Don't run the steps below yourself.

- **Every piece of work you spawn goes to the `issue-implementer` agent config:** `Agent` with `subagent_type: "github-workflows:issue-implementer"`. Use it for one issue or for several (one agent per issue). Never use `general-purpose`, a fork or an unnamed agent for this. The claims auditor in Step 7a is not yours to spawn: the implementer dispatches it from inside its own run.
- **Give it a worktree.** If this session is already in a worktree for this issue, name that path and its branch in the brief. Otherwise pass `isolation: "worktree"` so you don't have to run `git worktree add` yourself.
- **Brief it** with the Forgejo host, the repo (`owner/name`), the issue number or URL, the worktree path and branch, and anything specific to this task that the user said. Its standing rules (gates, attribution, never merge) live in its config, so don't repeat them.
- **Avoid shell commands in the parent whenever you can.** Let the implementer run `git` and the gates. If you need to read the issue or check the PR, use the `forgejo` MCP tools (`get_issue`, `get_pull_request`). If you need to look at code, use Read and Grep, not `cat` or `grep` in Bash. Only reach for Bash when no other tool can do the job and the work can't wait for the subagent.
- **Relay its report** to the user: the PR URL, gate results, claims-audit counts, and anything it flagged. Keep the agent's ID, because you message it later with SendMessage to address the PR's review once it has been reviewed.
- **Clean the worktree when the PR is done.** Once the PR has merged (or is abandoned) and nothing is still running there, delete the build output before the worktree goes. This applies to a worktree you named and to one `isolation: "worktree"` created: the harness keeps a worktree that has changes, so it isn't cleaned up for you.
  - If the repo has a script for it, use it (for example okf_mcp's `tools/agentic/remove-worktree.sh <path> --branch`).
  - Otherwise, in a Rust repo, run `cargo clean` in the worktree (bounded, for example `timeout 10m cargo clean`), then `git worktree remove`.
  - Why: `build-dir` in `~/.cargo/config.toml` puts each worktree's build in its own directory under `~/.cache/cargo-build/`, which `git worktree remove` leaves behind (30-47 GiB per worktree on okf_mcp). The implementer doesn't clean; its config leaves that to you.

## Prerequisites

Before starting, confirm:

1. **Inside a git repository.** `git rev-parse --show-toplevel` should succeed. If not, stop and tell the user.
2. **The `forgejo` MCP is connected.** Its tools show up with a `forgejo` prefix (likely `get_issue`, `create_pull_request`, `create_issue_comment`, etc.). If they are not available, stop and tell the user the MCP is not connected.
3. **Working tree is clean-ish.** Run `git status --porcelain`. If there are uncommitted changes, ask the user whether to stash them before continuing — do not silently stash or commit their work onto a new branch.

## Step 1: Identify the target issue

Extract two things from the user's request: the **issue number** and the **repo** (`owner/name`). The user will usually only give the issue number and expect you to infer the repo from the current directory.

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

## Step 2: Fetch the issue

Use the `forgejo` MCP to retrieve the issue. The tool is likely `get_issue` and takes `owner`, `repo`, and `index` (the issue number). If the exact name differs, pick the closest equivalent — the MCP's tool descriptions make the mapping obvious.

Read:
- **title** — source of branch name and PR title
- **body** — the problem statement; read it carefully
- **labels** — useful for choosing a branch/commit prefix (`bug` → `fix-`, `enhancement` → `feat-`)
- **comments** — sometimes the actual desired fix is in a comment rather than the body. Fetch them if any exist.
- **state** — if the issue is already closed, stop and ask the user whether to proceed anyway.

## Step 3: Plan the fix briefly

Before editing, read the relevant source files to confirm the approach. State the plan in one short paragraph — for the record, not for permission — then proceed.

If after reading the code the intent is genuinely ambiguous (e.g., "X is broken" but three things could plausibly be X), stop and ask. Do not guess on fundamentals.

## Step 4: Create and check out a branch

Naming convention: `<prefix>-issue-<number>-<slug>` where:
- **prefix**: `fix` if labels contain "bug", `feat` if labels contain "enhancement" or "feature", otherwise `issue`.
- **slug**: 2–5 words, lowercase kebab-case, derived from the issue title, max ~40 chars.

Example: issue #42 titled "Panic when parsing empty config file" with label `bug` → `fix-issue-42-panic-empty-config`.

```bash
git checkout -b <branch-name>
```

If the branch already exists locally, append `-v2` (or higher) rather than clobbering it.

## Step 5: Implement the fix

Make the code changes. Keep edits scoped to what the issue asks for — this is not the time for drive-by refactors unless they are strictly needed for the fix.

## Step 6: Validate (mandatory)

Run these three commands, in order, from the repo root. **All three must pass before you push.** If any fails, fix it and re-run the full sequence from the top — don't just re-run the one that failed, since formatting or clippy fixes can affect tests and vice versa.

```bash
just fmt
cargo clippy --all-targets -- -D warnings
just test
```

Notes:
- `-D warnings` on clippy treats warnings as errors. If that turns out to be too strict for this project, drop `-- -D warnings` and just run `cargo clippy --all-targets`, but surface any warnings you see in the PR summary.
- If the project has no `Cargo.toml`, skip `cargo clippy` and note it in the summary. `just fmt` and `just test` still run.
- If the project has no `justfile`, or the `fmt` / `test` recipes don't exist in it, **stop and tell the user** — this skill assumes that toolchain is present, and substituting silently is worse than asking.

If validation keeps failing after a few honest attempts, **do not push broken code.** Commit what you have on the branch locally, then stop and summarize for the user what's stuck — they can decide whether to push a draft/WIP PR manually or hand the work back.

### Also: exercise the artifact you just added

The three commands above are the *workspace* gate — they check that Rust code still compiles, lints, and tests. They do **not** validate the specific thing this PR delivers.

If your change adds or modifies a runnable artifact, run it. **Probe for the tools first** (e.g. `which docker`, `docker version`, `which helm`) before assuming they're absent — "deferred to a manual test plan" is the wrong default when the tool is one shell command away.

Examples:
- Added a `justfile` recipe → run the recipe.
- Added a `Dockerfile` → `docker build` it, check the resulting image actually runs, and verify any size/contract the issue specified.
- Added a Helm chart change → `helm template` it; if a kind/k3d is available, `helm install` into it.
- Added a CI workflow → if `act` or similar is present, run it; otherwise at minimum lint it and inspect the job graph.

If the issue body specifies an acceptance criterion you can check locally (image size under N MiB, binary exits 0, output matches a snapshot), **actually check it** — don't restate it back as a future TODO.

If you genuinely can't run the artifact (no Docker daemon, no cluster, etc.), say so explicitly in the PR body and name the missing tool. Don't silently punt to the PR's manual test plan.

## Step 6a: Reconcile the plan and downstream issues

Only applies when the issue names a plan — "Implements Task N of
`docs/.../some-plan.md`" or similar. Skip if there is no such document.

That plan is a **live instruction set** for the tasks that have not been done
yet, not a historical record. Git holds the history. A plan describing code that
no longer exists is not a record, it is a set of wrong instructions with a date
on it.

So whenever your implementation differs from what the plan specifies — a
different API, a renamed symbol or method, a step that turned out unnecessary,
something you deliberately did not build — do all three of these **before you
commit**:

**1. Edit the plan.**

- Mechanical changes (a wrong method name, a changed signature, a superseded
  SQL statement): fix the code inline so the next person can copy it and have it
  compile.
- Design changes (a different structure, an approach replaced wholesale): leave
  the plan's code and add a short block quote above or below it —
  `> **Superseded (issue #N).** ...` — saying what shipped instead and naming
  the file to read. Do not transcribe a whole implementation into a plan.
- Something deliberately not built: say so, and say why, at the point where the
  plan asks for it.

The changelog records *why*. The plan must record *what*, because the plan is
what the next implementer executes from.

**2. Grep the plan for every symbol you changed.**

```bash
grep -n "<symbol>" <plan-path>
```

Do this for each renamed method, changed signature, dropped table, or removed
step — then check every hit that belongs to a task not yet implemented.

**This is the step that pays.** A method name that was wrong in your task is
usually still wrong in two or three later ones, and those are compile errors
somebody else eats, weeks from now, with no idea they were predictable. Fix them
in the same pass.

**3. Comment on the open issue for any later task your change affects.**

Name the task, say what changed, and say what they should do differently. An
issue that restates the stale detail in its own body needs editing, not just a
comment.

Then note the reconciliation in the PR body, so the reviewer sees the plan diff
was intentional rather than scope creep.

**Do not skip this because you wrote a changelog.** A changelog is append-only:
it is the right place for the reasoning and the wrong place for the instruction,
because nobody reads it at the moment it matters. Writing one is not evidence
the divergence has been handled.

## Step 7: Commit

Clear, descriptive commit message, roughly:

```
<type>: <short imperative summary, under ~72 chars>

<Optional body: what changed and why, wrapped around 72 chars.
If there are multiple logical changes, one paragraph each.>

Closes #<issue-number>
```

`<type>` maps to the same buckets as the branch prefix (`fix`, `feat`, `refactor`, `docs`, `chore`, etc.). The `Closes #N` trailer is important — Forgejo auto-closes the linked issue when the PR merges.

Split into multiple commits only if the fix is genuinely multi-step (e.g., a prep refactor then the actual fix). Otherwise one commit is cleaner. The claims ledger, if any, gets its own commit in Step 7a.

## Step 7a: Audit the claims (mandatory)

The gates in Step 6 check that the code builds and its tests pass. This step checks that the change does what the issue asked and what the PR body is about to say, and that it didn't break anything the project's claims ledger records as working. The full method is the "Auditing a pull request" section of the `claims-audit` skill (install it from claims-mcp, following [its install guide](https://hypotheosis.github.io/claims-mcp/guides/install.html#3-install-the-skill)); this step is the part this workflow must do.

**1. Pick the mode.**
- **Ledger mode**: `git ls-files --error-unmatch claims.json` succeeds. Findings go into the ledger and are committed on the branch.
- **Table-only mode**: no tracked `claims.json`. The audit runs the same way but makes **no** claims-mcp calls at all (a write creates `claims.json`, and even a read creates `.claims.json.lock`; delete either if it appears), and its results go into the PR body **without claim ids**. Ids recorded nowhere would not match those a ledger assigns later.
- **Which ledger the tools write.** The `claims` MCP server opens `claims.json` relative to the directory this session started in. If this checkout is not that directory (you are in a git worktree, for example), the MCP tools would write the wrong ledger and pin the wrong commit. In that case the auditor passes `"catalog": "<this checkout>/claims.json"` (absolute path) on **every** claims tool call, reads included. First, check that the server honours `catalog`: `list_claims` with `"catalog": "/nonexistent-claims-probe/claims.json"` must return an error **that names `/nonexistent-claims-probe/`** (a 0.2.5+ server cannot open a ledger in a missing directory; don't probe with an empty string, which some clients drop). If it succeeds, the server predates `catalog` (before 0.2.5) and is ignoring it; if it fails with any other error, the result is inconclusive (an old server reading its own ledger can fail for unrelated reasons). Either way, stop and ask the user to upgrade claims-mcp and restart the session or reconnect the server (`/mcp`). Don't trust the tool schema you see for this; a client can keep showing the schema from before a reconnect.

**2. Draft the PR body now**, using the Step 9 template, into a scratch file. Its statements of fact are claims the audit checks.

**3. Dispatch the auditor: a fresh subagent on a different model** from yours (Agent tool with `model: "sonnet"` when you are Opus; another model family if you are already on Sonnet). Give it only:
- the issue URL, title, body and any comments that change the requirements;
- the path of the draft PR body;
- the repo path and the commit range `<default-branch>..HEAD`;
- the mode and, in ledger mode, the ledger path and whether to pass it as `catalog` on every call;
- the instruction: "Follow the claims-audit skill's 'Auditing a pull request' section. Return, per claim: id (ledger mode only), statement, verdict, key evidence locator, ours or elsewhere, and the `Fix:` step for anything not supported; then the `recheck` findings and the evidence ids you recorded."

Do **not** give it your plan, reasoning or summary of what you did. That is the producer's account, and the audit must not rest on it.

**4. Act on the verdicts.**
- **Refuted and ours.** These are claims from the issue or the PR body, or existing claims whose anchors this diff changed. Fix them. Fix the code, then go back through Step 6 and commit. If what was wrong is a statement in the PR body, correct the draft instead. Then send the same auditor (SendMessage resumes a finished subagent) the new commit range and the list of claims to re-audit; if it can't be resumed, start a fresh auditor on the same model with the previous hand-back. Repeat until no "ours" claim is refuted. If you can't get there after a few honest attempts, treat it like a validation failure: don't push, and report to the user.
- **Refuted and elsewhere.** These are problems in code this PR didn't touch. They stay recorded as refuted with their `Fix:` step and don't block the PR. List them in the PR body as pre-existing.
- **`not_enough_info`.** These never block. List each with what would decide it.

Check the auditor's numbers against `audit_report` (ledger mode) before you copy them into the PR body. An agent's summary is not evidence.

**5. Commit the ledger (ledger mode).** Before committing, check whether main's ledger moved:

```bash
git fetch origin && git diff --quiet $(git merge-base HEAD origin/<default-branch>) origin/<default-branch> -- claims.json
```

If it changed, two branches have handed out the same ids. Git may merge that silently into a ledger the server refuses to read. Do not merge or edit `claims.json` by hand. Run `git checkout origin/<default-branch> -- claims.json`, have the auditor record its findings again from its hand-back, and update the ids in the draft PR body. Then:

```bash
claims-mcp --catalog claims.json verify
git add claims.json && git commit -m "chore(claims): audit the change for #<issue-number>"
```

`verify` must pass. If it doesn't, stop and tell the user; never run `claims-mcp seal --adopt`.

**6. Merge method.** Ledger anchors pin this branch's commits, and a squash or rebase merge leaves them `commit_missing`. Check the repository's allowed merge styles with the `forgejo` MCP (`get_repository`; look for a field like `allow_merge_commits`). If merge commits are not allowed, say in the PR body and in your report that the ledger's anchors on this PR won't survive the merge.

## Step 8: Push

```bash
git push -u origin <branch-name>
```

`-u` sets upstream so future pushes from this branch are parameter-less.

## Step 9: Open the PR

Use the `forgejo` MCP to create the pull request. The tool is likely `create_pull_request` with roughly these fields: `owner`, `repo`, `title`, `body`, `head` (the new branch), `base` (the target branch).

For `base`, determine the repo's default branch:

```bash
git symbolic-ref refs/remotes/origin/HEAD   # e.g. refs/remotes/origin/main
```

Fall back to `main`, then `master`, if that command fails. The issue response from step 2 may also include a default branch field you can use.

**Title**: Mirror the issue title, prefixed to match the branch type. E.g., issue titled "Panic when parsing empty config file" with a `bug` label → PR title `fix: panic when parsing empty config file`.

**Body template**:

```markdown
## Summary
<1–3 sentences on what this PR does and why>

## Changes
- <bullet per meaningful change>

## Validation
- `just fmt` ✅
- `cargo clippy` ✅
- `just test` ✅

## Claims
<From Step 7a. A table of every claim the audit checked: the issue's
requirements, this body's own statements, and existing ledger claims
it re-audited. Refuted first, then not_enough_info, then supported.

| Claim | Verdict | Evidence |
|-------|---------|----------|
| CLM-0044 "README lists every subcommand" (pre-existing) | refuted | `seal` missing from README.md:120; Fix: add it |
| CLM-0190 "parse_config rejects files over 1 MiB" | supported | `cargo test config::too_large` (1 passed) |

Ledger mode: start each Claim cell with its id, and end the section with
"Merge with a merge commit: the ledger's anchors pin this branch's commits."
Table-only mode: no ids anywhere, and one line: "This repository has no
claims ledger; these findings were not recorded."
With more than about eight supported claims, collapse them into one line
listing each with a short citation.>

## Manual Test Plan
<Steps the reviewer can run to independently verify this change.
This is for the reviewer, not a TODO list for the author — anything
the author skipped belongs in the Validation section above, marked
honestly as not-yet-run. Write concrete commands with expected
outcomes, e.g.:

- `just controller-image-build` → succeeds; tagged `:dev` image present.
- `docker images r.gfpd.us/gfd/sandbawks-controller:dev` → size < 25 MiB.
- `docker run --rm r.gfpd.us/gfd/sandbawks-controller:dev --help` →
  binary loads under distroless (exits non-zero outside k8s is fine).

If the change has no reviewer-verifiable behavior beyond reading the
diff, delete this section rather than padding it.>

Closes #<issue-number>
```

Fill in real content for Summary and Changes. The Validation section should reflect what actually passed — do not tick boxes you did not run.

## Step 10: Link the PR back to the issue

Use the `forgejo` MCP to add a comment on the original issue. The tool is likely `create_issue_comment`, taking `owner`, `repo`, `index`, `body`.

Comment body:

```
Opened PR #<pr-number> to address this: <pr-url>
```

The PR URL usually comes back in the response from `create_pull_request`. If not, construct it: `https://<host>/<owner>/<repo>/pulls/<pr-number>`.

`Closes #N` in the PR body already creates a logical link — the comment is partly redundant, but it's useful because it surfaces the PR in the issue's timeline immediately rather than waiting for merge.

## Step 11: Report back to the user

End with a short summary:
- branch name
- PR number and URL
- which validation steps passed
- the claims audit: mode, counts by verdict, any refuted "elsewhere" claims, and whether the ledger was committed
- anything surprising encountered along the way

Keep it tight. The links are the point.

## Edge cases worth remembering

- **Dirty working tree at the start**: ask before stashing; never silently move the user's work.
- **Detached HEAD or otherwise unusual branch state**: stop, show `git status`, ask.
- **Issue references other issues/PRs as dependencies**: read them. If the fix is blocked by something unmerged, say so in the summary and don't push half a fix.
- **Validation flakes (known flaky test)**: re-run once. If still red, treat it as a real failure.
- **The claims MCP server is not connected, or predates `catalog`** (ledger mode only; table-only mode needs no server): stop before Step 8 and ask the user to connect or upgrade it (restart the session, or `/mcp` reconnect). If the user says to go on without it, skip the ledger, say so in the PR body's Claims section and in your report, and don't claim an audit that didn't run.
- **Pushing more commits after the audit** (review fixes, a merge of main): anchors stay pinned to the commits they were recorded on. Re-run Step 7a for the claims the new commits affect (`recheck` lists them), and re-check that main's ledger hasn't moved before pushing.
- **Remote is a fork**: `git remote get-url origin` gives the fork, but the issue probably lives on upstream. Check `git remote -v` for an `upstream` remote; if present, use that for the forgejo MCP calls and push the branch to `origin`. The PR `head` field will need the `<your-user>:<branch>` form.
- **Non-Rust project**: skip `cargo clippy`, keep the `just` commands. If `just` isn't set up either, stop and ask.
