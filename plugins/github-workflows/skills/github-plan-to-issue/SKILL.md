---
name: github-plan-to-issue
description: "Plan-first workflow that turns a feature idea into a well-structured GitHub issue using the `gh` CLI. Enters plan mode to shape the feature with the user, then commits the finalized plan to the repository's issue tracker so it can be actioned later (e.g. by the `github-issue-to-pr` skill). Use this skill whenever the user asks Claude to \"plan a feature\", \"file a feature issue\", \"create a feature plan in github\", \"turn this idea into an issue\", \"draft an issue for X\", \"let's plan X and track it\", or any similar phrasing that implies producing a GitHub issue from a design discussion. This is a plan-then-commit workflow — do not create the issue until the plan has been explicitly accepted."
---

# GitHub Plan → Issue

Plan-first workflow: shape a feature idea with the user in plan mode, then file it as a structured GitHub issue that a future session (human or agent) can pick up and implement. The deliverable is the issue URL.

This skill is the upstream counterpart to `github-issue-to-pr`. The two are designed to compose: the issue body produced here should be rich enough that `github-issue-to-pr` can read it later and go straight to implementation without re-deriving the design.

## Prerequisites

Before starting, confirm:

1. **Inside a git repository.** `git rev-parse --show-toplevel` should succeed. If not, stop and tell the user.
2. **The `gh` CLI is installed and authenticated.** Run `gh auth status`. If `gh` is missing or unauthenticated, stop and tell the user — suggest they run `! gh auth login` themselves, since it is interactive.
3. **Current directory maps to a GitHub repo.** Repo resolution is covered in step 1 — if it fails, stop and ask.

Note: a dirty working tree is fine for this skill — we are not committing code, just filing an issue.

## Step 1: Identify the target repository

`gh` infers the repo from the git remote automatically, so inside the repo you usually don't need to pass anything. To confirm what it resolved to:

```bash
gh repo view --json nameWithOwner,defaultBranchRef -q '.nameWithOwner, .defaultBranchRef.name'
```

If the user named a different repo explicitly ("file this against owner/other-repo"), that wins over the remote — pass it as `--repo owner/other-repo` on every `gh` call. If neither gives you owner/repo, stop and ask.

Note: for a GitHub Enterprise host, the remote's host will not be `github.com`; `gh` handles this if the host is configured (`gh auth status` shows it). If it isn't, stop and tell the user.

## Step 2: Gather the raw idea

The user will usually give a short seed: "I want a skill for X", "we should add Y", "let's plan a feature to Z". Before entering plan mode, collect whatever context you'll need to plan sensibly:

- Read any files the idea clearly touches — don't plan in the dark.
- If the idea references a pattern already in the repo (e.g. "like the github-issue-to-pr skill but for issues"), read that reference so the plan mirrors its conventions.
- Skim `README.md`, `CLAUDE.md`, and any `justfile` / `Cargo.toml` to learn the project's conventions (toolchain, style, validation commands). The issue will be actioned under those rules.

If the idea is genuinely ambiguous after reading the code ("add caching" — to what? with what semantics?), ask one or two focused clarifying questions before going further. Do not guess on fundamentals — a well-planned issue is the whole point of this skill.

## Step 3: Enter plan mode

Use `ExitPlanMode`'s counterpart `EnterPlanMode` to move into plan mode explicitly. Plan mode is the right venue here because:

- it signals to the user that you are *designing*, not editing
- it produces a structured plan artifact the user can accept or reject
- the accepted plan becomes the seed of the issue body

Inside plan mode, develop the plan using the structure in Step 4. Do not write any code or edit files in plan mode — this skill never touches the working tree.

## Step 4: Shape the plan

The plan must cover, at minimum:

1. **Problem / motivation** — why this feature exists. One paragraph. What does the user want that they don't have today?
2. **Proposed behavior** — what the feature does from the outside. User-facing description, not implementation. Cover the golden path and at least the obvious edge cases.
3. **Implementation sketch** — the shape of the change. Name the files, modules, or components that will be touched or created. Call out new dependencies, new public types, new CLI flags, new config keys, new environment variables.
4. **Validation strategy** — how a future agent will know the feature works. Which tests should exist? Are there manual verification steps (e.g. "run `just` target X and observe Y")? Reference the project's standard validation commands (e.g. `just fmt`, `cargo clippy`, `just test`) so the implementer knows what bar to meet.
5. **Out of scope** — what this issue explicitly does *not* cover. Prevents scope creep when someone picks it up later.
6. **Open questions** (optional) — anything the user explicitly deferred. Keep this section only if there are genuine unresolved decisions; do not invent questions to look thorough.

Length target: enough to implement from, not a novel. Two or three screens of markdown is usually right. If the plan is growing past that, the feature probably wants to be split across multiple issues — suggest that to the user.

## Step 5: Present the plan and get acceptance

Exit plan mode with the structured plan via `ExitPlanMode`. The user will accept or reject.

- **Rejected / revise**: iterate. Go back to Step 3 or 4 as needed. Do not file an issue from a rejected plan.
- **Accepted**: proceed to Step 6. Acceptance of the plan is acceptance of the issue body — do not ask for a second round of confirmation before filing.

## Step 6: Choose labels

Feature planning issues almost always want an `enhancement` or `feature` label so the future `github-issue-to-pr` run picks the `feat-` branch prefix. Check what labels the repo actually has:

```bash
gh label list --json name -q '.[].name'
```

Pick the closest match from what exists — don't invent new labels silently. Preference order:

1. `enhancement`
2. `feature`
3. `feat`
4. If none of those exist, file with no label and note it in the final summary so the user can add one manually.

New GitHub repos ship with a default `enhancement` label, so option 1 usually hits. `gh label create <name>` exists, but only use it if the user explicitly asks for a new label.

Additional labels are fine if the plan clearly fits one (e.g. `documentation` if the feature is doc-only, `infra` if it's tooling). Don't over-tag.

## Step 7: Compose the issue

**Title**: imperative mood, concise, under ~72 chars. Mirror the phrasing the user used for the feature where possible so it's recognizable to them later.

- Good: `Add github-plan-to-issue skill for design-first issue creation`
- Bad: `Feature request: it would be nice if we could maybe plan things` (vague, wordy, passive)

**Body template**:

```markdown
## Problem

<one paragraph — what's missing today and why it matters>

## Proposed behavior

<user-facing description of the feature. Bullets or prose, whichever
is clearer. Cover the golden path and the obvious edge cases.>

## Implementation sketch

- <file / module / component to touch or create>
- <new dependency, if any, and why>
- <new public type, flag, config key, env var, etc.>

## Validation

- <specific test or check that should pass>
- Standard project gates: `just fmt`, `cargo clippy --all-targets -- -D warnings`, `just test`

## Out of scope

- <thing this issue will not address>

## Open questions

- <only include if genuinely unresolved; omit the section otherwise>

---
_Filed via the `github-plan-to-issue` skill. Ready to be actioned by `github-issue-to-pr`._
```

Strip any section that doesn't apply (e.g. no open questions) rather than leaving it empty. The trailing footer is load-bearing: it tells the next agent that this issue was produced from an accepted plan, so the implementation sketch is authoritative — not just a suggestion.

## Step 8: Create the issue

```bash
gh issue create --title "<title>" --body-file <path-to-body.md> --label <label>
```

Write the body to a file in the scratchpad rather than wrestling with shell quoting on a multi-line `--body`. Repeat `--label` per label if you picked more than one.

Do **not** assign the issue to a user automatically (no `--assignee`). If the user wants it assigned to them, they'll say so; otherwise leave it unassigned so it's visible as open work.

Do **not** set a milestone (`--milestone`) unless the user named one explicitly.

`gh issue create` prints the new issue URL on stdout — capture it, you need it for the next step.

## Step 9: Report back

End with a short summary:

- issue number and URL (from `gh issue create`'s output — use what it printed rather than constructing a URL; if you lost it, `gh issue list --limit 1 --json number,url` gets it back)
- labels applied (or a note if none matched — see Step 6)
- a one-line pointer that the user can run `github-issue-to-pr` against this issue number when they're ready to implement

Keep it tight. The issue URL is the point.

## Edge cases worth remembering

- **User gave a one-liner and resists planning** ("just file it"): offer to file a lightweight issue with only Problem + Proposed behavior, and skip plan mode. Name the tradeoff — a thinner issue is harder to action later.
- **Duplicate of an existing issue**: before filing, optionally run `gh issue list --state open --search "<keywords>"` and scan titles for obvious duplicates. If you spot one, surface it and ask whether to add a comment there (`gh issue comment <number> --body-file <path>`) instead of filing new.
- **Repo has an issue template**: if `.github/ISSUE_TEMPLATE/` or `.github/ISSUE_TEMPLATE.md` exists, read it. If its structure materially conflicts with the body template above, adapt — the project's template wins.
- **Issue template is a YAML form** (`.github/ISSUE_TEMPLATE/*.yml` with `body:` fields): there is no clean way to submit form-structured issues from `gh` — `gh issue create --body-file` posts free-form markdown regardless. File the markdown body, mirroring the form's field labels as headings so it reads as if the form were filled in, and mention the mismatch in the final summary.
- **Repo has issues disabled**: `gh issue create` fails outright. Stop and tell the user — the issue may belong on a different repo (e.g. a dedicated tracker).
- **Label doesn't exist**: `gh issue create --label <name>` errors rather than creating the label. If the call fails on a label, re-run without `--label` and note it in the summary — don't block on it.
- **`gh` prompts to create a fork**: it does this when you lack push access. Filing an issue doesn't need push access, but if a prompt appears it will hang — stop and ask the user rather than accepting a fork on their behalf.
- **Plan reveals the feature is already implemented**: stop and tell the user. Don't file an issue for work that's done.
- **Plan grows too large**: suggest splitting into multiple issues with a brief map of how they relate. File them as a set only after the user agrees to the split.
- **Fork remote**: if `git remote -v` shows an `upstream`, the issue probably belongs on upstream, not the user's fork. Confirm with `gh repo view --json parent` and pass `--repo <upstream-owner>/<repo>` on the `gh issue` calls.
