# Site interview

Phase 2 of [the workflow site design](superpowers/specs/2026-11-21-workflow-site-design.md).
Peter Grace answered these questions one at a time. Each question was built from what
the skills already say, so Peter confirms or corrects how he actually works. Phase 3
writes the site's pages from this file, which makes it the source of every page.

Each answer has the question, Peter's answer in his own words where he gave them, and
notes on where it confirms or corrects the skills.

## 1. How I start and choose a workflow

### Where does new work usually start?

**Answer:** "Usually an idea, brainstormed. Sometimes an IDEA.md file that I write
before talking to the agent and insert at the start."

**Notes:** this confirms `superpowers:brainstorming` as the usual entry point: an
idea becomes a spec, then a plan. The skills don't mention IDEA.md. It's a file Peter
writes ahead of time and gives the agent at the start of the conversation.

### What goes in an IDEA.md?

**Answer:** the problem and the goal, plus prior art and links.

**Notes:** constraints and a rough design weren't chosen. IDEA.md frames the problem
and points at related work, and the design comes out of brainstorming.

### How do I choose a workflow once there's a spec?

**Answer:** by size and shape:
- a single change goes from one issue to one PR (`github-issue-to-pr`);
- planned multi-task work becomes an epic with subagents
  (`github-milestone-plan-to-issues`, then `github-epic-to-merged-prs`);
- independent items in the backlog get burned down (`github-issue-burndown`).

**Notes:** this confirms what the skills imply.

### How much do I stay in the loop?

**Answer:** "It depends on the project, sometimes I use those checkpoints as listed,
but other times I will curate the process issue-by-issue with github-issue-to-pr."

The listed checkpoints are:
- accepting the spec;
- accepting the sub-issue breakdown in plan mode;
- real design questions;
- the final merge into `main`.

Under a standing merge authorization, the rest runs on its own: implementing, answering
Brooke, and merging sub-issue PRs into the milestone branch.

### When do I curate issue by issue instead?

**Answer:** when the project is new or risky, or when the design is still moving.

**Notes:** curating means running `github-issue-to-pr` on one issue at a time and
looking at each PR before starting the next. The skills don't describe this as a
mode, so the site should present it as a choice. Not chosen: learning the codebase,
and machine or budget limits.

### Where do the sessions run?

**Answer:** on one shared workstation, in Claude Code in a terminal, often for several
projects at once.

**Notes:** this confirms why the skills have rules for worktrees, caches, gate locks
and killing processes by PID only.

## 2. Idea to merged PRs

## 3. Backlog burndown

## 4. Validating with claims-mcp

## 5. Study guides

## 6. The supporting setup
