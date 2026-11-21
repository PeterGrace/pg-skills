---
title: Your first issue to merged PR
description: Install the github-workflows plugin, file a tiny issue on a sandbox repository, and take it through a reviewed pull request to a merge.
sidebar:
  order: 1
---

In this tutorial you take one small issue all the way to a merged pull request, with an
AI agent doing the work and you doing the reviewing. It takes about half an hour. At the
end you'll have a merged PR on a sandbox repository that you can delete afterwards.

You'll use two skills: `github-issue-to-pr`, which turns an issue into a PR, and
`github-address-pr-review`, which answers a review. This is the "curate issue by issue"
way of working that [I describe here](/pg-skills/explanation/how-i-work/), and the
smallest piece of my workflow.

## What you need

- [Claude Code](https://claude.com/claude-code), signed in.
- [Git](/pg-skills/reference/dependencies/#git), and the
  [GitHub CLI](/pg-skills/reference/dependencies/#gh) (`gh`), signed in. Check with
  `gh auth status`.
- [`just`](/pg-skills/reference/dependencies/#just), a command runner. The skills run the
  project's `just fmt` and `just test`.
- Python 3, for the sandbox project below.

## 1. Install the plugin

In Claude Code, run these two commands. They come from the
[github-workflows reference page](/pg-skills/reference/plugins/github-workflows/), which
has the install commands for other clients too.

```text
/plugin marketplace add PeterGrace/pg-skills
/plugin install github-workflows@pg-skills
```

Start a new Claude Code session afterwards so it loads the plugin.

## 2. Create a sandbox repository

In a terminal, create a tiny project and push it to a new repository on your own
account. The project is one function and one test, and a `justfile` with the two
recipes that `github-issue-to-pr` expects, `fmt` and `test`.

```bash
mkdir sandbox-greeter && cd sandbox-greeter
git init -b main

cat > greeter.py <<'PY'
def greet(name):
    return "Hello, " + name + "!"
PY

cat > test_greeter.py <<'PY'
import unittest
from greeter import greet


class GreetTest(unittest.TestCase):
    def test_greet(self):
        self.assertEqual(greet("Ada"), "Hello, Ada!")


if __name__ == "__main__":
    unittest.main()
PY

cat > justfile <<'JUST'
fmt:
    @echo "nothing to format"

test:
    python3 -m unittest -v
JUST

cat > .gitignore <<'IGNORE'
__pycache__/
*.py[cod]
IGNORE

just test
git status --short
git add . && git commit -m "Add greeter"
gh repo create sandbox-greeter --private --source=. --push
```

`just test` should print `OK`. The `.gitignore` keeps Python's `__pycache__` out of the
repository, so later test runs don't leave the working tree dirty. `git status --short`
should list only `.gitignore`, `greeter.py`, `justfile` and `test_greeter.py`. Making the repository private keeps your sandbox out of
sight, and you can delete it at the end.

## 3. File a tiny issue

```bash
gh issue create --title "greet should handle an empty name" --body "greet(\"\") returns \"Hello, !\". It should return \"Hello, stranger!\" instead. Add a test."
```

Note the issue number it prints. The rest of this tutorial calls it `1`.

## 4. Run github-issue-to-pr

Open Claude Code in the `sandbox-greeter` directory and say:

```text
Run the github-issue-to-pr skill on issue 1.
```

Here is what you should see. The skill is a push-through workflow, so it doesn't stop
to ask you unless something fails.

1. Because your session is the top-level one, it hands the work to an `issue-implementer`
   subagent in a worktree of its own, and relays the report. The skill relays that agent's report when it
   finishes.
2. The agent reads the issue, creates a branch named `<prefix>-issue-1-<slug>`, where the
   prefix (`fix`, `feat` or `issue`) depends on the issue's labels and the slug comes from its title, and makes the change.
3. It runs `just fmt` and `just test`. It skips `cargo clippy` because the project has no
   `Cargo.toml`, and says so.
4. A second, fresh subagent audits the claims in the PR description. Your repository has
   no `claims.json`, so the audit runs in table-only mode and nothing is recorded; the
   results go into the PR body. The audit follows the
   [`claims-audit`](/pg-skills/reference/dependencies/#claims-audit) skill, which this
   plugin doesn't ship. If your agent can't find it, it may report the audit as skipped,
   and the rest of the tutorial still works.
5. It commits, pushes, opens a PR whose body includes `Closes #1`, and comments the PR
   link on the issue.

When it finishes you have a PR number. Open it with `gh pr view 2 --web` (use your number)
and look at the Summary, the Validation section and the Claims table.

## 5. Review the PR

I use a review bot, Brooke, for this step. You probably don't have one, so you'll be the
reviewer. A bot is optional. To see what a bot review looks like, read
[one of Brooke's](/pg-skills/explanation/review-bot/#read-three-real-reviews). You don't
need one to finish this tutorial.

Post a review that asks for one more change. GitHub won't let you approve your own PR, so
leave a comment review:

```bash
gh pr review 2 --comment --body "Please also add a test for a name with surrounding spaces: greet(\"  Ada  \") should return \"Hello, Ada!\"."
```

You can also open the PR in your browser, go to Files changed and leave inline comments on
particular lines. The next skill reads both kinds.

## 6. Run github-address-pr-review

Back in Claude Code, say:

```text
Walk through the review comments on PR 2.
```

The implementer's worktree may still have the PR's branch checked out. If the skill
reports that it can't check the branch out, run `git worktree list`, remove the
implementer's worktree with `git worktree remove <path>`, and ask again.

This skill never asks you anything. For your comment it should:

1. fetch the PR's conversation comments, inline comments and review bodies, and find
   yours;
2. decide to apply it, because it's a sensible, cheap request within the PR's scope;
3. edit the code, add the test and commit it, quoting your comment in the message;
4. run `just fmt` and `just test` again, and push only when they pass;
5. reply naming the commit, after the push (a review body gets a top-level PR comment
   rather than a threaded reply);
6. end with a report: the PR, a count per disposition, the commit SHAs, the validation
   results and the push status.

The skill may also choose to explain and change
nothing, and then you'll see a reply saying why. Either is a valid way to finish this step.

## 7. Merge

Check the PR's checks and read the new commit. Then merge. The skill doesn't merge
for you, and neither does the workflow unless you tell it to.

```bash
gh pr merge 2 --merge
```

Because the PR's base is `main`, the `Closes #1` in its body closes the issue when it
merges. Check:

```bash
gh issue view 1 --json state -q .state
```

It prints `CLOSED`.

## What you did

You took one issue to a merged PR: an implementer agent opened the PR and a second agent
audited its claims, you reviewed it, and a second skill answered your review. That's the
whole loop. The epic workflow runs this same loop for many issues at once.

## Next steps

- Delete the sandbox: `gh repo delete sandbox-greeter --yes` (`gh` may first ask you to run
  `gh auth refresh -s delete_repo`).
- Read [How I work](/pg-skills/explanation/how-i-work/) to see where this fits.
- Plan a larger piece of work with
  [Plan a milestone](/pg-skills/how-to/plan-a-milestone/).
