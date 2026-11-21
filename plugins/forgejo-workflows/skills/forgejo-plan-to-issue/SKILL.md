---
name: forgejo-plan-to-issue
description: "Plan-first workflow that turns a feature idea into a well-structured Forgejo issue using the `forgejo` MCP server (raohwork/forgejo-mcp). Enters plan mode to shape the feature with the user, then commits the finalized plan to the repository's issue tracker so it can be actioned later (e.g. by the `forgejo-issue-to-pr` skill). Use this skill whenever the user asks Claude to \"plan a feature\", \"file a feature issue\", \"create a feature plan in forgejo\", \"turn this idea into an issue\", \"draft an issue for X\", \"let's plan X and track it\", or any similar phrasing that implies producing a Forgejo issue from a design discussion. This is a plan-then-commit workflow — do not create the issue until the plan has been explicitly accepted."
---

# Forgejo Plan → Issue

Plan-first workflow: shape a feature idea with the user in plan mode, then file it as a structured Forgejo issue that a future session (human or agent) can pick up and implement. The deliverable is the issue URL.

This skill is the upstream counterpart to `forgejo-issue-to-pr`. The two are designed to compose: the issue body produced here should be rich enough that `forgejo-issue-to-pr` can read it later and go straight to implementation without re-deriving the design.

## Prerequisites

Before starting, confirm:

1. **Inside a git repository.** `git rev-parse --show-toplevel` should succeed. If not, stop and tell the user.
2. **The `forgejo` MCP is connected.** Its tools show up with a `forgejo` prefix (likely `create_issue`, `list_labels`, `get_repository`, etc.). If they are not available, stop and tell the user the MCP is not connected.
3. **Current directory maps to a Forgejo repo.** The remote URL parsing is covered in step 1 — if it fails, stop and ask.

Note: a dirty working tree is fine for this skill — we are not committing code, just filing an issue.

## Step 1: Identify the target repository

Infer the repo from the git remote:

```bash
git remote get-url origin
```

Parse it:
- SSH form: `git@git.example.com:myorg/myrepo.git` → host=`git.example.com`, owner=`myorg`, repo=`myrepo`
- HTTPS form: `https://git.example.com/myorg/myrepo.git` → same
- Strip the trailing `.git` if present.

If the user named a different repo explicitly ("file this against owner/other-repo"), that wins over the remote. If neither gives you owner/repo, stop and ask.

## Step 2: Gather the raw idea

The user will usually give a short seed: "I want a skill for X", "we should add Y", "let's plan a feature to Z". Before entering plan mode, collect whatever context you'll need to plan sensibly:

- Read any files the idea clearly touches — don't plan in the dark.
- If the idea references a pattern already in the repo (e.g. "like the forgejo-issue-to-pr skill but for issues"), read that reference so the plan mirrors its conventions.
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

Feature planning issues almost always want an `enhancement` or `feature` label so the future `forgejo-issue-to-pr` run picks the `feat-` branch prefix. Check what labels the repo actually has:

Use the `forgejo` MCP's label-listing tool (likely `list_labels`, taking `owner` and `repo`). Pick the closest match from what exists — don't invent new labels silently. Preference order:

1. `enhancement`
2. `feature`
3. `feat`
4. If none of those exist, file with no label and note it in the final summary so the user can add one manually.

Additional labels are fine if the plan clearly fits one (e.g. `documentation` if the feature is doc-only, `infra` if it's tooling). Don't over-tag.

## Step 7: Compose the issue

**Title**: imperative mood, concise, under ~72 chars. Mirror the phrasing the user used for the feature where possible so it's recognizable to them later.

- Good: `Add forgejo-plan-to-issue skill for design-first issue creation`
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
_Filed via the `forgejo-plan-to-issue` skill. Ready to be actioned by `forgejo-issue-to-pr`._
```

Strip any section that doesn't apply (e.g. no open questions) rather than leaving it empty. The trailing footer is load-bearing: it tells the next agent that this issue was produced from an accepted plan, so the implementation sketch is authoritative — not just a suggestion.

## Step 8: Create the issue

Use the `forgejo` MCP to create the issue. The tool is likely `create_issue` and takes roughly `owner`, `repo`, `title`, `body`, `labels`. If the exact name differs, pick the closest equivalent from the MCP's tool list.

Do **not** assign the issue to a user automatically. If the user wants it assigned to them, they'll say so; otherwise leave it unassigned so it's visible as open work.

Do **not** set a milestone unless the user named one explicitly.

## Step 9: Report back

End with a short summary:

- issue number and URL (from the create response; if absent, construct as `https://<host>/<owner>/<repo>/issues/<index>`)
- labels applied (or a note if none matched — see Step 6)
- a one-line pointer that the user can run `forgejo-issue-to-pr` against this issue number when they're ready to implement

Keep it tight. The issue URL is the point.

## Edge cases worth remembering

- **User gave a one-liner and resists planning** ("just file it"): offer to file a lightweight issue with only Problem + Proposed behavior, and skip plan mode. Name the tradeoff — a thinner issue is harder to action later.
- **Duplicate of an existing issue**: before filing, optionally list open issues (MCP `list_issues`) and scan titles for obvious duplicates. If you spot one, surface it and ask whether to add a comment there instead of filing new.
- **Repo has an issue template**: if `.gitea/ISSUE_TEMPLATE/` or `.forgejo/ISSUE_TEMPLATE/` exists, read it. If its structure materially conflicts with the body template above, adapt — the project's template wins.
- **Plan reveals the feature is already implemented**: stop and tell the user. Don't file an issue for work that's done.
- **Plan grows too large**: suggest splitting into multiple issues with a brief map of how they relate. File them as a set only after the user agrees to the split.
- **Fork remote**: if `git remote -v` shows an `upstream`, the issue probably belongs on upstream, not the user's fork. Use upstream's owner/repo for the MCP call.
- **No MCP labels tool**: fall back to filing without labels and call it out in the summary — don't block on tooling gaps.
