# Glossary

These skills are written for my own setup, so they name my bots, servers, projects and
habits. This page says what each of those is, so you can map it onto your own setup
before you install a plugin. Each entry ends with **Adapt:**, saying what to change.

## People and bots

### Brooke (`brooke-reviews[bot]`)

My pull-request review bot: the GitHub App of *prrb*, my self-hosted LLM PR
reviewer, named after my cat. She reviews every PR, posts a scored verdict, inline
comments and a security section, and acknowledges a request with an 👀 reaction.
Posting `/prrb` on a PR asks her to review it again. The `github-issue-burndown`
scripts read her reviews (`brooke-ok.sh`, `wait-brooke.sh`, `brooke-security.sh`).
**Adapt:** put your reviewer's login in the scripts' `bot=` line and your bot's
re-trigger command in place of `/prrb`. If no bot reviews your PRs, review them
yourself where the skills wait for Brooke.

### pgrace

Me. Dated notes such as "(pgrace, 2026-11-15)" record a decision I made and when.

## Agents and models

### `issue-implementer`

A Claude Code subagent, shipped in the `github-workflows` plugin, that implements
one issue end to end in a git worktree (via `github-issue-to-pr` or
`forgejo-issue-to-pr`), then answers the review. The coordinator skills
(`github-epic-to-merged-prs`, `github-issue-burndown`, the `*-issue-to-pr` skills
when they fan out) always start their implementers as this agent.
**Adapt:** read its standing rules (gates, shared-machine etiquette, what it may
never do) and change those that don't match how you work.

### Sonnet-first, Opus to escalate

My model policy for subagents. Implementers and auditors run on Sonnet. A PR moves
to Opus only when a skill's escalation triggers fire, such as a security finding or
repeated failed review rounds. I set this to keep within my usage limits.
**Adapt:** change the `model` the skills pass if your limits or budget differ.

## Servers and tools

### The knowledge catalog (Telekin, OKF)

My private catalog of notes about my systems, projects and processes, in Open
Knowledge Format and served over MCP by Telekin
([okf_mcp](https://github.com/hypotheosis/okf_mcp)). Skills point to concepts in it,
such as `/processes/subagent-pr-workflow.md`, as background reading. You can't read
it. **Adapt:** skip those pointers, or point them at your own docs.

### claims-mcp and `claims-audit`

My MCP server and skill for auditing a change's claims: a ledger (`claims.json`)
of claims, evidence and supported/refuted verdicts. The `*-issue-to-pr` skills run
`claims-audit` on a fresh subagent before opening a PR. **Adapt:** install
claims-mcp, or drop that step and review the PR against the issue yourself.

### superpowers

The [superpowers](https://github.com/obra/superpowers) Claude Code plugin. Skills
that name `superpowers:<skill>` (for example `superpowers:writing-plans`) need it
installed.

### forgejo-mcp

[raohwork/forgejo-mcp](https://github.com/raohwork/forgejo-mcp), the MCP server
the `forgejo-*` skills use to talk to a Forgejo instance. **Adapt:** configure it for
your Forgejo host and token.

## Conventions

### Gates: `just fmt`, `cargo clippy`, `just test`

Most of my repos are Rust with a `justfile`, and these are the checks that must be
green before a push (some repos add `just lint` or `just test-cached`).
**Adapt:** swap in your project's format, lint and test commands.

### Cargo `build-dir` and `cargo clean` before removing a worktree

My `~/.cargo/config.toml` sets `build-dir` so each checkout builds under
`~/.cache/cargo-build/`. `git worktree remove` doesn't delete that directory, and an
agent worktree's build can reach 30-60 GiB, so the skills run `cargo clean` in a
worktree before removing it. **Adapt:** harmless if you build into `target/`; keep
it if you also use `build-dir`.

### okf_mcp and autobots

Two of my repositories that the skills use as examples: okf_mcp (the catalog
server, with its `tools/agentic/remove-worktree.sh` script) and autobots (which has a
shared gates lock and a long kind smoke test that agents must not run locally).
**Adapt:** ignore them, or add the equivalent quirks of your repos.

### The `accepted` label

Marks an issue I've triaged and want implemented. `github-issue-burndown` works
through the open `accepted` issues, highest priority first. **Adapt:** pass your own
label.

### Milestone integration branches (`milestone/<epic>-<slug>`)

`github-epic-to-merged-prs` merges each sub-issue's PR into one integration branch
for the epic, then merges that branch into `main` once at the end.
