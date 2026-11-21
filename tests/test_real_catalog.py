"""Checks on this repository's own catalog.yaml, not on a fixture."""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any

import yaml

CATALOG = Path(__file__).resolve().parents[1] / "catalog.yaml"

# Skills that run github-issue-to-pr only through an implementer subagent.
INDIRECT = ("github-issue-burndown", "github-epic-to-merged-prs")


def skill_requires(plugin: str, skill: str) -> dict[str, dict[str, Any]]:
    data = yaml.safe_load(CATALOG.read_text())
    for entry in data["plugins"]:
        if entry["name"] != plugin:
            continue
        for item in entry["skills"]:
            if isinstance(item, dict) and item["name"] == skill:
                return {req["id"]: req for req in item.get("requires", [])}
    raise AssertionError(f"{skill} not found in {plugin}")


class IndirectRequirementsTest(unittest.TestCase):
    def test_skills_that_run_the_implementer_require_its_tools(self) -> None:
        for skill in INDIRECT:
            reqs = skill_requires("github-workflows", skill)
            for dep in ("just", "claims-audit"):
                with self.subTest(skill=skill, dep=dep):
                    self.assertIn(dep, reqs)
                    self.assertFalse(reqs[dep].get("optional", False))
                    self.assertIn("implementer", reqs[dep]["for"])


if __name__ == "__main__":
    unittest.main()
