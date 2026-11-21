---
title: Validate a change with claims-mcp and claims-audit
description: Install claims-audit, let github-issue-to-pr audit a change's claims before its PR opens, choose ledger or table-only mode, read the verdicts, and fix what the audit refutes.
sidebar:
  order: 9
---

This guide gets a claims audit onto the changes your agent makes. The audit is Step 7a
of [github-issue-to-pr](/pg-skills/reference/skills/github-issue-to-pr/), and the
`forgejo-issue-to-pr` skill has the matching step. For why it exists, read
[Why audit claims](/pg-skills/explanation/why-audit-claims/).

## Install

1. Install the [claims-audit](/pg-skills/reference/dependencies/#claims-audit) skill.
   `github-issue-to-pr` needs it. Copy the skill's folder, `skills/claims-audit` in a
   checkout of [claims-mcp](https://github.com/hypotheosis/claims-mcp), into your Claude
   Code skills directory. claims-mcp's
   [install guide](https://hypotheosis.github.io/claims-mcp/guides/install.html#3-install-the-skill)
   has the exact commands for your platform, and for installing it into a project
   instead of for yourself.
   Restart Claude Code afterwards.
2. Optional: install [claims-mcp](/pg-skills/reference/dependencies/#claims-mcp). You
   need it only for ledger mode, and for audits outside a PR (see
   [Audit an artifact outside a PR](/pg-skills/how-to/audit-an-artifact/)). Take the
   install steps from claims-mcp's
   [install guide](https://hypotheosis.github.io/claims-mcp/guides/install.html). In
   short: put a release binary on your `PATH` (or `cargo install --locked --git
   https://github.com/hypotheosis/claims-mcp`), then register it from your project's
   root:

   ```bash
   claude mcp add --scope project claims -- claims-mcp --catalog claims.json
   ```

## What Step 7a does for you

When you run `github-issue-to-pr`, after the gates and the commit, the skill:

1. Picks a mode (below).
2. Drafts the PR body into a scratch file. Its statements of fact are claims the audit
   checks.
3. Dispatches a fresh subagent. The skill asks for a different model from the one that
   wrote the change; the `issue-implementer` agent overrides this and uses Sonnet, usually
   its own model. The auditor gets the issue, the draft body, the repository path and the commit range.
   It doesn't get the implementer's plan or summary.
4. Acts on the verdicts, as described in [Read the verdicts](#read-the-verdicts).
5. In ledger mode, commits `claims.json` in a commit of its own.
6. Puts a `## Claims` table in the PR body.

You don't run any of this yourself. If you're the top-level session, the skill hands the
work to an `issue-implementer` subagent, and that agent dispatches the auditor.

## Choose a mode

The skill picks the mode by checking whether `claims.json` is tracked:

```bash
git ls-files --error-unmatch claims.json
```

- **It succeeds: ledger mode.** The auditor records claims, evidence and verdicts in
  the ledger through the claims-mcp tools, and the implementer commits it. Merge the
  PR with a merge commit: the ledger's anchors pin the branch's commits, and a squash
  or rebase leaves them `commit_missing`. The skill checks
  `gh repo view --json mergeCommitAllowed` and says so in the PR body if merge commits
  are off.
- **It fails: table-only mode.** The auditor makes no claims-mcp calls at all, because
  even a read creates a `.claims.json.lock` file. The results go in the PR body without
  claim ids, with a line saying the repository has no ledger. You need only the
  `claims-audit` skill.

Pick ledger mode for a long-lived, spec-driven or correctness-critical project, and
start the ledger early. See
[Why audit claims](/pg-skills/explanation/why-audit-claims/#ledger-mode-or-table-only-mode)
for why. To start one, install and register claims-mcp, run an
[audit](/pg-skills/how-to/audit-an-artifact/), and commit the `claims.json` it writes.
Add `.claims.json.lock` and `.claims.json.tmp` to `.gitignore`.

### Ledger mode in a worktree

The claims server opens `claims.json` relative to the directory the session started in.
If you work in a git worktree, the auditor has to pass the worktree's absolute ledger
path as `catalog` on every claims call, and the skill first probes that your server
honours the argument. A server older than 0.2.5 doesn't. If the probe doesn't return an error naming the probe path, the skill
stops and asks you to upgrade claims-mcp and restart the session or run `/mcp`. 

If `main`'s ledger changed since your branch started, the skill takes main's file and
records the findings again, because two branches can hand out the same ids. It doesn't
merge `claims.json` by hand, and you shouldn't either. claims-mcp's
[guide to branches that both write the ledger](https://hypotheosis.github.io/claims-mcp/guides/parallel-branches.html)
has the details.

## Read the verdicts

Each claim gets one of three verdicts.

| Verdict | What it means | What happens |
|---|---|---|
| supported | The auditor gathered evidence itself and it shows the claim holds. | Listed in the table. |
| refuted | The evidence shows the claim doesn't hold. | See below. |
| not_enough_info | The evidence can't decide it. | Never blocks. The table says what would decide it. |

For a refuted claim, the question is whose it is:

- **Ours:** a claim from the issue or the PR body, or an existing claim this diff broke.
  The implementer fixes it before the PR opens. If the code was wrong, it fixes the
  code and goes back through the gates. If the PR body was wrong, it corrects the draft.
  Then the auditor checks the new commit range, so a fix is confirmed by a second look.
  This repeats until no claim of ours is refuted. If it can't get there, it doesn't push
  and reports to you.
- **Elsewhere:** a problem in code the PR didn't touch. It stays recorded as refuted,
  with its `Fix:` step, and is listed in the PR body as pre-existing. It doesn't block.

The table lists refuted claims first, then not_enough_info, then supported. With more
than about eight supported claims, the supported ones are collapsed into one line with
a short citation each. Here is the skill's example of rows, without the claim ids, as
in table-only mode:

| Claim | Verdict | Evidence |
|---|---|---|
| "parse_config rejects files over 1 MiB" | supported | `cargo test config::too_large` (1 passed) |
| "README lists every subcommand" (pre-existing) | refuted | `seal` missing from README.md:120; Fix: add it |

Real tables are on [PR #34](https://github.com/PeterGrace/pg-skills/pull/34) and
[PR #36](https://github.com/PeterGrace/pg-skills/pull/36), both in table-only mode.

## What to check before you approve the PR

1. The table covers the issue's requirements, not just the body's sentences. A requirement
   with no row wasn't audited.
2. Each supported row cites something you could run or open, such as a command with its
   counts or a `file:line`. Verdicts rest on evidence the auditor gathered itself, and a
   row that only repeats the body doesn't.
3. Every not_enough_info row says what would decide it.
4. In ledger mode, the report's counts match `audit_report`; the skill checks the
   auditor's numbers against it before copying them.
5. Anything marked pre-existing is a problem in code the PR didn't touch. Decide whether to file an issue for it.

A reviewer, human or bot, can then check the body against the diff, as
[a review bot can do](/pg-skills/explanation/review-bot/#what-i-rely-on-her-for).

## Related

- [Audit an artifact outside a PR](/pg-skills/how-to/audit-an-artifact/).
- [Answer review comments](/pg-skills/how-to/answer-review-comments/) is the step after
  the PR opens.
