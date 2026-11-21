---
title: "The model policy: Sonnet first, and when work escalates to Opus"
description: Why implementers start on Sonnet, the three recorded triggers that move a PR to Opus, and why the auditor runs on Sonnet too.
sidebar:
  order: 6
---

Every pull request starts with a Sonnet implementer. Opus takes over a pull request only when a
recorded trigger fires. This page gives the rule, my reasons, and the numbers the
skills record. For how to change the policy in your own setup, see
[Adapt the skills to your setup](/pg-skills/how-to/adapt-the-skills/#choose-your-models).

## The rule

The [`issue-implementer`](/pg-skills/reference/agents/issue-implementer/) agent has
`model: sonnet` in its definition. The coordinator skills,
[`github-epic-to-merged-prs`](/pg-skills/reference/skills/github-epic-to-merged-prs/)
and [`github-issue-burndown`](/pg-skills/reference/skills/github-issue-burndown/), tell
the session to start implementers that way. The epic skill says "Always start on
Sonnet: leave `model` off the call." Opus is for taking over a PR, never a first attempt, "however subtle the
sub-issue looks."

Opus takes over a PR from its Sonnet implementer only on one of three triggers:

- **Security.** The reviewer marks a security problem as blocking and sinks the score.
  For Brooke, the `brooke-security.sh` script prints `ESCALATE` when the score is
  under 80 and her Security section has a `**Blocking:**` item.
- **Review rounds.** Two Sonnet address rounds are done, and the review of the new head
  still has blocking or inline comments.
- **CI.** The agent has failed twice to get CI or the gates green on its own changes,
  not on a known flake.

An agent that reports a sub-issue as ambiguous, or as conflicting with the plan, is
not a trigger. A different model won't settle that, so it goes to me.

To escalate, the coordinator stops the Sonnet agent's loops and starts a new
`issue-implementer` with `model: "opus"` on the same worktree, branch and PR. It builds
on the existing work and answers every later round. The coordinator records
`model: opus (<trigger>: <evidence>)` in its state file and its report. The skill says
"A model change without a recorded trigger is a mistake." If Opus has done two
address rounds and the review still blocks, the coordinator stops on that PR and
reports it to me. In the burndown skill that state is called Stuck.

Planning, design and coordination stay on the model of the session I'm in. The agent's
own description says it is "Not for planning, design or research, which stay on the
parent's model."

## Why I set it up this way

I have two reasons.

**The usage limit.** Opus implementers were most of my weekly spend. I set the policy
to keep within my usage limits.

**Judgment at the top.** Planning, design and coordination are where the stronger
model pays off. The coordinator skill adds a point about implementers: "The plan and
the gates carry most of the judgment."

I'm not claiming more than that. I don't say Sonnet is always enough, and I don't say
escalation is rare. Those aren't my reasons.

## The numbers the skills record

Both coordinator skills record the same measurement. In the week to 2026-11-21, 58 of
117 implementers ran on Opus, at about 4× the cost of a Sonnet implementer, and most
had no stated reason. The burndown skill states the three triggers right after this
figure, and requires a written reason for a model change.

The coordinator's own context is a second cost. In the same week, coordinator sessions
ran at a median of 430k context tokens, peaked near 900k and took 400-900 turns per
epic, and the coordinator alone was 20-50% of a run's tokens. A burndown session that
ran 2.5 days had a median of 290k and a peak of 610k. The coordinator skills have a
section on keeping context small for this reason.

## The auditor runs on Sonnet too

`github-issue-to-pr` asks for the claims auditor to be a fresh subagent on a different
model from the implementer. The agent definition overrides that. It tells the
implementer to dispatch the auditor on Sonnet, "the same model as you, even though the
skill asks for a different model: an Opus auditor costs too many tokens (pgrace,
2026-11-15)." The auditor is "still a fresh subagent that gets none of your
reasoning," and the agent is told never to run it on Opus.

On the auditor's model, the agent definition overrides the skill. It overrides
it on other points too, such as the gates; see the
[agent reference](/pg-skills/reference/agents/issue-implementer/). The
[glossary](/pg-skills/reference/glossary/#sonnet-first-opus-to-escalate) has the
policy's one-paragraph version. For why the audit exists at all, see
[Why I audit claims](/pg-skills/explanation/why-audit-claims/).

## An observation, not a reason

Epic [#3](https://github.com/PeterGrace/pg-skills/issues/3), this site's first
milestone, escalated zero times. Every commit on its ten PRs
([#13](https://github.com/PeterGrace/pg-skills/pull/13),
[#14](https://github.com/PeterGrace/pg-skills/pull/14),
[#15](https://github.com/PeterGrace/pg-skills/pull/15),
[#16](https://github.com/PeterGrace/pg-skills/pull/16),
[#18](https://github.com/PeterGrace/pg-skills/pull/18),
[#21](https://github.com/PeterGrace/pg-skills/pull/21),
[#22](https://github.com/PeterGrace/pg-skills/pull/22),
[#23](https://github.com/PeterGrace/pg-skills/pull/23),
[#24](https://github.com/PeterGrace/pg-skills/pull/24) and
[#27](https://github.com/PeterGrace/pg-skills/pull/27)) carries a
`Co-Authored-By: Claude Sonnet` trailer, except two merges that caught a branch up, and none
carries an Opus one. I record that as what happened on one epic. It isn't
why I chose the policy, and one epic is too few to say how often a trigger fires.

## Checking the policy

The [`token-usage-review`](/pg-skills/reference/skills/token-usage-review/) skill, in
the [`usage-analysis`](/pg-skills/reference/plugins/usage-analysis/) plugin, reads the
local Claude Code transcripts and reports where the tokens went: by model, token type,
session and subagent type, plus Opus overrides with no stated reason. The "58 of 117"
figure above is the kind of finding it produces. It suggests re-running the review
about a week after a change and comparing the Opus share of subagents, the coordinator's
median context and the unexplained Opus overrides. It needs
[Python 3](/pg-skills/reference/dependencies/#python) and reads only the sessions on
the machine it runs on.

## What the skills need

What each skill needs is on the [dependencies page](/pg-skills/reference/dependencies/).
