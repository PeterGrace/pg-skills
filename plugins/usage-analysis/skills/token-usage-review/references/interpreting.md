# Reading the usage report

Each pattern names what the report shows, how to confirm it, and the usual fix. The
thresholds are rough guides, not rules.

## Huge coordinator contexts

- **Shows:** cache reads are over half the cost. Top sessions have coordinator
  context p50 above about 200k and hundreds of turns. They are usually
  orchestrators such as `github-workflows:github-epic-to-merged-prs` or
  `github-workflows:github-issue-burndown`.
- **Why it costs:** every turn re-reads the whole context. A 450k context costs
  roughly 4× a 100k one per turn, and auto-compact doesn't fire until the context
  nears the model's window, which may be 1M.
- **Fix:**
  - Keep the run's state in a file and compact at checkpoints. The
    `github-workflows` coordinators do this; they print a ready-to-paste
    `/compact` line.
  - Lower the auto-compact threshold with the `autoCompactWindow` setting or the
    `CLAUDE_CODE_AUTO_COMPACT_WINDOW` env var, for example 300000. Each compaction
    is itself a full-context call, so don't go much below about 200k.
  - Start a fresh session between planning and execution.

## Opus by default

- **Shows:** the "subagents by type and model" table has a large Opus row for an
  agent type meant to run on Sonnet. The session report shows many
  `model=opus` overrides, and many of them have no stated reason.
- **Confirm:** compare the median turns and peak context of the Opus and Sonnet
  groups of the same agent type. Opus groups often run longer as well as costing
  more per token.
- **Fix:** start every subagent on Sonnet, and let Opus take over only on a
  recorded, measurable trigger: a reviewer security block, repeated failed review
  rounds, repeated failed CI fixes. Broad exceptions ("touches security", "looks
  subtle") turn into the default.

## Untyped subagents inheriting the parent's model

- **Shows:** `general-purpose`, `fork` or `?` rows on Opus.
- **Why:** an Agent call with no `subagent_type`, or with a type that has no
  `model`, runs on the parent's model.
- **Fix:** use a typed agent whose definition sets `model: sonnet`, or pass `model`
  on the call. Keep Opus for planning and the main thread.

## Polling loops

- **Shows:** the coordinator's tool list is dominated by `Bash` (often over half
  its turns), alongside large context.
- **Why:** each check on a review, CI run or agent is a full-context turn that
  does almost nothing.
- **Fix:**
  - Run one background watcher per wait, which prints a single line when it's done.
  - Let the harness notify on agent completion instead of checking on agents.
  - Read only the fields needed (`--jq`, `tail`).

## Cache-write churn

- **Shows:** cache writes above about 30% of cost.
- **Why:** the cache keeps being rebuilt:
  - sessions resumed after the cache TTL;
  - switching models mid-session;
  - many short sessions over the same large prompt;
  - a subagent fan-out where every agent writes its own large context.
- **Fix:** batch related work into one session, avoid model switches, and keep
  subagent briefs and the definitions they load small.

## Output-heavy

- **Shows:** output above about 25% of cost.
- **Why:** long generated files, verbose reports, or high reasoning effort on
  routine work.
- **Fix:** ask subagents for short reports (the parent reads only the report), and
  lower the effort level for mechanical tasks.

## A single spike

- **Shows:** one day or one session far above the rest.
- **Fix:** drill into that session and name what it was doing (its prompt and
  skills). A one-off large job may be fine. Say so rather than inventing a fix.
