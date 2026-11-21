# Task runner for the skills repo. Run `just` to list recipes.
#
# Everything runs through uv (https://docs.astral.sh/uv/), which fetches Python and the
# tool's dependencies on demand. tools/skills.py validates the catalog and skills and
# generates the vendor manifests.

set shell := ["bash", "-euo", "pipefail", "-c"]

skills := "uv run --quiet --script tools/skills.py"

# List the available recipes.
default:
    @just --list

# Validate every skill against the Agent Skills spec and catalog.yaml.
validate:
    {{ skills }} validate

# Regenerate every vendor manifest. Commit the result with your skill change.
generate:
    {{ skills }} generate

# Fail if any generated manifest is missing or out of date.
generate-check:
    {{ skills }} generate --check

# Type-check the tool, skill scripts and tests with mypy in strict mode, one file at a
# time so that scripts with the same filename in different skills don't collide.
typecheck:
    find tools plugins tests -name '*.py' -print0 \
        | xargs -0 -n1 uvx --with types-PyYAML --with pyyaml mypy --strict --no-error-summary

# Run the tests for the tool and for skill scripts.
test:
    uv run --quiet --no-project --with pyyaml python -m unittest discover --start-directory tests

# Run everything CI runs. Use before pushing.
check: validate generate-check typecheck test
