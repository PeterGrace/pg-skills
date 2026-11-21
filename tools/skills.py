#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""Validate the skills catalog and generate every vendor's marketplace manifests.

`catalog.yaml` and `plugins/<plugin>/skills/<skill>/SKILL.md` are the source of truth.
Everything `generate` writes is an output; never edit those files by hand.

Usage (from the repository root):
    uv run --script tools/skills.py validate
    uv run --script tools/skills.py generate [--check]
    uv run --script tools/skills.py reference --out DIR --repo OWNER/NAME --url-prefix PATH
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

CATALOG_FILE = "catalog.yaml"
PLUGINS_DIR = "plugins"
SKILLS_DIR = "skills"
SKILL_FILE = "SKILL.md"
AGENTS_DIR = "agents"
SCHEMA_VERSION = 1

MAX_NAME_LEN = 64
MAX_DESCRIPTION_LEN = 1024
MAX_COMPATIBILITY_LEN = 500
RECOMMENDED_MAX_LINES = 500

AGENT_PLUGINS_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"

# Names Claude Code and claude.ai refuse. The docs list marketplace names "and others",
# so this can be incomplete; `claude plugin validate` is the final word.
RESERVED_MARKETPLACE_NAMES = frozenset(
    {
        "agent-skills",
        "anthropic-agent-skills",
        "anthropic-plugins",
        "cargo",
        "claude-code-plugins",
        "claude-for-legal",
        "claude-plugins-official",
        "claude-tag-plugins",
        "gh",
        "github",
        "knowledge-work-plugins",
        "life-sciences",
        "npm",
        "pip",
        "uv",
    }
)
RESERVED_MARKETPLACE_PREFIX = "claudeai-"
RESERVED_PLUGIN_NAMES = frozenset(
    {"anthropic", "anthropics", "claude", "claude-code", "claude-mods"}
)
RESERVED_PLUGIN_PREFIXES = ("anthropic-", "anthropics-", "cc-plugin-", "claude-")
RESERVED_SKILL_WORDS = ("anthropic", "claude")

# Agent Skills spec top-level frontmatter keys (https://agentskills.io/specification).
REQUIRED_SKILL_KEYS = frozenset({"name", "description"})
SPEC_SKILL_KEYS = frozenset({"license", "compatibility", "metadata", "allowed-tools"})

# Keys Claude Code adds (https://code.claude.com/docs/en/skills, checked 2026-11-21),
# with the YAML types each accepts. Other harnesses ignore them, but claude.ai and the
# Skills API reject a skill upload that has any of them.
STR: tuple[type, ...] = (str,)
STR_OR_LIST: tuple[type, ...] = (str, list)
CLAUDE_CODE_KEYS: dict[str, tuple[type, ...]] = {
    "when_to_use": STR,
    "argument-hint": STR,
    "arguments": STR_OR_LIST,
    "disable-model-invocation": (bool,),
    "user-invocable": (bool,),
    "disallowed-tools": STR_OR_LIST,
    "model": STR,
    "effort": STR,
    "context": STR,
    "agent": STR,
    "background": (bool,),
    "hooks": (dict,),
    "paths": STR_OR_LIST,
    "shell": STR,
}
CLAUDE_CODE_CHOICES: dict[str, frozenset[str]] = {
    "effort": frozenset({"low", "medium", "high", "xhigh", "max"}),
    "context": frozenset({"fork"}),
    "shell": frozenset({"bash", "powershell"}),
}
OPTIONAL_SKILL_KEYS = SPEC_SKILL_KEYS | frozenset(CLAUDE_CODE_KEYS)

NAME_PATTERN = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
SEMVER_PATTERN = re.compile(
    r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?"
)


@dataclass(frozen=True)
class Issue:
    """One problem found during validation."""

    path: str
    message: str
    error: bool = True

    def __str__(self) -> str:
        level = "error" if self.error else "warning"
        return f"{level}: {self.path}: {self.message}"


# Kinds of external dependency, in the order the dependencies page lists them.
DEPENDENCY_KINDS = {
    "skill-pack": "Skill packs",
    "skill": "Skills",
    "mcp-server": "MCP servers",
    "cli": "Command-line tools",
    "service": "Services",
}
DEPENDENCIES_PAGE = "dependencies"


@dataclass(frozen=True)
class Dependency:
    """Something the skills need that this repository doesn't ship."""

    id: str
    name: str
    kind: str
    description: str
    url: str | None = None
    note: str | None = None
    install: str | None = None


@dataclass(frozen=True)
class Requirement:
    """One `requires` item: a dependency, whether it is optional, and what it is for."""

    id: str
    purpose: str
    optional: bool = False


@dataclass(frozen=True)
class Plugin:
    """A validated `catalog.yaml` plugin entry."""

    name: str
    description: str
    version: str
    category: str
    keywords: tuple[str, ...]
    skills: tuple[str, ...]
    requires: tuple[Requirement, ...] = ()
    skill_requires: dict[str, tuple[Requirement, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class Catalog:
    """A validated `catalog.yaml`."""

    name: str
    description: str
    owner: dict[str, str]
    plugins: tuple[Plugin, ...]
    dependencies: tuple[Dependency, ...] = ()


@dataclass
class Report:
    """Everything validation found."""

    issues: list[Issue] = field(default_factory=list)
    catalog: Catalog | None = None

    @property
    def has_errors(self) -> bool:
        return self.catalog is None or any(issue.error for issue in self.issues)

    def add(self, path: str | Path, message: str, *, error: bool = True) -> None:
        self.issues.append(Issue(str(path), message, error))


def name_problem(name: object) -> str | None:
    """Returns why `name` is not a valid kebab-case name, or None if it is."""
    if not isinstance(name, str) or not name:
        return "name must be a non-empty string"
    if len(name) > MAX_NAME_LEN:
        return f"name is {len(name)} characters long; the maximum is {MAX_NAME_LEN}"
    if not NAME_PATTERN.fullmatch(name):
        return (
            f"name {name!r} must be lowercase ASCII letters, digits and single hyphens, "
            "not starting or ending with a hyphen"
        )
    return None


def length_problem(label: str, value: object, max_len: int) -> str | None:
    """Returns why `value` is not a string of 1 to `max_len` characters, or None."""
    if not isinstance(value, str):
        return f"{label} must be a string"
    length = len(value.strip())
    if length == 0 or length > max_len:
        return f"{label} is {length} characters long; it must be 1-{max_len}"
    return None


def unknown_keys(mapping: dict[Any, Any], allowed: frozenset[str]) -> list[str]:
    return sorted(str(key) for key in mapping if key not in allowed)


def split_frontmatter(source: str) -> tuple[str, str] | str:
    """Splits SKILL.md into (frontmatter YAML, body), or returns an error message."""
    source = source.removeprefix("﻿")
    lines = source.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        return "SKILL.md must start with a `---` line that opens the YAML frontmatter"
    for index, line in enumerate(lines[1:], start=1):
        if line.rstrip("\r\n") == "---":
            return "".join(lines[1:index]), "".join(lines[index + 1 :])
    return "the YAML frontmatter is never closed with a `---` line"


def check_skill(path: Path, dir_name: str, report: Report) -> None:
    """Validates one SKILL.md against the Agent Skills spec."""
    source = path.read_text(encoding="utf-8")
    line_count = len(source.splitlines())
    if line_count > RECOMMENDED_MAX_LINES:
        report.add(
            path,
            f"SKILL.md has {line_count} lines; keep it under {RECOMMENDED_MAX_LINES} "
            "and move detail to references/",
            error=False,
        )
    parts = split_frontmatter(source)
    if isinstance(parts, str):
        report.add(path, parts)
        return
    try:
        front = yaml.safe_load(parts[0])
    except yaml.YAMLError as error:
        report.add(path, f"invalid YAML frontmatter: {error}")
        return
    if not isinstance(front, dict):
        report.add(path, "frontmatter must be a YAML mapping")
        return
    for key in unknown_keys(front, REQUIRED_SKILL_KEYS | OPTIONAL_SKILL_KEYS):
        report.add(path, f"unknown top-level frontmatter key {key!r}; put it under metadata")
    for key in sorted(REQUIRED_SKILL_KEYS - front.keys()):
        report.add(path, f"missing required frontmatter key {key!r}")

    name = front.get("name")
    if "name" in front:
        if problem := name_problem(name):
            report.add(path, problem)
        elif name != dir_name:
            report.add(path, f"name {name!r} must equal its directory name {dir_name!r}")
        elif any(word in name for word in RESERVED_SKILL_WORDS):
            report.add(
                path,
                f"skill name {name!r} contains \"anthropic\" or \"claude\", "
                "which claude.ai and the API reject",
            )
    if "description" in front:
        if problem := length_problem("description", front["description"], MAX_DESCRIPTION_LEN):
            report.add(path, problem)
    if "compatibility" in front:
        problem = length_problem("compatibility", front["compatibility"], MAX_COMPATIBILITY_LEN)
        if problem:
            report.add(path, problem)
    if "license" in front and not isinstance(front["license"], str):
        report.add(path, "license must be a string")
    # The spec says a string; Claude Code also takes a YAML list.
    if "allowed-tools" in front and not isinstance(front["allowed-tools"], (str, list)):
        report.add(path, "allowed-tools must be a string or a list")
    for key, types in CLAUDE_CODE_KEYS.items():
        if key not in front:
            continue
        value = front[key]
        # bool is a subclass of int, but no key here takes an int, so isinstance is exact.
        if not isinstance(value, types):
            wanted = " or ".join(
                {str: "a string", list: "a list", bool: "true or false", dict: "a mapping"}[t]
                for t in types
            )
            report.add(path, f"{key} must be {wanted}")
        elif key in CLAUDE_CODE_CHOICES and value not in CLAUDE_CODE_CHOICES[key]:
            choices = ", ".join(sorted(CLAUDE_CODE_CHOICES[key]))
            report.add(path, f"{key} must be one of: {choices}")
    if "metadata" in front:
        metadata = front["metadata"]
        if not isinstance(metadata, dict):
            report.add(path, "metadata must be a mapping of strings to strings")
        else:
            for key, value in metadata.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    report.add(
                        path,
                        f"metadata.{key} must map a string to a string; quote values "
                        'such as "1.0" or "true"',
                    )


def parse_requires(
    raw: object, where: str, known: frozenset[str], report: Report
) -> tuple[Requirement, ...]:
    """Validates a `requires` list. Problems go to `report`; bad items are dropped."""
    if not isinstance(raw, list):
        report.add(where, "requires must be a list")
        return ()
    found: list[Requirement] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        here = f"{where}: requires[{index}]"
        if not isinstance(item, dict):
            report.add(here, "must be a mapping with id and for")
            continue
        for key in unknown_keys(item, frozenset({"id", "optional", "for"})):
            report.add(here, f"unknown key {key!r}")
        for key in ("id", "for"):
            if key not in item:
                report.add(here, f"missing required key {key!r}")
        dep_id, purpose = item.get("id"), item.get("for")
        optional = item.get("optional", False)
        if not isinstance(optional, bool):
            report.add(here, "optional must be true or false")
            optional = False
        if "for" in item and (not isinstance(purpose, str) or not purpose.strip()):
            report.add(here, "for must say, in a non-empty string, what the dependency is used for")
            continue
        if not isinstance(dep_id, str):
            continue
        if dep_id not in known:
            report.add(here, f"requires unknown dependency {dep_id!r}")
        elif dep_id in seen:
            report.add(here, f"requires {dep_id!r} more than once")
        elif isinstance(purpose, str):
            seen.add(dep_id)
            found.append(Requirement(dep_id, purpose, optional))
    return tuple(found)


def parse_dependency(raw: object, index: int, report: Report) -> Dependency | None:
    """Validates one `dependencies[]` entry, returning it if it is well-formed."""
    where = f"{CATALOG_FILE}: dependencies[{index}]"
    if not isinstance(raw, dict):
        report.add(where, "must be a mapping")
        return None
    errors_before = len(report.issues)
    allowed = frozenset({"id", "name", "kind", "description", "url", "note", "install"})
    for key in unknown_keys(raw, allowed):
        report.add(where, f"unknown key {key!r}")
    for key in ("id", "name", "kind", "description"):
        if key not in raw:
            report.add(where, f"missing required key {key!r}")
    if "id" in raw and (problem := name_problem(raw["id"])):
        report.add(where, f"id: {problem}")
    for key in ("name", "description", "note", "install"):
        if key in raw and (not isinstance(raw[key], str) or not raw[key].strip()):
            report.add(where, f"{key} must be a non-empty string")
    kind = raw.get("kind")
    if "kind" in raw and kind not in DEPENDENCY_KINDS:
        report.add(where, f"kind must be one of: {', '.join(DEPENDENCY_KINDS)}")
    url = raw.get("url")
    if url is not None and (
        not isinstance(url, str) or not url.startswith("https://") or len(url.split()) != 1
    ):
        report.add(where, "url must start with https:// and contain no spaces")
    if url is None and kind in DEPENDENCY_KINDS:
        if kind != "service":
            report.add(where, f"a dependency of kind {kind!r} needs a url")
        elif "note" not in raw:
            report.add(where, "a service without a url needs a note saying what to use instead")
    if len(report.issues) > errors_before:
        return None
    return Dependency(
        id=str(raw["id"]),
        name=str(raw["name"]),
        kind=str(kind),
        description=str(raw["description"]),
        url=url,
        note=raw.get("note"),
        install=raw.get("install"),
    )


def parse_dependencies(raw: object, report: Report) -> tuple[Dependency, ...]:
    """Validates the top-level `dependencies` list."""
    if raw is None:
        return ()
    if not isinstance(raw, list):
        report.add(CATALOG_FILE, "dependencies must be a list")
        return ()
    found: list[Dependency] = []
    for index, entry in enumerate(raw):
        dependency = parse_dependency(entry, index, report)
        if dependency is None:
            continue
        if any(dependency.id == other.id for other in found):
            report.add(CATALOG_FILE, f"dependency {dependency.id!r} is listed twice")
        else:
            found.append(dependency)
    return tuple(found)


def parse_plugin(
    raw: object, index: int, known: frozenset[str], report: Report
) -> Plugin | None:
    """Validates one `plugins[]` entry, returning it if it is well-formed."""
    where = f"{CATALOG_FILE}: plugins[{index}]"
    if not isinstance(raw, dict):
        report.add(CATALOG_FILE, f"plugins[{index}] must be a mapping")
        return None
    errors_before = len(report.issues)
    allowed = frozenset(
        {"name", "description", "version", "category", "keywords", "skills", "requires"}
    )
    for key in unknown_keys(raw, allowed):
        report.add(where, f"unknown key {key!r}")
    for key in sorted(allowed - {"keywords", "requires"} - raw.keys()):
        report.add(where, f"missing required key {key!r}")

    name = raw.get("name")
    if problem := name_problem(name):
        report.add(where, problem)
    elif isinstance(name, str) and (
        name in RESERVED_PLUGIN_NAMES or name.startswith(RESERVED_PLUGIN_PREFIXES)
    ):
        report.add(where, f"plugin name {name!r} is reserved by Claude Code")
    if problem := length_problem("description", raw.get("description"), MAX_DESCRIPTION_LEN):
        report.add(where, problem)
    version = raw.get("version")
    if not isinstance(version, str) or not SEMVER_PATTERN.fullmatch(version):
        report.add(where, f"version {version!r} must be a full semver string such as 0.1.0")
    category = raw.get("category")
    if not isinstance(category, str) or not category.strip():
        report.add(where, "category must be a non-empty string")
    keywords = raw.get("keywords", [])
    if not isinstance(keywords, list) or not all(isinstance(k, str) for k in keywords):
        report.add(where, "keywords must be a list of strings")
    requires = parse_requires(raw["requires"], where, known, report) if "requires" in raw else ()
    raw_skills = raw.get("skills")
    skills: list[str] = []
    skill_requires: dict[str, tuple[Requirement, ...]] = {}
    if not isinstance(raw_skills, list):
        report.add(where, "skills must be a list of skill names")
    else:
        for skill in raw_skills:
            if isinstance(skill, dict):
                skill_where = f"{where}: skills[{len(skills)}]"
                for key in unknown_keys(skill, frozenset({"name", "requires"})):
                    report.add(skill_where, f"unknown key {key!r}")
                if "requires" not in skill:
                    report.add(skill_where, "missing required key 'requires'")
                skill_name = skill.get("name")
                reqs = parse_requires(skill.get("requires", []), skill_where, known, report)
            else:
                skill_name, reqs = skill, ()
            if problem := name_problem(skill_name):
                report.add(where, f"skills: {problem}")
            elif isinstance(skill_name, str):
                skills.append(skill_name)
                if reqs:
                    skill_requires[skill_name] = reqs

    if len(report.issues) > errors_before:
        return None
    assert isinstance(name, str) and isinstance(version, str) and isinstance(category, str)
    return Plugin(
        name=name,
        description=str(raw["description"]),
        version=version,
        category=category,
        keywords=tuple(keywords),
        skills=tuple(skills),
        requires=requires,
        skill_requires=skill_requires,
    )


def parse_catalog(raw: object, report: Report) -> Catalog | None:
    """Validates the shape of `catalog.yaml`, returning it if it is well-formed."""
    if not isinstance(raw, dict):
        report.add(CATALOG_FILE, "the catalog must be a YAML mapping")
        return None
    errors_before = len(report.issues)
    for key in unknown_keys(raw, frozenset({"schema_version", "marketplace", "dependencies", "plugins"})):
        report.add(CATALOG_FILE, f"unknown key {key!r}")
    if raw.get("schema_version") != SCHEMA_VERSION:
        report.add(CATALOG_FILE, f"schema_version must be {SCHEMA_VERSION}")

    market = raw.get("marketplace")
    owner: dict[str, str] = {}
    if not isinstance(market, dict):
        report.add(CATALOG_FILE, "marketplace must be a mapping")
        market = {}
    else:
        for key in unknown_keys(market, frozenset({"name", "description", "owner"})):
            report.add(CATALOG_FILE, f"marketplace: unknown key {key!r}")
        name = market.get("name")
        if problem := name_problem(name):
            report.add(CATALOG_FILE, f"marketplace: {problem}")
        elif isinstance(name, str) and (
            name in RESERVED_MARKETPLACE_NAMES or name.startswith(RESERVED_MARKETPLACE_PREFIX)
        ):
            report.add(CATALOG_FILE, f"marketplace name {name!r} is reserved by Claude Code")
        description = market.get("description")
        if not isinstance(description, str) or not description.strip():
            report.add(CATALOG_FILE, "marketplace: description must be a non-empty string")
        raw_owner = market.get("owner")
        if not isinstance(raw_owner, dict):
            report.add(CATALOG_FILE, "marketplace: owner must be a mapping with a name")
        else:
            for key in unknown_keys(raw_owner, frozenset({"name", "email"})):
                report.add(CATALOG_FILE, f"marketplace.owner: unknown key {key!r}")
            for key in ("name", "email"):
                value = raw_owner.get(key)
                if value is None and key == "email":
                    continue
                if not isinstance(value, str) or not value.strip():
                    report.add(CATALOG_FILE, f"marketplace.owner.{key} must be a string")
                else:
                    owner[key] = value

    dependencies = parse_dependencies(raw.get("dependencies"), report)
    known = frozenset(dependency.id for dependency in dependencies)
    raw_plugins = raw.get("plugins")
    plugins: list[Plugin] = []
    if not isinstance(raw_plugins, list):
        report.add(CATALOG_FILE, "plugins must be a list")
    else:
        for index, entry in enumerate(raw_plugins):
            if plugin := parse_plugin(entry, index, known, report):
                plugins.append(plugin)
        used = {
            requirement.id
            for plugin in plugins
            for requirement in (
                *plugin.requires,
                *(r for reqs in plugin.skill_requires.values() for r in reqs),
            )
        }
        # A plugin dropped for another error may have been the only user, so check only
        # when every plugin parsed.
        if len(plugins) == len(raw_plugins):
            for dependency in dependencies:
                if dependency.id not in used:
                    report.add(
                        CATALOG_FILE,
                        f"dependency {dependency.id!r} is not required by any plugin or skill",
                    )

    if len(report.issues) > errors_before:
        return None
    return Catalog(
        name=str(market["name"]),
        description=str(market["description"]),
        owner=owner,
        plugins=tuple(plugins),
        dependencies=dependencies,
    )


def subdirectories(path: Path) -> list[str]:
    if not path.is_dir():
        return []
    return sorted(child.name for child in path.iterdir() if child.is_dir())


def validate(root: Path) -> Report:
    """Checks `catalog.yaml` and the plugin tree against each other and the spec."""
    report = Report()
    catalog_path = root / CATALOG_FILE
    try:
        raw = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        report.add(CATALOG_FILE, "not found; run from the repository root")
        return report
    except yaml.YAMLError as error:
        report.add(CATALOG_FILE, f"invalid YAML: {error}")
        return report
    catalog = parse_catalog(raw, report)
    if catalog is None:
        return report

    plugin_owner: dict[str, int] = {}
    skill_owner: dict[str, str] = {}
    for plugin in catalog.plugins:
        if plugin.name in plugin_owner:
            report.add(CATALOG_FILE, f"plugin {plugin.name!r} is listed twice")
            continue
        plugin_owner[plugin.name] = 1
        plugin_dir = Path(PLUGINS_DIR) / plugin.name
        if not (root / plugin_dir).is_dir():
            report.add(plugin_dir, f"plugin {plugin.name!r} has no directory")
            continue
        for skill in plugin.skills:
            if skill in skill_owner:
                report.add(
                    CATALOG_FILE,
                    f"skill {skill!r} is listed in both {skill_owner[skill]!r} and "
                    f"{plugin.name!r}; skill names must be unique",
                )
                continue
            skill_owner[skill] = plugin.name
            skill_dir = plugin_dir / SKILLS_DIR / skill
            if not (root / skill_dir).is_dir():
                report.add(skill_dir, f"skill {skill!r} is listed but has no directory")
            elif not (root / skill_dir / SKILL_FILE).is_file():
                report.add(skill_dir, f"missing {SKILL_FILE}")
            else:
                check_skill(root / skill_dir / SKILL_FILE, skill, report)

    listed = {plugin.name: set(plugin.skills) for plugin in catalog.plugins}
    for plugin_name in subdirectories(root / PLUGINS_DIR):
        plugin_dir = Path(PLUGINS_DIR) / plugin_name
        if plugin_name not in listed:
            report.add(plugin_dir, f"plugin directory {plugin_name!r} is not in {CATALOG_FILE}")
            continue
        for skill in subdirectories(root / plugin_dir / SKILLS_DIR):
            if skill not in listed[plugin_name]:
                report.add(
                    plugin_dir / SKILLS_DIR / skill,
                    f"skill directory {skill!r} is not listed under plugin "
                    f"{plugin_name!r} in {CATALOG_FILE}",
                )

    report.catalog = catalog
    return report


def to_json(value: object) -> str:
    """Pretty-prints JSON with two-space indents and a trailing newline."""
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def generate(catalog: Catalog) -> dict[str, str]:
    """Returns every generated file, keyed by path relative to the repository root.

    Output is deterministic: keys appear in a fixed order and plugins in catalog order.
    """

    def source(plugin: Plugin) -> str:
        return f"./{PLUGINS_DIR}/{plugin.name}"

    def with_keywords(entry: dict[str, Any], plugin: Plugin) -> dict[str, Any]:
        if plugin.keywords:
            entry["keywords"] = list(plugin.keywords)
        return entry

    owner = dict(catalog.owner)
    metadata = {"description": catalog.description}
    files: dict[str, str] = {}

    # Claude Code (and claude.ai org sync) and GitHub Copilot CLI share one format.
    claude = {
        "name": catalog.name,
        "owner": owner,
        "metadata": metadata,
        "plugins": [
            with_keywords(
                {
                    "name": plugin.name,
                    "source": source(plugin),
                    "description": plugin.description,
                    "version": plugin.version,
                    "author": owner,
                    "category": plugin.category,
                },
                plugin,
            )
            for plugin in catalog.plugins
        ],
    }
    files[".claude-plugin/marketplace.json"] = to_json(claude)
    files[".github/plugin/marketplace.json"] = to_json(claude)

    # OpenAI Codex: metadata comes from each plugin's Agent Plugins plugin.json.
    files[".agents/plugins/marketplace.json"] = to_json(
        {
            "name": catalog.name,
            "plugins": [
                {
                    "name": plugin.name,
                    "source": {"source": "local", "path": source(plugin)},
                    "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                    "category": plugin.category,
                }
                for plugin in catalog.plugins
            ],
        }
    )

    # Cursor: its published schema allows only name, source and description per entry.
    files[".cursor-plugin/marketplace.json"] = to_json(
        {
            "name": catalog.name,
            "owner": owner,
            "metadata": metadata,
            "plugins": [
                {
                    "name": plugin.name,
                    "source": source(plugin),
                    "description": plugin.description,
                }
                for plugin in catalog.plugins
            ],
        }
    )

    for plugin in catalog.plugins:
        plugin_dir = f"{PLUGINS_DIR}/{plugin.name}"
        # Agent Plugins 1.0 (read by Copilot CLI, Codex and Cursor). The schema is closed.
        files[f"{plugin_dir}/plugin.json"] = to_json(
            with_keywords(
                {
                    "$schema": AGENT_PLUGINS_SCHEMA,
                    "name": plugin.name,
                    "version": plugin.version,
                    "description": plugin.description,
                    "author": owner,
                },
                plugin,
            )
        )
        # Gemini CLI extension manifest.
        files[f"{plugin_dir}/gemini-extension.json"] = to_json(
            {
                "name": plugin.name,
                "version": plugin.version,
                "description": plugin.description,
            }
        )
    return dict(sorted(files.items()))


def out_of_date(root: Path, files: dict[str, str]) -> list[str]:
    """Lists generated files that are missing or differ from what is on disk."""
    stale = []
    for path, contents in files.items():
        target = root / path
        if not target.is_file() or target.read_bytes() != contents.encode("utf-8"):
            stale.append(path)
    return stale


def write_files(root: Path, files: dict[str, str]) -> list[str]:
    """Writes the files that are missing or changed, leaving current ones untouched."""
    written = out_of_date(root, files)
    for path in written:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(files[path].encode("utf-8"))
    return written


GENERATED_MARKER = ".generated"
GENERATED_NOTE = (
    "<!-- Generated by `tools/skills.py reference` from the repository. "
    "Don't edit it: change the source and rebuild. -->"
)


@dataclass(frozen=True)
class SiteContext:
    """Where the generated reference pages are served from, and the repo they describe."""

    repo: str
    url_prefix: str

    @property
    def repo_url(self) -> str:
        return f"https://github.com/{self.repo}"

    def link(self, *parts: str) -> str:
        """Returns the absolute URL of a generated page, with a trailing slash."""
        return "/".join([self.url_prefix.rstrip("/"), *parts]) + "/"


def plain(text: str) -> str:
    """Decodes HTML entities written into a source file and collapses whitespace."""
    return " ".join(html.unescape(text).split())


def md_text(text: str) -> str:
    """Returns `text` as one line of Markdown prose, with HTML special characters escaped."""
    return html.escape(plain(text), quote=False)


def page(title: str, description: str, body: str, order: int | None = None) -> str:
    """Returns a Starlight Markdown page with frontmatter and the generated-file note."""
    front = [
        "---",
        f"title: {json.dumps(title, ensure_ascii=False)}",
        f"description: {json.dumps(plain(description), ensure_ascii=False)}",
    ]
    if order is not None:
        front += ["sidebar:", f"  order: {order}"]
    front.append("---")
    return "\n".join([*front, "", GENERATED_NOTE, "", body.strip(), ""])


def read_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    """Returns a Markdown file's YAML frontmatter and body."""
    parts = split_frontmatter(path.read_text(encoding="utf-8"))
    if isinstance(parts, str):
        raise ValueError(f"{path}: {parts}")
    front = yaml.safe_load(parts[0])
    if not isinstance(front, dict):
        raise ValueError(f"{path}: frontmatter must be a YAML mapping")
    return front, parts[1]


def requires_lines(
    requirements: Sequence[Requirement],
    catalog: Catalog,
    ctx: SiteContext,
    suffix: str = "",
) -> list[str]:
    """Returns one Markdown bullet per requirement, linking the dependencies page."""
    names = {dependency.id: dependency.name for dependency in catalog.dependencies}
    return [
        f"- [{md_text(names[req.id])}]({ctx.link(DEPENDENCIES_PAGE)}#{req.id}), "
        f"{'optional' if req.optional else 'required'}: {md_text(req.purpose)}{suffix}"
        for req in requirements
    ]


def skill_page(
    plugin: Plugin,
    skill: str,
    front: dict[str, Any],
    catalog: Catalog,
    ctx: SiteContext,
    order: int,
) -> str:
    """Returns the reference page for one skill."""
    source = f"{PLUGINS_DIR}/{plugin.name}/{SKILLS_DIR}/{skill}/{SKILL_FILE}"
    description = str(front["description"])
    body = [
        f"> {md_text(description)}",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Plugin | [{plugin.name}]({ctx.link('plugins', plugin.name)}) |",
        f"| Invoke as | `{plugin.name}:{skill}` |",
        f"| Source | [`{source}`]({ctx.repo_url}/blob/main/{source}) |",
    ]
    settings = [
        f"- `{key}`: `{json.dumps(front[key], ensure_ascii=False)}`"
        for key in CLAUDE_CODE_KEYS
        if key in front
    ]
    if settings:
        body += ["", "## Claude Code settings", "", *settings]
    own = plugin.skill_requires.get(skill, ())
    own_ids = {req.id for req in own}
    inherited = [req for req in plugin.requires if req.id not in own_ids]
    if own or inherited:
        body += [
            "",
            "## Requires",
            "",
            *requires_lines(own, catalog, ctx),
            *requires_lines(inherited, catalog, ctx, " (from the plugin)"),
        ]
    return page(skill, description, "\n".join(body), order)


def demote_headings(markdown: str) -> str:
    """Moves every Markdown heading down one level, leaving fenced code alone.

    A fence closes only on a line of the opener's character, at least as long as the
    opener, with nothing after it, so other fence-like lines inside it stay code.
    """
    lines: list[str] = []
    opener: tuple[str, int] | None = None
    for line in markdown.splitlines():
        fence = re.match(r" {0,3}(`{3,}|~{3,})(.*)$", line)
        if opener is None:
            if fence and not (fence.group(1)[0] == "`" and "`" in fence.group(2)):
                opener = (fence.group(1)[0], len(fence.group(1)))
            elif re.match(r"#{1,5} ", line):
                line = "#" + line
        elif (
            fence
            and fence.group(1)[0] == opener[0]
            and len(fence.group(1)) >= opener[1]
            and not fence.group(2).strip()
        ):
            opener = None
        lines.append(line)
    return "\n".join(lines)


def install_rows(plugin: Plugin, catalog: Catalog, ctx: SiteContext) -> list[str]:
    """Returns a Markdown table of install commands for each client."""
    target = f"{plugin.name}@{catalog.name}"
    clone_dir = ctx.repo.split("/")[-1]
    return [
        "| Client | How |",
        "|---|---|",
        f"| Claude Code | `/plugin marketplace add {ctx.repo}`, then `/plugin install {target}` |",
        f"| GitHub Copilot CLI | `copilot plugin marketplace add {ctx.repo}`, then "
        f"`copilot plugin install {target}` |",
        f"| OpenAI Codex | `codex plugin marketplace add {ctx.repo}`, then install "
        f"`{plugin.name}` from `/plugins` |",
        f"| Gemini CLI | `git clone {ctx.repo_url}.git`, then "
        f"`gemini extensions install ./{clone_dir}/plugins/{plugin.name}` |",
    ]


def plugin_page(
    plugin: Plugin, catalog: Catalog, agents: list[str], ctx: SiteContext, order: int
) -> str:
    """Returns the reference page for one plugin."""
    facts = f"**Version** {plugin.version} · **Category** {plugin.category}"
    if plugin.keywords:
        facts += f" · **Keywords** {', '.join(plugin.keywords)}"
    body = [
        md_text(plugin.description),
        "",
        facts,
        "",
        "## Install",
        "",
        *install_rows(plugin, catalog, ctx),
        "",
    ]
    if plugin.requires:
        body += ["", "## Requires", "", *requires_lines(plugin.requires, catalog, ctx)]
    body += [
        "",
        "## Skills",
        "",
        *[f"- [{skill}]({ctx.link('skills', skill)})" for skill in plugin.skills],
    ]
    if agents:
        body += [
            "",
            "## Agents",
            "",
            *[f"- [{plugin.name}:{agent}]({ctx.link('agents', agent)})" for agent in agents],
        ]
    return page(plugin.name, plugin.description, "\n".join(body), order)


def agent_page(plugin: Plugin, path: Path, ctx: SiteContext, order: int) -> tuple[str, str]:
    """Returns an agent's name and its reference page."""
    front, rules = read_frontmatter(path)
    name = front.get("name", path.stem)
    problem = name_problem(name)
    if problem:
        raise ValueError(f"{path}: agent {problem}")
    name = str(name)
    description = str(front.get("description", ""))
    source = f"{PLUGINS_DIR}/{plugin.name}/{AGENTS_DIR}/{path.name}"
    body = [
        f"> {md_text(description)}",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Subagent type | `{plugin.name}:{name}` |",
        f"| Plugin | [{plugin.name}]({ctx.link('plugins', plugin.name)}) |",
    ]
    if "model" in front:
        body.append(f"| Model | `{front['model']}` |")
    body += [
        f"| Source | [`{source}`]({ctx.repo_url}/blob/main/{source}) |",
        "",
        "## Standing rules",
        "",
        demote_headings(rules.strip()),
    ]
    return name, page(name, description, "\n".join(body), order)


def needed_by_lines(dependency: Dependency, catalog: Catalog, ctx: SiteContext) -> list[str]:
    """Returns a bullet for each plugin and skill that requires `dependency`."""
    lines: list[str] = []

    def add(label: str, name: str, link: str, req: Requirement) -> None:
        state = "optional" if req.optional else "required"
        lines.append(f"  - {label} [{name}]({link}), {state}: {md_text(req.purpose)}")

    for plugin in catalog.plugins:
        for req in plugin.requires:
            if req.id == dependency.id:
                add("Plugin", plugin.name, ctx.link("plugins", plugin.name), req)
        for skill in plugin.skills:
            for req in plugin.skill_requires.get(skill, ()):
                if req.id == dependency.id:
                    add("Skill", skill, ctx.link("skills", skill), req)
    return lines


def dependencies_page(catalog: Catalog, ctx: SiteContext) -> str | None:
    """Returns the dependencies page, or None if the catalog declares no dependencies."""
    if not catalog.dependencies:
        return None
    body = [
        "These are the things the skills here rely on but this repository doesn't ship: "
        "other skill packs, MCP servers, command-line tools and services. Each entry says "
        "where to get it and which plugins and skills need it, as required or optional.",
    ]
    for kind, label in DEPENDENCY_KINDS.items():
        members = [d for d in catalog.dependencies if d.kind == kind]
        if not members:
            continue
        body += ["", f"## {label}"]
        for dependency in members:
            body += [
                "",
                f'<a id="{dependency.id}"></a>',
                f"### {md_text(dependency.name)}",
                "",
                md_text(dependency.description),
                "",
            ]
            if dependency.url:
                body.append(f"- **Link:** <{dependency.url}>")
            if dependency.install:
                body.append(f"- **Install:** {md_text(dependency.install)}")
            if dependency.note:
                body.append(f"- **Note:** {md_text(dependency.note)}")
            body += ["- **Needed by:**", *needed_by_lines(dependency, catalog, ctx)]
    return page(
        "Dependencies",
        "What the skills need that this repository doesn't ship, where to get it, and "
        "which plugins and skills need it.",
        "\n".join(body),
    )


def glossary_page(root: Path) -> str | None:
    """Returns GLOSSARY.md as a page, without its own title heading, if it exists."""
    path = root / "GLOSSARY.md"
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return page(
        "Glossary",
        "The personal names and conventions these skills use, and how to adapt them.",
        "\n".join(lines),
    )


def reference_pages(root: Path, catalog: Catalog, ctx: SiteContext) -> dict[str, str]:
    """Returns every reference page, keyed by path relative to the output directory."""
    pages: dict[str, str] = {}
    skill_order = 0
    agent_order = 0
    for index, plugin in enumerate(catalog.plugins, start=1):
        agents_dir = root / PLUGINS_DIR / plugin.name / AGENTS_DIR
        agent_names: list[str] = []
        for path in sorted(agents_dir.glob("*.md")) if agents_dir.is_dir() else []:
            agent_order += 1
            name, text = agent_page(plugin, path, ctx, agent_order)
            key = f"agents/{name}.md"
            if key in pages:
                raise ValueError(f"agent {name!r} is defined in more than one plugin")
            pages[key] = text
            agent_names.append(name)
        pages[f"plugins/{plugin.name}.md"] = plugin_page(plugin, catalog, agent_names, ctx, index)
        for skill in plugin.skills:
            skill_order += 1
            front, _ = read_frontmatter(
                root / PLUGINS_DIR / plugin.name / SKILLS_DIR / skill / SKILL_FILE
            )
            pages[f"skills/{skill}.md"] = skill_page(
                plugin, skill, front, catalog, ctx, skill_order
            )
    dependencies = dependencies_page(catalog, ctx)
    if dependencies is not None:
        pages[f"{DEPENDENCIES_PAGE}.md"] = dependencies
    glossary = glossary_page(root)
    if glossary is not None:
        pages["glossary.md"] = glossary
    return dict(sorted(pages.items()))


def write_reference(out: Path, pages: dict[str, str]) -> None:
    """Replaces `out` with exactly `pages`, if `out` is missing or was written by this tool.

    Every page path must stay inside `out`; this is checked before anything is deleted.
    """
    base = out.resolve()
    for rel in pages:
        if not (base / rel).resolve().is_relative_to(base) or Path(rel).is_absolute():
            raise ValueError(f"page path {rel!r} is outside {out}; refusing to write")
    if out.exists():
        foreign = not out.is_dir() or (
            any(out.iterdir()) and not (out / GENERATED_MARKER).is_file()
        )
        if foreign:
            raise ValueError(
                f"{out} has files this tool did not write (no {GENERATED_MARKER} marker); "
                "refusing to replace it"
            )
        shutil.rmtree(out)
    out.mkdir(parents=True)
    # The marker goes first, so a failed page write still leaves a directory a retry may replace.
    (out / GENERATED_MARKER).write_text(
        "Written by tools/skills.py reference. Safe to delete.\n", encoding="utf-8"
    )
    for rel, text in pages.items():
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--root", type=Path, default=Path("."), help="repository root")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate", help="check the catalog and every skill")
    gen = commands.add_parser("generate", help="regenerate the vendor manifests")
    gen.add_argument(
        "--check", action="store_true", help="fail if a generated file is out of date"
    )
    ref = commands.add_parser("reference", help="write the documentation site's reference pages")
    ref.add_argument("--out", type=Path, required=True, help="directory to replace")
    ref.add_argument("--repo", required=True, help="GitHub repository, as owner/name")
    ref.add_argument("--url-prefix", required=True, help="URL path the pages are served under")
    args = parser.parse_args(argv)
    root: Path = args.root

    report = validate(root)
    for issue in report.issues:
        print(issue, file=sys.stderr)
    if report.has_errors or report.catalog is None:
        print("validation failed", file=sys.stderr)
        return 1

    if args.command == "validate":
        skills = sum(len(plugin.skills) for plugin in report.catalog.plugins)
        print(f"ok: {len(report.catalog.plugins)} plugins, {skills} skills")
        return 0

    if args.command == "reference":
        try:
            pages = reference_pages(root, report.catalog, SiteContext(args.repo, args.url_prefix))
            write_reference(args.out, pages)
        except (ValueError, OSError, yaml.YAMLError) as error:
            print(f"error: {error}", file=sys.stderr)
            return 1
        print(f"wrote {len(pages)} reference pages to {args.out}")
        return 0

    files = generate(report.catalog)
    if args.check:
        stale = out_of_date(root, files)
        for path in stale:
            print(f"out of date: {path}", file=sys.stderr)
        if stale:
            print("run `just generate` and commit the result", file=sys.stderr)
            return 1
        print(f"ok: {len(files)} generated files are current")
        return 0
    written = write_files(root, files)
    for path in written:
        print(f"wrote {path}")
    print(f"{len(written)} of {len(files)} generated files changed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
