---
name: token-usage-review
description: "Works out where local Claude Code token usage went over a window (default the last 7 days) from the session transcripts: by model, token type, project, day and session, main session vs subagents by agent type and model, coordinator context sizes, and Opus overrides with no stated reason. Then maps each finding to a fix. Use when the user is near or over a usage or weekly limit, asks where their tokens or spend went, why usage is so high, which sessions or subagents cost the most, or wants a usage review or follow-up check."
---

# Token usage review

Find where Claude Code usage went, and why, from the local transcripts. Then turn each
finding into a fix with its evidence. A coding-agent workflow mostly pays for context
re-reads and model choice, not for the code it writes. This skill attributes cost to
sessions, subagent types and models, so it can show which workflow and which decision
drove it.

The script reads only `~/.claude/projects/` on this machine. It doesn't see claude.ai
chat, other machines or cloud sessions. Say so in the report.

## 1. Run the summary

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/usage_report.py --days 7 summary --top 10
```

- `--days` and `--root` go **before** the subcommand. Use the window the user names,
  for example `--days 30` for "this month".
- The script takes a few seconds and prints compact tables. Never read transcripts
  into context yourself: they run to gigabytes. If you need a field the script
  doesn't print, extract it with a short `python3` or `jq` one-off and print only
  the result.
- Costs are weighted by relative API price: input 1, output 5, cache read 0.1, cache
  write 1.25 or 2; Opus 5×, Sonnet 3×, Haiku 1×. The plan limit's exact accounting
  isn't published, so call shares "approximate".

From the output, note:
- the share of each token type;
- the model split;
- main vs subagent;
- which subagent type and model rows dominate;
- the top sessions, with their first prompt, skills and coordinator context.

## 2. Drill into the top sessions

Take the 3-5 sessions with the largest share, by their 8-character id:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/usage_report.py --days 7 session <id> <id> ...
```

For each one, it prints:
- the coordinator's share against its subagents';
- the coordinator's turn count and context p50/p90/max;
- its most-used tools;
- its Agent calls by type and model override;
- Opus overrides with no stated reason. Only the coordinator's own text just before
  the call counts as a reason, never the brief's boilerplate;
- each subagent group's share, count, median turns and median peak context.

## 3. Diagnose

Match what you see against [references/interpreting.md](references/interpreting.md).
It lists the usual patterns (huge coordinator contexts, Opus by default, untyped
subagents inheriting Opus, polling loops, cache-write churn), each with the check that
confirms it and the fix. Back every finding with numbers from the script, such as
"58 of 117 implementers ran on Opus, at a median of 4× the cost of a Sonnet one". Don't
report a pattern the numbers don't show.

## 4. Report

Keep it short:
1. A table of the main splits: model, token type, main vs subagent, top projects.
2. The top sessions: share, what they were doing (prompt or skill), coordinator
   context.
3. The 2-4 findings that explain most of the spend, each with its evidence and fix,
   largest saving first.
4. What the numbers leave out: the weighting, and that only local sessions are covered.

## 5. Apply fixes only with the user's go-ahead

Propose the changes and let the user choose. Fixes change skills, agent definitions or
settings that other sessions use, so make them only once the user agrees. For skills
in this repository, follow `skill-authoring:authoring-skills`. If the user keeps notes
or a knowledge catalog (see their CLAUDE.md), record the review's findings and changes
there.

## 6. Follow up

Suggest re-running the review about a week after any change. Compare the same
numbers: the Opus share of subagents, coordinator context p50, and the unexplained
Opus overrides. That shows whether the fix held.
