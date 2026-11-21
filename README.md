# pg-skills

My personal AI agent skills: one place to write and version them, installable in Claude
Code, Claude apps, GitHub Copilot CLI, OpenAI Codex, Cursor and Gemini CLI.

Skills follow the [Agent Skills spec](https://agentskills.io/specification). The
tooling is one self-contained script, `tools/skills.py`, run through `just` and `uv`.

**Documentation:** <https://petergrace.github.io/pg-skills/>, with how I use these
skills and a reference page for every plugin, skill and agent.

## What's here

| Path | What it is | Edit by hand? |
|---|---|---|
| `catalog.yaml` | The plugins, and which skills each one ships | yes |
| `plugins/<plugin>/skills/<skill>/` | One skill: `SKILL.md` plus optional `references/`, `scripts/`, `assets/` | yes |
| `plugins/<plugin>/agents/` | Claude Code subagents the plugin ships (found automatically; named `<plugin>:<agent>`) | yes |
| `GLOSSARY.md` | The personal names and conventions the skills use, and how to adapt them | yes |
| `tools/skills.py` | Validates the catalog and skills, and generates the manifests | yes |
| `site/` | The documentation site (Astro Starlight); its reference section is generated | yes, except `site/src/content/docs/reference/` |
| `tests/` | Tests for the tool, and for skill scripts in `tests/skill_scripts/` (kept out of the skills so they aren't shipped) | yes |
| `.claude-plugin/`, `.github/plugin/`, `.agents/plugins/`, `.cursor-plugin/` | Vendor marketplace files | **no, generated** |
| `plugins/<plugin>/plugin.json`, `plugins/<plugin>/gemini-extension.json` | Per-plugin manifests | **no, generated** |

Generated files are rebuilt by `just generate`, and CI fails if they are out of date.

## Installing the skills

The marketplace is named **`pg-skills`**. The skills are written for my own setup and
name my review bot, servers and conventions; [GLOSSARY.md](GLOSSARY.md) explains each
one and what to change to adapt it.

| Plugin | What it does |
|---|---|
| `github-workflows` | Issue-to-merged-PR workflows on GitHub with `gh`: plan, groom and split issues, implement them with subagents in worktrees, answer review-bot feedback, burn down a backlog, close out epics. Ships the `issue-implementer` subagent. |
| `forgejo-workflows` | The same planning, grooming and issue-to-PR workflows on Forgejo, through forgejo-mcp. Its subagent fan-out needs `github-workflows` installed too, for `issue-implementer`. |
| `study-guides` | Write study docs for a codebase, fact-check them against the code, and reconcile the fact-check back in. |
| `skill-authoring` | How to add or change a skill in this repository. |
| `usage-analysis` | Work out where Claude Code token usage went, from local transcripts, and what to change. |

The examples below install `skill-authoring`; substitute any plugin name.

| Client | How |
|---|---|
| **Claude Code** | `/plugin marketplace add PeterGrace/pg-skills`, then `/plugin install skill-authoring@pg-skills` (or `claude plugin install ...` from a shell) |
| **Claude apps** (claude.ai, desktop) | *Customize*, *Plugins*, *Add marketplace*, and give it this repo. |
| **GitHub Copilot CLI** | `copilot plugin marketplace add PeterGrace/pg-skills`, then `copilot plugin install skill-authoring@pg-skills` |
| **OpenAI Codex** (CLI and desktop app) | `codex plugin marketplace add PeterGrace/pg-skills`, then install from `/plugins` in the CLI or the app's Plugins directory. The IDE extension doesn't support plugins. |
| **Cursor** | No command-line install. On a Teams plan (one team marketplace) or an Enterprise plan (unlimited), import this repo with *Import from Repo* under *Dashboard*, *Plugins & MCPs*, *Team Marketplaces* ([Cursor's plugin docs](https://cursor.com/docs/plugins)); members then find the plugins in *Customize*. Cursor reads `.cursor-plugin/marketplace.json`. |
| **Gemini CLI** | Gemini can't install an extension from a repo subfolder, so clone first: `git clone git@github.com:PeterGrace/pg-skills.git`, then `gemini extensions install ./pg-skills/plugins/skill-authoring` |

## Adding or changing a skill

The `authoring-skills` skill walks an agent through this; install `skill-authoring` and
ask it to add a skill.

1. **Pick a plugin**, or add one to `catalog.yaml` (and create `plugins/<plugin>/skills/`):

   ```yaml
   - name: release-tools            # kebab-case; also its directory under plugins/
     description: "Skills for versioning and releasing software."   # always quoted; 1-1024 characters
     version: 0.1.0                 # semver; bump it with every change to its skills
     category: Developer Tools      # required (Codex needs one)
     keywords: [release, semver]    # optional
     skills:
       - semver-bump
   ```

2. **Write `plugins/<plugin>/skills/<skill>/SKILL.md`:**

   ```markdown
   ---
   name: semver-bump               # must equal the directory name
   description: "Computes the next semantic version... Use when cutting a release, ..."
   ---

   # Instructions for the agent...
   ```

   - **`description` decides when agents load the skill**, so say what it does *and
     when to use it*. It must be 1-1024 characters. Always wrap it in double quotes,
     here and in `catalog.yaml`: unquoted, ` #` starts a YAML comment and silently
     truncates the text, and `just check` doesn't catch it.
   - **Top-level keys are the spec's** (`name`, `description`, `license`,
     `compatibility`, `metadata`, `allowed-tools`) **plus Claude Code's** (such as
     `argument-hint`, `disable-model-invocation`, `user-invocable`, `model`,
     `context`, `agent`, `paths`). Any other key is an error; put extras under
     `metadata`, with string values. claude.ai and the Skills API refuse uploads with
     Claude Code keys, so leave them out of skills meant for those.
   - **Refer to other plugin skills and agents by their namespaced name**
     (`github-workflows:issue-implementer`), and to files in the skill with
     `${CLAUDE_SKILL_DIR}`, never a home-directory path.
   - **Name anything personal in [GLOSSARY.md](GLOSSARY.md)**: bots, servers, repos and
     conventions a reader would have to swap for their own.
   - **Keep `SKILL.md` under 500 lines.** Put detail in `references/`, which agents load
     only when needed.
   - **Names must be unique across all plugins.** They are lowercase letters, digits and
     single hyphens, and may not contain `claude` or `anthropic`, which claude.ai
     rejects.

3. **Scripts (optional).** Put them in `scripts/`, and test them in
   `tests/skill_scripts/`. Python scripts need full type hints and must pass
   `mypy --strict`.

4. **Regenerate and check:**

   ```
   just generate
   just check
   ```

   `just check` validates every skill against the spec and the catalog, checks the
   generated files are current, and type-checks and runs the tests. It needs only
   [`just`](https://just.systems) and [`uv`](https://docs.astral.sh/uv/).

5. **Bump the plugin's `version`** in `catalog.yaml` whenever you change any of its
   skills, then run `just generate` again. Claude Code treats a plugin's version as a
   pin: without a bump, existing installs don't receive the change.

6. **Commit the skill and the generated files together**, and push to `main` (or merge
   a pull request once CI is green).

## The documentation site

```
(cd site && npm ci)   # once per checkout: install the site's dependencies (needs Node and npm)
just site-dev         # preview at http://localhost:4321/pg-skills/
just site-build       # what CI runs: install, generate the reference, build, check every link
```

`just site-dev` doesn't install dependencies; `just site-build` does (`npm ci`), so
running it once also works.

The build also publishes the site for AI agents: `llms.txt` (an index), `llms-full.txt`
(every page in one file) and `llms-small.txt` (an abridged version), plus a raw markdown
copy of every page at its address with `.md` in place of the trailing slash (the home page
is `index.md`). Point an agent at `https://petergrace.github.io/pg-skills/llms-full.txt`.
The per-page endpoint is `site/src/pages/[...slug].md.ts`.

The reference pages are written by `tools/skills.py reference` from `catalog.yaml`,
each `SKILL.md`, each plugin's `agents/` and `GLOSSARY.md`, so they never need a
hand edit. Pushes to `main` that touch the site, the skills or the tooling redeploy
it. Changes only under `site/` or `docs/` don't cut a release.

## Releases

Every push to `main` is a release. Once CI passes on `main`, it tags the next patch
version (`v0.1.0`, `v0.1.1`, ...) and publishes a GitHub release. Marketplace clients
that track `main` (Claude, Copilot, Codex, Cursor) pick up the same commit. Claude Code
updates an installed plugin only when its `version` changes, which is why every skill
change needs a version bump (step 5 above).

Nobody tags releases by hand. Only CI does.
