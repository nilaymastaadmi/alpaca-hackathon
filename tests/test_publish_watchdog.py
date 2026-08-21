"""
Tests for artifact publishing and the watchdog.

Two failures these exist to prevent, both of which would only surface during the
live window when nobody is watching:

  1. An automated pusher publishing something nobody meant to publish. It runs
     unattended every cycle for five days, so "it only stages artifacts" has to
     be a tested property, not a comment.
  2. The watchdog failing to kill a hung cycle. propdesk lost 11.5h and 4.8h of
     a live process to a sleep-hung HTTP call. A supervisor that cannot kill is
     worse than none, because it looks like protection.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

AGENT_DIR = Path(__file__).resolve().parent.parent / "agent"
sys.path.insert(0, str(AGENT_DIR))

import publish as P  # noqa: E402
import watchdog as W  # noqa: E402


# --- publishing scope: only artifacts, ever -------------------------------

def test_publishable_list_is_narrow_and_explicit():
    """
    The allowlist is the safety property. If someone widens it to a glob or a
    directory, this test should be the thing that objects.
    """
    assert set(P.PUBLISHABLE) == {
        "artifacts/decisions.jsonl",
        "artifacts/merkle_root.json",
        # Added after the audit found the deployed dashboard rendering "Flat.
        # No open structures." while the agent held five live condors.
        "artifacts/positions.json",
    }
    for path in P.PUBLISHABLE:
        assert path.startswith("artifacts/"), "nothing outside artifacts/ may publish"


def test_publishable_excludes_live_operational_state():
    """
    state.json and positions.json are gitignored on purpose: they hold live
    operational state rather than the decision record.
    """
    joined = " ".join(P.PUBLISHABLE)
    # state.json is session bookkeeping and stays unpublished. positions.json IS
    # published: the dashboard reads it, and a dashboard claiming "flat" while
    # five condors are open is worse than no dashboard.
    assert "artifacts/state.json" not in joined
    assert "watchdog.json" not in joined


def test_env_is_never_publishable():
    assert not any(".env" in p for p in P.PUBLISHABLE)


def test_publish_reports_rather_than_raises_on_a_bad_repo(monkeypatch, tmp_path):
    """
    A git failure must not propagate into the trading loop. The agent has real
    positions to manage and a broken push is not a reason to stop.
    """
    monkeypatch.setattr(P, "REPO", tmp_path)          # not a git repo
    monkeypatch.setattr(P, "PUBLISHABLE", ("artifacts/decisions.jsonl",))
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts" / "decisions.jsonl").write_text("{}\n")
    res = P.publish(push=False)
    assert res.ok is False
    assert res.action == "failed"
    assert isinstance(res.detail, str)


def test_publish_is_a_noop_when_no_artifacts_exist(monkeypatch, tmp_path):
    monkeypatch.setattr(P, "REPO", tmp_path)
    monkeypatch.setattr(P, "PUBLISHABLE", ("artifacts/decisions.jsonl",))
    res = P.publish(push=False)
    assert res.ok is True
    assert res.action == "nothing_to_do"


def test_publish_result_serialises_for_the_artifact_log():
    d = P.PublishResult(True, "pushed", "x" * 500).to_dict()
    assert d["ok"] is True
    assert len(d["detail"]) <= 300


def test_staged_files_are_safe_detects_unsafe_staging(monkeypatch):
    """A file outside the allowlist being staged must be reported, not ignored."""
    class FakeRun:
        stdout = "artifacts/decisions.jsonl\n.env\nagent/config.py\n"
    monkeypatch.setattr(P, "_git", lambda *a, **k: FakeRun())
    ok, unsafe = P.staged_files_are_safe()
    assert ok is False
    assert ".env" in unsafe
    assert "agent/config.py" in unsafe


def test_staged_files_are_safe_passes_on_allowlisted_only(monkeypatch):
    class FakeRun:
        stdout = "artifacts/decisions.jsonl\nartifacts/merkle_root.json\n"
    monkeypatch.setattr(P, "_git", lambda *a, **k: FakeRun())
    ok, unsafe = P.staged_files_are_safe()
    assert ok is True and unsafe == []


# --- watchdog: it must actually kill --------------------------------------

def _spawn(seconds: float) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-c", f"import time; time.sleep({seconds})"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def test_kill_verified_reports_already_exited():
    p = _spawn(0.01)
    p.wait(timeout=10)
    assert W.kill_verified(p) == "already_exited"


def test_kill_verified_actually_terminates_a_running_process():
    """
    THE test. A hung cycle must genuinely die, and the process must be confirmed
    gone rather than assumed. propdesk's pkill reported success while workers
    stayed alive.
    """
    p = _spawn(120)
    assert p.poll() is None, "process should be running before the kill"
    disposition = W.kill_verified(p, grace=10.0)
    assert disposition in ("terminated", "killed")
    assert p.poll() is not None, "process must actually be gone after kill_verified"


def test_kill_is_verified_not_assumed():
    p = _spawn(120)
    W.kill_verified(p, grace=10.0)
    # A second call on the now-dead process must recognise it, not hang.
    assert W.kill_verified(p) == "already_exited"


# --- watchdog configuration invariants ------------------------------------

def test_timeout_is_shorter_than_interval_by_default():
    """
    Otherwise a hung cycle is still being killed when the next should start and
    cycles pile up on each other.
    """
    assert W.DEFAULT_TIMEOUT < W.DEFAULT_INTERVAL


def test_defaults_leave_headroom_for_a_slow_but_healthy_cycle():
    """
    A healthy cycle makes 10 to 25 MCP calls at a measured 246ms round trip, so
    roughly 3 to 8 seconds plus chain pagination. The timeout must be far above
    that or the watchdog kills working cycles.
    """
    assert W.DEFAULT_TIMEOUT >= 120


def test_agent_entrypoint_exists():
    assert W.AGENT.exists(), "watchdog points at a missing agent.py"


def test_heartbeat_path_is_inside_artifacts():
    assert "artifacts" in str(W.HEARTBEAT)


def test_write_heartbeat_roundtrips(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(W, "HEARTBEAT", tmp_path / "watchdog.json")
    W.write_heartbeat({"alive": True, "stats": {"cycles": 3}})
    data = json.loads((tmp_path / "watchdog.json").read_text())
    assert data["alive"] is True
    assert data["stats"]["cycles"] == 3
    assert "updated_at" in data, "a heartbeat without a timestamp proves nothing"


def test_max_consecutive_failures_is_set():
    assert W.MAX_CONSECUTIVE_FAILURES >= 3
