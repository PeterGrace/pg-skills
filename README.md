# pg-agent-skills

My personal AI agent skills: one place to write and version them, installable in Claude
Code, Claude apps, GitHub Copilot CLI, OpenAI Codex, Cursor and Gemini CLI.

Skills follow the [Agent Skills spec](https://agentskills.io/specification). The
tooling is one self-contained script, `tools/skills.py`, run through `just` and `uv`.

## What's here

| Path | What it is | Edit by hand? |
|---|---|---|
| `catalog.yaml` | The plugins, and which skills each one ships | yes |
| `plugins/<plugin>/skills/<skill>/` | One skill: `SKILL.md` plus optional `references/`, `scripts/`, `assets/` | yes |
| `tools/skills.py` | Validates the catalog and skills, and generates the manifests | yes |
| `tests/` | Tests for the tool, and for skill scripts in `tests/skill_scripts/` (kept out of the skills so they aren't shipped) | yes |
| `.claude-plugin/`, `.github/plugin/`, `.agents/plugins/`, `.cursor-plugin/` | Vendor marketplace files | **no, generated** |
| `plugins/<plugin>/plugin.json`, `plugins/<plugin>/gemini-extension.json` | Per-plugin manifests | **no, generated** |

Generated files are rebuilt by `just generate`, and CI fails if they are out of date.

## Installing the skills

The marketplace is named **`pg-skills`**. Plugins today: `skill-authoring`.

| Client | How |
|---|---|
| **Claude Code** | `/plugin marketplace add PeterGrace/pg-agent-skills`, then `/plugin install skill-authoring@pg-skills` (or `claude plugin install ...` from a shell) |
| **Claude apps** (claude.ai, desktop) | *Customize*, *Plugins*, *Add marketplace*, and give it this repo. |
| **GitHub Copilot CLI** | `copilot plugin marketplace add PeterGrace/pg-agent-skills`, then `copilot plugin install skill-authoring@pg-skills` |
| **OpenAI Codex** (CLI and desktop app) | `codex plugin marketplace add PeterGrace/pg-agent-skills`, then install from `/plugins` in the CLI or the app's Plugins directory. The IDE extension doesn't support plugins. |
| **Cursor** | *Customize*, *Plugins*, add this repo as a marketplace, tracking `main`. |
| **Gemini CLI** | Gemini can't install an extension from a repo subfolder, so clone first: `git clone git@github.com:PeterGrace/pg-agent-skills.git`, then `gemini extensions install ./pg-agent-skills/plugins/skill-authoring` |

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
   - **Only spec fields are allowed at the top level:** `name`, `description`,
     `license`, `compatibility`, `metadata`, `allowed-tools`. Any other key is an
     error; put extras under `metadata`, with string values.
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

## Releases

Every push to `main` is a release. Once CI passes on `main`, it tags the next patch
version (`v0.1.0`, `v0.1.1`, ...) and publishes a GitHub release. Marketplace clients
that track `main` (Claude, Copilot, Codex, Cursor) pick up the same commit. Claude Code
updates an installed plugin only when its `version` changes, which is why every skill
change needs a version bump (step 5 above).

Nobody tags releases by hand. Only CI does.
