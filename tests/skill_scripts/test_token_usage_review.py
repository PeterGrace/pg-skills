"""Tests for the token-usage-review skill's usage_report.py."""

from __future__ import annotations

import datetime as dt
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any

SCRIPT = (Path(__file__).resolve().parents[2] / "plugins" / "usage-analysis" / "skills"
          / "token-usage-review" / "scripts" / "usage_report.py")


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("usage_report", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Dataclasses look their module up in sys.modules while the class is built.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ur = load()
NOW = dt.datetime.now(dt.timezone.utc)
HOME = Path("/home/tester")


def assistant(msg_id: str, model: str, when: dt.datetime, *, output: int = 10,
              cache_read: int = 1000, cache_1h: int = 100, content: list[Any] | None = None) -> str:
    return json.dumps({
        "type": "assistant",
        "requestId": "req-" + msg_id,
        "timestamp": when.isoformat().replace("+00:00", "Z"),
        "message": {
            "id": msg_id,
            "model": model,
            "content": content or [],
            "usage": {
                "input_tokens": 2,
                "output_tokens": output,
                "cache_read_input_tokens": cache_read,
                "cache_creation_input_tokens": cache_1h,
                "cache_creation": {"ephemeral_1h_input_tokens": cache_1h,
                                   "ephemeral_5m_input_tokens": 0},
            },
        },
    })


def user(text: str, when: dt.datetime) -> str:
    return json.dumps({"type": "user", "timestamp": when.isoformat(),
                       "message": {"content": text}})


class Fixture:
    """A fake ~/.claude/projects tree with one coordinator session and two subagents."""

    def __init__(self, root: Path) -> None:
        self.root = root
        project = root / "-home-tester-repos-app--worktrees-app-feature"
        project.mkdir(parents=True)
        recent = NOW - dt.timedelta(hours=1)
        old = NOW - dt.timedelta(days=30)
        agent_call = {"type": "tool_use", "name": "Agent", "input": {
            "subagent_type": "issue-implementer", "model": "opus",
            "description": "Implement #1", "prompt": "Shared machine: security rules apply."}}
        reasoned = {"type": "tool_use", "name": "Agent", "input": {
            "subagent_type": "issue-implementer", "model": "opus",
            "description": "Implement #2"}}
        (project / "sess-1.jsonl").write_text("\n".join([
            user("run the epic", recent),
            assistant("m1", "claude-opus-5-5", recent, content=[
                {"type": "text", "text": "Starting the next issue."}, agent_call]),
            assistant("m1", "claude-opus-5-5", recent),  # duplicate line: counted once
            assistant("m2", "claude-opus-5-5", recent, content=[
                {"type": "text", "text": "This changes lock order, so Opus."}, reasoned]),
            assistant("m0", "claude-opus-5-5", old),  # outside the window
            "not json",
        ]) + "\n")
        subagents = project / "sess-1" / "subagents"
        subagents.mkdir(parents=True)
        (subagents / "agent-a.jsonl").write_text(
            assistant("s1", "claude-sonnet-5-5", recent, output=100) + "\n")
        (subagents / "agent-a.meta.json").write_text(json.dumps({"agentType": "issue-implementer"}))
        (subagents / "agent-b.jsonl").write_text(
            assistant("s2", "claude-sonnet-5-5", recent) + "\n")


class UsageReportTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        Fixture(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def calls(self) -> list[Any]:
        return list(ur.iter_calls(self.root, NOW - dt.timedelta(days=7), HOME))

    def test_dedupes_and_applies_the_window(self) -> None:
        ids = sorted((c.agent or "main", c.output) for c in self.calls())
        self.assertEqual(ids, [("agent-a", 100), ("agent-b", 10), ("main", 10), ("main", 10)])

    def test_attributes_subagents_and_their_type(self) -> None:
        by_agent = {c.agent: c for c in self.calls() if c.agent}
        self.assertEqual(by_agent["agent-a"].agent_type, "issue-implementer")
        self.assertIsNone(by_agent["agent-b"].agent_type)
        self.assertTrue(all(c.session == "sess-1" for c in self.calls()))

    def test_folds_worktrees_and_strips_home(self) -> None:
        self.assertEqual({c.project for c in self.calls()}, {"repos-app"})
        self.assertEqual(ur.project_name("-home-tester", HOME), "~")
        self.assertEqual(ur.project_name("-var-cache", HOME), "-var-cache")

    def test_cost_weights(self) -> None:
        call = ur.Call(project="p", session="s", agent=None, agent_type=None,
                       model="claude-opus-5-5", day="d", input=10, output=10,
                       cache_read=100, cache_write_5m=0, cache_write_1h=10)
        # (10*1 + 10*5 + 100*0.1 + 10*2) * 5 for Opus
        self.assertAlmostEqual(ur.cost(call), 450.0)
        self.assertEqual(ur.model_weight("claude-haiku-5-5"), 1.0)
        self.assertEqual(ur.model_weight("something-new"), 3.0)
        self.assertEqual(call.context, 120)

    def test_stated_reason_ignores_plain_text(self) -> None:
        self.assertEqual(ur.stated_reason("Starting the next issue."), [])
        self.assertIn("lock", ur.stated_reason("This changes lock order"))

    def test_summary_runs(self) -> None:
        out = io.StringIO()
        ur.summary(self.root, 7, 5, out)
        text = out.getvalue()
        self.assertIn("Calls: 4.", text)
        self.assertIn("issue-implementer | claude-sonnet-5-5", text)
        self.assertIn("run the epic", text)

    def test_session_report_counts_unexplained_opus(self) -> None:
        out = io.StringIO()
        ur.session_report(self.root, "sess-1", 7, out)
        text = out.getvalue()
        # The brief's "security" must not count as a reason; the lock-order text does.
        self.assertIn("Opus overrides: 2, 1 with no stated reason", text)
        self.assertIn("Implement #1", text)
        self.assertNotIn("Implement #2", text.split("Opus overrides")[1].splitlines()[0])

    def test_missing_root(self) -> None:
        self.assertEqual(ur.main(["--root", str(self.root / "nope"), "summary"]), 1)


if __name__ == "__main__":
    unittest.main()
