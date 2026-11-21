---
title: Adapt the skills to your setup
description: Change the reviewer, gates, models, forge and knowledge catalog the skills assume, so they run without my bot, my machine or my catalog.
sidebar:
  order: 12
---

The skills are written for my setup, so they name my review bot, my gates and my
catalog. This guide takes you through making them yours. It is
ordered by what you will hit first. You can stop after any section, and the sections
don't depend on each other except where they say so.

You need the plugin you plan to use installed
([install commands](/pg-skills/reference/plugins/github-workflows/)), and a fork or
copy of it if you want to edit the skill and agent files. The
[dependencies page](/pg-skills/reference/dependencies/) lists what each skill needs. The
ones this guide touches are
[a review bot or a human reviewer](/pg-skills/reference/dependencies/#review-bot),
[just](/pg-skills/reference/dependencies/#just),
[jq](/pg-skills/reference/dependencies/#jq),
[claims-audit](/pg-skills/reference/dependencies/#claims-audit),
[claims-mcp](/pg-skills/reference/dependencies/#claims-mcp),
[forgejo-mcp](/pg-skills/reference/dependencies/#forgejo-mcp) and
[Telekin](/pg-skills/reference/dependencies/#telekin).

## Choose your reviewer

Brooke is my review bot, and she isn't a public product, so you can't install her. Use
any review bot, or review the PRs yourself. The
[review bot page](/pg-skills/explanation/review-bot/) lists what a reviewer should
check.

Which skills need a reviewer:

- `github-address-pr-review` needs one, because it answers the review's comments.
- `github-epic-to-merged-prs` and `github-issue-burndown` need one. Both wait for a
  review on each PR before they merge.
- `github-epic-close-out` treats one as optional. Its review gate checks that every PR
  was reviewed.

Three things in the skills are specific to Brooke.

1. **Her login.** The epic skill finds the reviewer from the project's notes, or from
   `gh api .../pulls/<recent>/reviews --jq '.[].user.login'` on a recently merged PR.
   If no reviewer shows up, it asks whether to merge without a review. A bot's login
   ends in `[bot]` in the REST API, so match it with `startswith(...)`. Check the login
   on one real review first.
2. **The re-trigger command.** Brooke's is `/prrb`. The epic skill says to use the
   bot's re-trigger command if it has one when no review arrives. The burndown script
   `wait-brooke.sh` posts `/prrb` itself. Put your bot's command there.
3. **The burndown scripts.** In `github-issue-burndown/scripts/`, four of the five
   scripts are written for Brooke: `wait-brooke.sh`, `brooke-ok.sh`,
   `brooke-security.sh` and `merge-if-ready.sh`. `next-issue.sh` isn't. Edit them like
   this:
   - In `wait-brooke.sh`, `brooke-ok.sh` and `brooke-security.sh`, set the `bot=`
     line to your reviewer's login.
   - In `merge-if-ready.sh`, replace the `brooke-reviews` login in the GraphQL result
     filter, which finds review threads that have no reply. This script has no `bot=`
     line. It calls `brooke-ok.sh`, so it follows that script's changes.
   - Change what counts as "OK". `brooke-ok.sh` reads the review body for a
     `Quality score:` line and for text such as "requests changes", and counts inline
     comments on the head. It doesn't read the review's state. A reviewer with a
     different format needs a different check.
   - Change the security trigger, or do it by hand. `brooke-security.sh` looks for a
     score under 80 and a `**Blocking:**` item in a `### Security` section. If your
     reviewer has no such section, decide the security trigger yourself. It is one of the
     three in [the model policy](/pg-skills/explanation/model-policy/).
   - Change the wording in the skill text as well. `forgejo-address-pr-review` names
     `brooke-reviews[bot]` in a rule that her comments must not be filtered out of the
     walk, and the burndown skill's description names her.

If you have no bot, you can run without the scripts. The glossary's line is to review
the PRs yourself where the skills wait for Brooke. In the epic skill, the review
watcher in step 4 waits for a review whose login starts with the reviewer name you give
it, so give it your own login and post your review on the PR. `github-issue-burndown` is harder to run that way, since its
scripts decide when a PR may merge. Use `github-epic-to-merged-prs`, or run
`github-issue-to-pr` and `github-address-pr-review` on single issues, as in the
[tutorial](/pg-skills/tutorials/first-issue-to-merged-pr/).

## Replace the gates

My repositories are mostly Rust with a `justfile`. The gates the skills name are
`just fmt`, `cargo clippy --all-targets -- -D warnings` and `just test`. Some of my
repositories add `just lint` or `just test-cached`. Swap in yours.

How each skill treats a gate it can't run:

- **`github-issue-to-pr` and `forgejo-issue-to-pr`** skip `cargo clippy` when there is
  no `Cargo.toml`. If there is no `justfile`, or it has no `fmt` or `test` recipe, they
  stop and tell you. They don't substitute other commands. The simplest fix is a
  `justfile` with `fmt` and `test` recipes that call your project's commands.
- **`github-address-pr-review`** degrades. It skips the tools that are missing and says
  so in its final report. It doesn't substitute different commands either.
- **The coordinators** take the gates from your project. They find its lint and test
  commands in its justfile, Makefile or CLAUDE.md, and put them in each agent's brief.
  The agent must have them green before it pushes.
- **The `issue-implementer` agent** has its gates in its standing rules: usually
  `just fmt`, `just lint`, `just test-cached` or `just test`, plus any the brief adds.
  The brief can override a standing rule.

Two things in the agent file are specific to my repository named autobots: the shared
gates lock command, and the rule not to run the kind smoke test locally. Edit or delete
them. If you have a lock of your own, give the lock command instead. The rules are in
[Working on a shared machine](/pg-skills/explanation/shared-machine/).

## Choose your models

Implementers run on the model in the agent's frontmatter. It is `model: sonnet` in
`plugins/github-workflows/agents/issue-implementer.md`. Change that line to change the
default. The coordinators leave `model` off the call, so they get the agent's value.
They pass `model: "opus"` only to escalate a PR.

The auditor has an override. `github-issue-to-pr` asks for the claims auditor to run
on a different model from yours. The agent file overrides that: the auditor runs on
Sonnet, the same model as the implementer, and never on Opus. I did that to save
tokens. If you change the agent's model, change that bullet too, since its reason
("the same model as you") would no longer hold. The auditor is a fresh subagent either
way.

The escalation triggers are text in `github-epic-to-merged-prs` and
`github-issue-burndown`, so edit them there if your limits differ.
[The model policy](/pg-skills/explanation/model-policy/) gives my reasons.
`token-usage-review` shows what a policy costs you. The glossary entry is
[Sonnet-first, Opus to escalate](/pg-skills/reference/glossary/#sonnet-first-opus-to-escalate).

## Move to Forgejo

The `forgejo-workflows` plugin has five skills: `forgejo-plan-to-issue`,
`forgejo-groom-issue`, `forgejo-issue-to-subissues`, `forgejo-issue-to-pr` and
`forgejo-address-pr-review`. They talk to Forgejo through
[forgejo-mcp](/pg-skills/reference/dependencies/#forgejo-mcp), so install and configure
it for your Forgejo host and token first. The plugin also needs
[git](/pg-skills/reference/dependencies/#git).

Differences from the GitHub skills:

- **There are no coordinators.** The plugin has no epic, burndown, milestone or
  close-out skill. The epic and burndown skills use `gh`, so they are GitHub only.
- **The implementer comes from `github-workflows`.** `forgejo-issue-to-pr` fans out to
  the `github-workflows:issue-implementer` agent, so install that plugin too to get
  the agent.
- **`forgejo-address-pr-review` is interactive.** `github-address-pr-review` decides
  each comment itself. The Forgejo skill shows each comment with a suggested
  resolution and asks you to pick `a` (accept), `e` (explain), `s` (skip), `x`
  (expand) or `q` (quit). Your choice is the approval, and it carries the choice out.
  It also reads both the timeline comments and the inline review comments, and on a
  fork PR it offers only explain and skip.
- **It needs `forgejo-mcp`, not `gh`.** The skills read and file issues and PRs
  through the `forgejo` MCP tools, and parse the host, owner and repo from your
  git remote.
- **`forgejo-address-pr-review` names Brooke.** It has a rule never to filter
  `brooke-reviews[bot]` out of the walk. Change the name to your bot, or drop the rule.

`forgejo-issue-to-pr` also needs [just](/pg-skills/reference/dependencies/#just) and
[claims-audit](/pg-skills/reference/dependencies/#claims-audit), and can use
[claims-mcp](/pg-skills/reference/dependencies/#claims-mcp). `forgejo-address-pr-review`
needs a [review bot](/pg-skills/reference/dependencies/#review-bot) and can use just.

## Decide what to do about the knowledge catalog

You don't need one. Four skills in `github-workflows` point at my catalog, and each
lists [Telekin](/pg-skills/reference/dependencies/#telekin) as optional:
`github-milestone-plan-to-issues`, `github-epic-to-merged-prs`,
`github-issue-burndown` and `github-epic-close-out`.

1. Skip the background reading. The skills tell the session to read concepts in my
   catalog, and you can't read it.
2. Decide where lessons go. The skills record merge authorization, a dated line per run,
   flakes and root causes in the catalog. Put them in your project's notes, a
   `CLAUDE.md`, or your own catalog.
3. If you want your own, Telekin is built on
   [okf_mcp](https://github.com/hypotheosis/okf_mcp), which you can host yourself. Point
   the skills' catalog references at it.

[The knowledge catalog](/pg-skills/explanation/knowledge-catalog/) explains why I keep
one.

## Go through the glossary's Adapt lines

The [glossary](/pg-skills/reference/glossary/) ends each entry with **Adapt:**. Here is
each one, and where this guide covers it.

| Entry | Adapt | Covered in |
|---|---|---|
| [Brooke](/pg-skills/reference/glossary/#brooke-brooke-reviewsbot) | Put your reviewer's login in the scripts' `bot=` line and your bot's re-trigger command in place of `/prrb`. With no bot, review the PRs yourself. | [Choose your reviewer](#choose-your-reviewer) |
| [`issue-implementer`](/pg-skills/reference/glossary/#issue-implementer) | Read its standing rules (gates, shared-machine etiquette, what it may never do) and change those that don't match how you work. | [Replace the gates](#replace-the-gates) and [Choose your models](#choose-your-models) |
| [Sonnet-first, Opus to escalate](/pg-skills/reference/glossary/#sonnet-first-opus-to-escalate) | Change the `model` the skills pass if your limits or budget differ. | [Choose your models](#choose-your-models) |
| [The knowledge catalog](/pg-skills/reference/glossary/#the-knowledge-catalog-telekin-okf) | Skip those pointers, or point them at your own docs. | [Decide what to do about the knowledge catalog](#decide-what-to-do-about-the-knowledge-catalog) |
| [claims-mcp and `claims-audit`](/pg-skills/reference/glossary/#claims-mcp-and-claims-audit) | Install `claims-audit` (and claims-mcp if you want a ledger), or drop that step and review the PR against the issue yourself. | [Audit](#audit) below |
| [forgejo-mcp](/pg-skills/reference/glossary/#forgejo-mcp) | Configure it for your Forgejo host and token. | [Move to Forgejo](#move-to-forgejo) |
| [Gates](/pg-skills/reference/glossary/#gates-just-fmt-cargo-clippy-just-test) | Swap in your project's format, lint and test commands. | [Replace the gates](#replace-the-gates) |
| [Cargo `build-dir`](/pg-skills/reference/glossary/#cargo-build-dir-and-cargo-clean-before-removing-a-worktree) | Harmless if you build into `target/`; keep it if you also use `build-dir`. | [Working on a shared machine](/pg-skills/explanation/shared-machine/) |
| [okf_mcp and autobots](/pg-skills/reference/glossary/#okf_mcp-and-autobots) | Ignore them, or add the equivalent quirks of your repos. | [Replace the gates](#replace-the-gates) |
| [The `accepted` label](/pg-skills/reference/glossary/#the-accepted-label) | Pass your own label. | [Burn down the backlog](/pg-skills/how-to/burn-down-the-backlog/) |

### Audit

`github-issue-to-pr` runs the claims audit in Step 7a. Install
[claims-audit](/pg-skills/reference/dependencies/#claims-audit) and the step works in
table-only mode: no `claims.json` is tracked, the auditor makes no claims-mcp calls, and
its results go into the PR body. Install
[claims-mcp](/pg-skills/reference/dependencies/#claims-mcp) as well if you want a
committed ledger. If you drop the step, review the PR against the issue yourself.
[Validate a change](/pg-skills/how-to/validate-a-change/) has the steps.

## Check your work

Run one issue through `github-issue-to-pr` on a small repository, with your reviewer
and gates in place, before you let a coordinator fan out many. If something still names
Brooke or one of my repositories, the glossary tells you what it is.
