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

### How often do I use these skills?

**Answer:** "Every day."

**Notes:** Peter confirmed this on 2026-11-21, when an audit flagged the home page's
"every day" claim (issue #39, N3). It is the source for that sentence.

## 2. Idea to merged PRs

### How closely do I read the spec and the plan?

**Answer:** I approve the spec only.

**Notes:** once the spec is right, Peter doesn't read the plan. Brooke's review of
the plan PR and the gates catch problems in the plan. The site should say plainly
that the spec is where Peter puts his attention.

### What do I check when accepting the sub-issue breakdown?

**Answer:** "I don't use this one as much anymore, but I usually just trusted it."

### What replaced the breakdown step?

**Answer:** the milestone skill does it. `github-milestone-plan-to-issues` files one
sub-issue per plan task, so there's no separate breakdown to review.

**Notes:** `github-issue-to-subissues` still runs inside the milestone skill. On its
own it's for an epic that has no checked-in plan. The site should present the
milestone skill as the normal path.

### What do I rely on Brooke's review for?

**Answer:** all four:
- **Real bugs:** correctness and edge cases the agent missed.
- **Plan fidelity:** the PR does what the plan and design said.
- **Honest PR descriptions:** she catches claims the diff doesn't support.
- **Security:** a blocking security finding escalates a PR to Opus.

**Notes:** epic #3 has an example of each:
- **Real bugs:** path traversal in `write_reference` (#18) and the release skip's
  SIGPIPE (#25, fixed in #27).
- **Plan fidelity:** her plan-fidelity section in each review.
- **Honest PR descriptions:** a stale description on #16, and the scope claim on #29.

### Why merge an epic into a milestone branch instead of `main`?

**Answer:**
- **`main` stays shippable:** half a milestone never reaches `main` or a release,
  and hotfixes can still go out.
- **One final review:** Brooke and the close-out audit see the whole milestone at
  once, which catches problems that span PRs. On #25 she caught one that every
  sub-issue review had missed.
- **Easy to abandon:** if the milestone goes wrong, `main` is untouched.

**Notes:** "fewer releases" wasn't chosen as a reason.

### What goes wrong most often?

**Answer:** all four:
- **Cost and context:** Opus implementers and large coordinator contexts use up the
  weekly limit.
- **Stalled reviews:** Brooke skips a stale branch or misses a request, and the PR
  sits.
- **Machine overload:** too many agents, gates or build caches at once.
- **Scope creep:** follow-ups and audit findings grow the epic past the plan.

**Notes:** each has a recorded incident and a rule in the skills:
- **Cost and context:** Sonnet first, state files and `/compact` checkpoints.
- **Stalled reviews:** stale-branch merges, `/prrb` and watchers.
- **Machine overload:** gate locks, `cargo clean` before removing a worktree, and
  limits on parallel agents.
- **Scope creep:** ask once, in a batch, which follow-ups belong in the epic.

The site's how-to and explanation pages should present them as warnings.

### Is the close-out audit worth it?

**Answer:** yes, it finds gaps. It has caught real misses after every PR had passed
review, such as undocumented divergences and acceptance criteria with no test.

## 3. Backlog burndown

### How does an issue earn the `accepted` label?

**Answer:** "Sometimes I make an issue, sometimes an agent makes an issue, either way I
read, groom if needed, then apply the label."

**Notes:** the label is Peter's decision, whoever filed the issue. Filers include Peter,
implementers and Brooke follow-ups. Peter grooms (`github-groom-issue`) only when an
issue is too vague to implement unattended.

### When do I run a burndown?

**Answer:** during unattended stretches, and when the backlog piles up.

**Notes:** the burndown runs one issue at a time and stops on anything hard. Not
chosen: between milestones, and alongside an epic.

### What happens to a `burndown-blocked` issue?

**Answer:** "I usually ask claude in a separate session to work interactively with me
on the issue so we can get it either fixed for resume, or pushed manually."

**Notes:** a blocked issue goes to a hands-on session. That session either fixes it
so the burndown can pick it up again, or finishes and pushes it directly. The skills
stop at the label, so the site's burndown how-to should add this step.

### Should follow-ups the burndown files wait for me?

**Answer:** yes, keep them waiting. Nothing enters the queue until Peter has read it.
Otherwise the burndown would feed itself.

## 4. Validating with claims-mcp

### What does the claims audit catch that the gates miss?

**Answer:**
- **The change didn't do what was asked:** the code passes, but part of the issue or
  plan was quietly dropped.
- **The PR body overclaims:** the description says things the diff doesn't support.
- **Self-grading bias:** the implementer can't fairly grade its own work, so a fresh
  subagent on a different model checks it independently.

**Notes:** "regressions recorded in the ledger" wasn't chosen as a main reason.

### Which projects get a committed ledger (`claims.json`)?

**Answer:** "Generally long-lived, spec-driven, or correctness-matters projects.
Sometimes I delay the committed ledger until a later date, which spawns a raft of
issues. It's better to start the ledger very early if you think you're going to need
it."

**Notes:** advice for copiers: start the ledger at the beginning of any project that
may need one. Adding it later means backfilling claims for everything already built,
and that turns up a batch of issues at once. Other projects stay in table-only mode.

### Where else do I use `claims-audit`?

**Answer:**
- **Generated docs:** study guides, and this site's pages in phase 4.
- **Agent outputs:** checking that a long agent task did everything its brief asked.

**Notes:** milestone audits weren't chosen. `github-epic-close-out` covers those.

### What do I do with the audit's results?

**Answer:** I leave it to Brooke.

**Notes:** the audit's table goes in the PR body. Brooke's review checks the body's
claims against the diff, and Peter rarely reads the table himself. So the audit and
Brooke make two independent checks on the description before Peter looks at it.

## 5. Study guides

### What do I use study guides for?

**Answer:** learning a codebase, talking about it knowledgeably, and onboarding
others.

**Notes:** the flashcards weren't chosen. The skill writes them, but Peter doesn't
mention studying them, so the site shouldn't present them as central.

### Why generate, fact-check and reconcile instead of trusting the first draft?

**Answer:** all four reasons:
- **Hallucinations:** generated docs confidently describe code that doesn't exist or
  works differently.
- **Circular reasoning:** a guide that cites itself or other docs instead of the code
  looks right but isn't grounded.
- **Overconfidence:** guesses get stated as facts. The reconcile step reframes them.
- **Experience:** Peter has been burned by unchecked output before.

### What burned me?

**Answer:** "I had a software project that confidently claimed a feature was
implemented and it was not implemented, and was only found when I used
claims-mcp/claims-audit to find it."

**Notes:** this is the origin story for both checking loops:
- fact-checking generated docs (this area);
- auditing claims (area 4).

The site's explanation pages should tell it once, in "Why audit claims", and link to
it from "Why I fact-check generated docs". Name no private project.

### How do I finish a guide that has deferred findings?

**Answer:** it depends on the situation. Peter either uses the guide as it is, with
the deferred items still flagged, or resolves them, now or later.

**Notes:** deferred findings stay marked in the guide, so the guide is usable before
every finding is resolved.

### Which models do I use for writing and checking a guide?

**Answer:** "I generally use a opus writes / sonnet checks workflow with the study
guide."

**Notes:** the skills ask only that the two passes run on different models, without
naming any. Peter's usual pairing is Opus to write and Sonnet to fact-check. He added
this on 2026-11-21, after area 4 was published.

### How do I switch models for the check?

**Answer:** "I use /model in a fresh new claude code window usually."

**Notes:** this gives the check a fresh context as well as a different model: a new
session, then `/model`. Running `/model` in the writer's own session would leave the
writing conversation in context.

## 6. The supporting setup

### What does the knowledge catalog give me that CLAUDE.md and built-in memory don't?

**Answer:** all four, plus: "It enriches essentially every interaction I have with an
LLM these days."
- **Shared across projects:** every session and project reads the same place.
- **Reviewed and versioned:** changesets, history and revert, so Peter can audit and
  undo what an agent wrote.
- **Lessons compound:** a failure in one project becomes a rule that every later
  session sees.
- **Works beyond Claude Code:** any MCP harness can read and write it, even without a
  filesystem.

**Notes:** for the explanation page "The knowledge catalog as long-term memory".
Epic #3's own example: the Brooke behaviours learned on earlier projects, such as
stale-branch skips and no re-review of an unchanged head, were already in the
catalog when this epic ran.

### Why Sonnet first, with Opus only on a recorded trigger?

**Answer:** the usage limit, and keeping judgment at the top.
- **The usage limit:** Opus implementers were most of the weekly spend.
- **Judgment at the top:** planning, design and coordination are where the stronger
  model pays off.

**Notes:** Peter's reasons don't include that Sonnet is enough or that escalation is
rare, though epic #3 escalated zero times. The site can give that as an observation,
not as Peter's reason.

### Which shared-machine rule comes first for a copier?

**Answer:** "Worktree per agent is table stakes but the rest of these are also
incredibly important, they're equally important but the worktree per agent is first
among equals for sure."

**Notes:** the explanation page should present the rest as equally important. Each
one came from an incident:
- bound and serialize the gates;
- mind the disk: build caches per worktree, and `cargo clean` before removing one;
- never touch other sessions' processes or caches: kill by PID only, no pattern
  kills, no machine-wide prunes.

### What should a copier without Brooke use?

**Answer:** any review bot, or a human reviewer. "prrb isn't a public product yet."

**Notes:**
- Don't link to prrb or present it as installable.
- The site can describe what Brooke checks, as an example of what a reviewer should
  check.
- The how-to "Adapt the skills to your setup" should cover switching the reviewer:
  the bot's login, its re-trigger command and the watcher scripts.
