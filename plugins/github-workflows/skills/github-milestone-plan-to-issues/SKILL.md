---
name: github-milestone-plan-to-issues
description: "Use when a project's design document lays out milestones or phases and the user wants the next one turned into an implementation plan plus a GitHub epic with one sub-issue per task, ready for subagents to execute. Triggers on \"plan milestone N\", \"write the plan for the next milestone\", \"write the milestone plan and file the epic and sub-issues\", \"take DESIGN.md section X and turn it into issues\", or \"set up the next milestone the way we did the last one\"."
---

# Milestone design → plan PR → epic → sub-issues

This is the planning half of the subagent workflow. You take the next
milestone from the design doc and produce:
1. a checked-in implementation plan, merged after review;
2. one epic issue;
3. one sub-issue per plan task, ordered by dependency.

Executing those sub-issues is the next skill, `github-epic-to-merged-prs`. The
reasoning behind both is in the catalog concept `/processes/subagent-pr-workflow.md`
in catalog `peter-grace` on the Telekin server. Read it, and the project's own concept,
first.

**REQUIRED SUB-SKILLS:**
- `superpowers:writing-plans`, for the plan;
- `github-issue-to-subissues`, for the sub-issues, which needs the user's
  acceptance in plan mode.

**The plan is the single source of truth.** The epic and the sub-issues give
scope and acceptance only, never code. When the implementation diverges, the
plan is corrected, in the same PR, with a dated note.

## 1. Gather the inputs

- **The milestone's section of the design doc**, for example `docs/DESIGN.md`
  section 17, milestone N. Also read every design section it references.
- **The previous milestone's plan and its milestone changelog,** for the
  conventions to copy and the deferrals to pick up.
- **Open follow-up issues** from earlier milestones:
  `gh issue list --label <prev-milestone>` and the previous epic's close-out
  comment. Decide which ones belong in this milestone.
- **The code as it is on `origin/main`,** not as the design imagines it. Work
  in a fresh worktree off `origin/main`.

## 2. Check the facts the plan depends on

Before you write any task, confirm each external API the plan will use
against its real source. Look in `~/.cargo/registry/src/*/<crate>-<ver>/`, the
vendored code or the docs, and check signatures, defaults and behaviour.
Record each one in a **"Verified facts the code relies on"** section with a
file:line citation. Unverified assumptions about libraries are the most
common reason a plan's code doesn't compile.

## 3. Ask the user only the real design questions

Use AskUserQuestion, four questions at most per call, each with a
recommended option. Ask only about choices the design leaves open and the
user has to make, for example:
- a new crate versus a module;
- how real an external dependency the tests need;
- streaming or not;
- which follow-ups to include.

Record every answer in the plan's **"Decisions taken while planning
(<date>)"** section. Where the plan departs from the design on purpose, list
it under **"Simplifications and deviations relative to the design"** and fix
the design doc in the task that implements it.

## 4. Write the plan

Follow `superpowers:writing-plans`. Save it as
`docs/superpowers/plans/<YYYY-MM-DD>-milestone-<N>-<slug>.md`, or wherever the
previous milestone's plan lives. It has these sections:

1. **Goal, Architecture and Tech Stack** (the writing-plans header).
2. **Scope:** what's in, and a table of what's deliberately deferred with
   where each item goes.
3. **Decisions** and **Deviations** (step 3).
4. **Verified facts** (step 2).
5. **Conventions for every task.** Include:
   - the project's gates;
   - test-style and lint rules;
   - one changelog entry per task, `changelog/<UTC ts>-m<N>-task-<NN>-<slug>.md`;
   - this rule, verbatim: "The code in this plan has not been compiled. If an
     implementation has to differ, fix this plan in the same PR (inline, or
     with a dated `> **Corrected (issue #N).**` note), then grep later tasks
     for the changed symbol."
6. **File map:** every file created or modified, and which task touches it.
   The executor uses it to tell which tasks can run in parallel.
7. **Task dependencies:** an explicit `A -> B` graph. Tasks with no
   dependencies can start straight away. The last task is a smoke test, the
   README and the milestone changelog, and it depends on all the others.
8. **Tasks.** Each one is a PR-sized unit with Files, failing test first,
   implementation, gates and commit, following writing-plans.

   Each carried-over follow-up is its own task, named with its issue number,
   for example "Task 8: ... (#127)". When a follow-up's root cause is
   unconfirmed, make its task "investigate first, then fix if confirmed;
   stop and report if refuted".

Before opening the PR, run writing-plans' self-review: does the plan cover
every item in the design section, are there any placeholders, and are names
and types consistent across tasks?

## 5. Open the plan PR and get it reviewed

1. Branch `docs-milestone-<N>-plan`, commit
   `docs: milestone <N> (<name>) implementation plan`, and push.
2. Open the PR with `gh pr create`.
3. Wait for the reviewer with a background poll that matches the bot's real
   login, including the `[bot]` suffix. If it skips the PR, read its comments:
   a branch behind `main` is the usual cause.
4. Address the review yourself with `github-address-pr-review`.
5. Merge only if the user has authorized merging plan PRs; otherwise report
   it ready to merge. **Don't file issues until the plan is on `main`**,
   because the issues link to it there.

## 6. File the epic

`gh issue create` with labels `epic` and `milestone-<N>` (create any that are
missing). The body is in prose with no code, and has these sections:
- **Goal:** two or three sentences. Say which milestone of how many, link the
  design section, and say "the plan `<path>` (PR #X) is the source of truth".
- **In scope:** grouped bullets, and the carried-over issues with their
  numbers.
- **Decisions (taken while planning, <date>):** copied from the plan.
- **Deliberately deferred:** a short list that points to the plan's table.
- **Working these in parallel:**
  - one PR per sub-issue;
  - which tasks can start straight away;
  - expected merge conflicts in shared files ("keep both sides");
  - the gates;
  - fix divergences in the plan;
  - the dependency graph as a code block.

## 7. File the sub-issues

Run `github-issue-to-subissues <epic>`. Use **one sub-issue per plan task**,
which overrides that skill's target of 2 to 6. Titles are
`M<N>.<NN>: <task title>`. Each body has:
- "Part of #<epic>" and "Implements **Task k** of `<plan>`";
- a one-paragraph scope;
- the files, taken from the plan's Files list;
- its blockers, taken from the Task dependencies graph;
- its validation: the task's named tests plus the gates.

The skill nests the sub-issues under the epic, sets the blocked-by edges and
posts the index comment. Then read the edges back to check them.

## 8. Hand off

Report:
- the plan path and PR;
- the epic URL;
- the sub-issue numbers in order, with the dependency graph;
- which tasks can start now.

If the user asks to continue, invoke `github-epic-to-merged-prs`.

## Common mistakes

| Mistake | Fix |
|---|---|
| Writing tasks against an imagined library API | Verify the API in the registry source first, and cite the file and line. |
| Copying code into issues | Issues link to the plan's Task. Detail copied into an issue goes stale when the plan is corrected. |
| Filing issues before the plan PR merges | The issues link to the plan on `main`, so wait. |
| Asking the user what the design already decides | Ask only about choices the design leaves open, and give a recommended option. |
| Folding earlier follow-ups into unrelated tasks | Give each one its own task, named with its issue number, so its PR closes it. |
| Only a linear task chain | Draw the real graph, so independent tasks can run in parallel. |
| A missing file map | The executor needs it to see which tasks would conflict. |
