#!/usr/bin/env python3
"""Break down local Claude Code token usage from session transcripts.

Claude Code writes one JSONL transcript per session under
``~/.claude/projects/<encoded-cwd>/<session-id>.jsonl``, and one per subagent under
``<session-id>/subagents/agent-*.jsonl`` with an ``agent-*.meta.json`` beside it.
Every assistant line carries ``message.model`` and ``message.usage``.

Costs are weighted by relative API price, because the plan limit's exact accounting
isn't published: input 1, output 5, cache read 0.1, cache write 1.25 (5-minute) or
2 (1-hour), times a model weight (Opus 5, Sonnet 3, Haiku 1). Shares are approximate.

Usage:
    usage_report.py summary [--days 7] [--top 10] [--root DIR]
    usage_report.py session <session-id-prefix>... [--days 7] [--root DIR]
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

TOKEN_WEIGHTS = {
    "input": 1.0,
    "output": 5.0,
    "cache_read": 0.1,
    "cache_write_5m": 1.25,
    "cache_write_1h": 2.0,
}
MODEL_WEIGHTS = (("opus", 5.0), ("sonnet", 3.0), ("haiku", 1.0))
DEFAULT_MODEL_WEIGHT = 3.0

# Words that, in the coordinator's text just before an Opus Agent call, count as a
# stated reason for choosing Opus.
OPUS_REASON_WORDS = (
    "lock", "transaction", "migration", "security", "auth", "schema",
    "concurren", "crypto", "permission", "escalat", "takeover", "take over",
    "trigger", "retry",
)


@dataclass(frozen=True)
class Call:
    """One deduplicated API call, from a main session or one of its subagents."""

    project: str
    session: str
    agent: str | None  # subagent file stem, or None for the main session
    agent_type: str | None
    model: str
    day: str
    input: int
    output: int
    cache_read: int
    cache_write_5m: int
    cache_write_1h: int

    @property
    def context(self) -> int:
        """Tokens of context this call read: cached plus newly written plus input."""
        return self.input + self.cache_read + self.cache_write_5m + self.cache_write_1h


def model_weight(model: str) -> float:
    """The relative price of a model family; unknown models count as Sonnet."""
    lower = model.lower()
    for name, weight in MODEL_WEIGHTS:
        if name in lower:
            return weight
    return DEFAULT_MODEL_WEIGHT


def cost_parts(call: Call) -> dict[str, float]:
    """The weighted cost of a call, split by token type."""
    w = model_weight(call.model)
    return {
        "input": call.input * TOKEN_WEIGHTS["input"] * w,
        "output": call.output * TOKEN_WEIGHTS["output"] * w,
        "cache read": call.cache_read * TOKEN_WEIGHTS["cache_read"] * w,
        "cache write": (call.cache_write_5m * TOKEN_WEIGHTS["cache_write_5m"]
                        + call.cache_write_1h * TOKEN_WEIGHTS["cache_write_1h"]) * w,
    }


def cost(call: Call) -> float:
    """The weighted cost of a call."""
    return sum(cost_parts(call).values())


def project_name(dirname: str, home: Path | None = None) -> str:
    """A readable project name from an encoded transcript directory name.

    The directory encodes the session's working directory with ``/`` and ``.`` as
    ``-``. Strip the home directory and fold worktrees (``--worktrees-...``) into
    their repository.
    """
    home_enc = re.sub(r"[/.]", "-", str(home if home is not None else Path.home()))
    name = dirname
    if name == home_enc:
        return "~"
    if name.startswith(home_enc + "-"):
        name = name[len(home_enc) + 1:]
    name = re.sub(r"--worktrees-.*$", "", name)
    return name or "~"


def _usage_int(usage: dict[str, Any], key: str) -> int:
    value = usage.get(key, 0)
    return value if isinstance(value, int) else 0


def _parse_call(line: str, since: dt.datetime) -> tuple[tuple[str, str], dict[str, Any]] | None:
    if '"usage"' not in line:
        return None
    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(record, dict) or record.get("type") != "assistant":
        return None
    message = record.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("usage"), dict):
        return None
    stamp = record.get("timestamp")
    if not isinstance(stamp, str):
        return None
    try:
        when = dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    if when < since:
        return None
    key = (str(message.get("id")), str(record.get("requestId")))
    return key, {"message": message, "when": when}


def _agent_type(agent_file: Path) -> str | None:
    meta = agent_file.with_name(agent_file.stem + ".meta.json")
    try:
        data = json.loads(meta.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(data, dict):
        value = data.get("agentType")
        return value if isinstance(value, str) else None
    return None


def transcript_files(root: Path, since: dt.datetime) -> Iterator[Path]:
    """Every transcript under ``root`` modified since ``since``."""
    cutoff = since.timestamp()
    for path in sorted(root.glob("**/*.jsonl")):
        try:
            if path.stat().st_mtime >= cutoff:
                yield path
        except OSError:
            continue


def iter_calls(root: Path, since: dt.datetime, home: Path | None = None) -> Iterator[Call]:
    """Every API call since ``since``, deduplicated on (message id, request id)."""
    seen: set[tuple[str, str]] = set()
    for path in transcript_files(root, since):
        rel = path.relative_to(root).parts
        if len(rel) < 2:
            continue
        project = project_name(rel[0], home)
        is_agent = "subagents" in rel
        session = rel[1] if is_agent else path.stem
        agent = path.stem if is_agent else None
        agent_type = _agent_type(path) if is_agent else None
        try:
            lines = path.read_text(errors="ignore").splitlines()
        except OSError:
            continue
        for line in lines:
            parsed = _parse_call(line, since)
            if parsed is None:
                continue
            key, data = parsed
            if key in seen:
                continue
            seen.add(key)
            message: dict[str, Any] = data["message"]
            usage: dict[str, Any] = message["usage"]
            creation = usage.get("cache_creation")
            cw1 = cw5 = 0
            if isinstance(creation, dict):
                cw1 = _usage_int(creation, "ephemeral_1h_input_tokens")
                cw5 = _usage_int(creation, "ephemeral_5m_input_tokens")
            if cw1 + cw5 == 0:
                cw5 = _usage_int(usage, "cache_creation_input_tokens")
            when: dt.datetime = data["when"]
            yield Call(
                project=project,
                session=session,
                agent=agent,
                agent_type=agent_type,
                model=str(message.get("model", "?")),
                day=when.strftime("%a %Y-%m-%d"),
                input=_usage_int(usage, "input_tokens"),
                output=_usage_int(usage, "output_tokens"),
                cache_read=_usage_int(usage, "cache_read_input_tokens"),
                cache_write_5m=cw5,
                cache_write_1h=cw1,
            )


@dataclass
class Bucket:
    """Totals for one row of a breakdown."""

    cost: float = 0.0
    calls: int = 0
    output: int = 0
    cache_read: int = 0
    sessions: set[str] = field(default_factory=set)

    def add(self, call: Call) -> None:
        self.cost += cost(call)
        self.calls += 1
        self.output += call.output
        self.cache_read += call.cache_read
        self.sessions.add(call.session)


def breakdown(calls: Iterable[Call], key: Any) -> dict[str, Bucket]:
    """Group calls into buckets by ``key(call)``."""
    out: dict[str, Bucket] = collections.defaultdict(Bucket)
    for call in calls:
        out[str(key(call))].add(call)
    return dict(out)


def _m(n: float) -> str:
    return f"{n / 1e6:.1f}M"


def print_table(title: str, buckets: dict[str, Bucket], total: float, top: int,
                out: Any = sys.stdout) -> None:
    """Print a breakdown, largest share first."""
    print(f"\n== {title} ==", file=out)
    print(f"{'key':44} {'share':>6} {'calls':>6} {'sess':>5} {'output':>8} {'cacheRd':>9}", file=out)
    for name, b in sorted(buckets.items(), key=lambda kv: -kv[1].cost)[:top]:
        share = 100 * b.cost / total if total else 0.0
        print(f"{name[:44]:44} {share:5.1f}% {b.calls:6} {len(b.sessions):5} "
              f"{_m(b.output):>8} {_m(b.cache_read):>9}", file=out)


def _session_files(root: Path, prefix: str) -> list[Path]:
    return sorted(p for p in root.glob(f"*/{prefix}*.jsonl"))


def _first_prompt_and_skills(path: Path) -> tuple[str, list[str], list[int]]:
    prompt = ""
    skills: set[str] = set()
    contexts: list[int] = []
    try:
        lines = path.read_text(errors="ignore").splitlines()
    except OSError:
        return prompt, [], contexts
    for line in lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        if record.get("type") == "user" and not prompt:
            content = message.get("content")
            text = content if isinstance(content, str) else " ".join(
                str(part.get("text", "")) for part in content or [] if isinstance(part, dict))
            text = text.strip()
            if text and not text.startswith("<system") and not text.startswith("Caveat"):
                prompt = re.sub(r"\s+", " ", text)[:140]
        if record.get("type") == "assistant":
            for part in message.get("content") or []:
                if isinstance(part, dict) and part.get("type") == "tool_use" and part.get("name") == "Skill":
                    args = part.get("input")
                    if isinstance(args, dict):
                        skills.add(str(args.get("skill")))
            usage = message.get("usage")
            if isinstance(usage, dict):
                contexts.append(_usage_int(usage, "cache_read_input_tokens")
                                + _usage_int(usage, "cache_creation_input_tokens")
                                + _usage_int(usage, "input_tokens"))
    return prompt, sorted(skills), contexts


def summary(root: Path, days: int, top: int, out: Any = sys.stdout) -> None:
    """Print the whole-window breakdown."""
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    calls = list(iter_calls(root, since))
    if not calls:
        print(f"No calls in the last {days} days under {root}.", file=out)
        return
    total = sum(cost(c) for c in calls)
    parts: dict[str, float] = collections.defaultdict(float)
    for c in calls:
        for name, value in cost_parts(c).items():
            parts[name] += value
    print(f"Window: last {days} days. Calls: {len(calls)}. "
          f"Sessions: {len({c.session for c in calls})}.", file=out)
    print(f"Tokens: output {_m(sum(c.output for c in calls))}, cache read "
          f"{_m(sum(c.cache_read for c in calls))}, cache write "
          f"{_m(sum(c.cache_write_5m + c.cache_write_1h for c in calls))}, input "
          f"{_m(sum(c.input for c in calls))}.", file=out)
    print("\n== cost by token type ==", file=out)
    for name, value in sorted(parts.items(), key=lambda kv: -kv[1]):
        print(f"{name:12} {100 * value / total:5.1f}%", file=out)
    print_table("by model", breakdown(calls, lambda c: c.model), total, top, out)
    print_table("by day", breakdown(calls, lambda c: c.day), total, 31, out)
    print_table("by project", breakdown(calls, lambda c: c.project), total, top, out)
    print_table("main vs subagent", breakdown(
        calls, lambda c: "subagent" if c.agent else "main"), total, 2, out)
    print_table("subagents by type and model", breakdown(
        (c for c in calls if c.agent),
        lambda c: f"{c.agent_type or '?'} | {c.model}"), total, top, out)
    sessions = breakdown(calls, lambda c: f"{c.project} {c.session[:8]}")
    print(f"\n== top {top} sessions ==", file=out)
    for name, b in sorted(sessions.items(), key=lambda kv: -kv[1].cost)[:top]:
        project, prefix = name.rsplit(" ", 1)
        files = _session_files(root, prefix)
        prompt, skills, contexts = _first_prompt_and_skills(files[0]) if files else ("", [], [])
        agents = len(list(files[0].with_suffix("").glob("subagents/*.jsonl"))) if files else 0
        avg = sum(contexts) // max(len(contexts), 1)
        peak = max(contexts) if contexts else 0
        print(f"{100 * b.cost / total:5.1f}%  {project} {prefix}  subagents={agents} "
              f"main ctx avg/max={avg // 1000}k/{peak // 1000}k  skills={','.join(skills) or '-'}",
              file=out)
        if prompt:
            print(f"        {prompt}", file=out)


def _percentile(values: Sequence[int], pct: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(pct * len(ordered)))]


def stated_reason(text: str) -> list[str]:
    """The Opus-reason words found in ``text``."""
    lower = text.lower()
    return [w for w in OPUS_REASON_WORDS if w in lower]


def session_report(root: Path, prefix: str, days: int, out: Any = sys.stdout) -> None:
    """Print one session's breakdown: coordinator vs subagents, models, Opus choices."""
    files = _session_files(root, prefix)
    if not files:
        print(f"\n### {prefix}: no transcript found", file=out)
        return
    main_file = files[0]
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    calls = [c for c in iter_calls(root, since) if c.session == main_file.stem]
    total: float = sum((cost(c) for c in calls), 0.0) or 1.0
    main_calls = [c for c in calls if c.agent is None]
    contexts = [c.context for c in main_calls]
    tools: collections.Counter[str] = collections.Counter()
    agent_calls: collections.Counter[str] = collections.Counter()
    unexplained: list[str] = []
    opus_calls = 0
    last_text = ""
    for line in main_file.read_text(errors="ignore").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict) or record.get("type") != "assistant":
            continue
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        for part in message.get("content") or []:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "text":
                last_text = str(part.get("text", ""))
            if part.get("type") != "tool_use":
                continue
            name = str(part.get("name"))
            tools[name] += 1
            args = part.get("input")
            if name in ("Agent", "Task") and isinstance(args, dict):
                agent_type = str(args.get("subagent_type") or "-")
                model = str(args.get("model") or "default")
                agent_calls[f"{agent_type} | model={model}"] += 1
                if model == "opus":
                    # Only the coordinator's own words count. Briefs carry boilerplate
                    # (security, auth) that would make every call look justified.
                    description = str(args.get("description", ""))
                    if not stated_reason(last_text[-600:] + " " + description):
                        unexplained.append(description[:60])
                    opus_calls += 1
    main_cost = sum(cost(c) for c in main_calls)
    print(f"\n### {project_name(main_file.parent.name)} {main_file.stem[:8]}", file=out)
    print(f"coordinator {100 * main_cost / total:.0f}%, subagents {100 - 100 * main_cost / total:.0f}%; "
          f"coordinator turns {len(main_calls)}; context p50/p90/max "
          f"{_percentile(contexts, 0.5) // 1000}k/{_percentile(contexts, 0.9) // 1000}k/"
          f"{max(contexts, default=0) // 1000}k", file=out)
    print("coordinator tools: " + ", ".join(f"{n} {k}" for k, n in tools.most_common(8)), file=out)
    print("agent calls: " + (", ".join(f"{n}x {k}" for k, n in agent_calls.most_common()) or "none"),
          file=out)
    if opus_calls:
        print(f"Opus overrides: {opus_calls}, {len(unexplained)} with no stated reason in the "
              "coordinator's text just before the call" + (": " + "; ".join(unexplained) if unexplained else ""),
              file=out)
    per_agent: dict[str, list[Call]] = collections.defaultdict(list)
    for c in calls:
        if c.agent:
            per_agent[c.agent].append(c)
    groups: dict[str, list[tuple[float, int, int]]] = collections.defaultdict(list)
    for agent_list in per_agent.values():
        first = agent_list[0]
        groups[f"{first.agent_type or '?'} | {first.model}"].append(
            (sum(cost(c) for c in agent_list), len(agent_list), max(c.context for c in agent_list)))
    print("subagents (share, count, median turns, median peak context):", file=out)
    for name, rows in sorted(groups.items(), key=lambda kv: -sum(r[0] for r in kv[1])):
        share = 100 * sum(r[0] for r in rows) / total
        print(f"  {share:5.1f}%  n={len(rows):3}  turns~{statistics.median(r[1] for r in rows):.0f}  "
              f"peak~{statistics.median(r[2] for r in rows) / 1000:.0f}k  {name}", file=out)


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="Break down local Claude Code token usage.")
    parser.add_argument("--root", type=Path, default=Path.home() / ".claude" / "projects",
                        help="transcript directory (default: ~/.claude/projects)")
    parser.add_argument("--days", type=int, default=7, help="window in days (default 7)")
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("summary", help="whole-window breakdown")
    s.add_argument("--top", type=int, default=10)
    d = sub.add_parser("session", help="drill into sessions by id prefix")
    d.add_argument("prefixes", nargs="+")
    args = parser.parse_args(argv)
    root: Path = args.root
    if not root.is_dir():
        print(f"No transcript directory at {root}.", file=sys.stderr)
        return 1
    if args.command == "summary":
        summary(root, args.days, args.top)
    else:
        for prefix in args.prefixes:
            session_report(root, prefix, args.days)
    return 0


if __name__ == "__main__":
    sys.exit(main())
