"""
Publish must recover from a rejected push by rebasing onto origin/main.

Found 2026-09-02, live: a README commit pushed from another checkout at
19:09 IST made every publish for the rest of the session fail with
"fetch first". 42 artifact commits piled up locally, the public dashboard
sat 3.5 hours stale, and nothing surfaced it because the watchdog only kept
the last 4 lines of a completed cycle's output. The local commits only ever
touch artifacts/, so replaying them on top of the remote is conflict-free
unless someone else edited the artifacts, in which case the rebase must be
abandoned cleanly rather than left in progress for the next trading cycle
to trip over.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

import publish as P  # noqa: E402


class Run:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


class ScriptedGit:
    """Answers git calls from a script keyed on the first argument(s)."""

    def __init__(self, script: dict):
        self.script = script
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, *args, **kwargs):
        self.calls.append(args)
        key = args[0]
        if key == "push":
            n = sum(1 for c in self.calls if c[0] == "push")
            return self.script["push"][min(n, len(self.script["push"])) - 1]
        if key == "rebase" and len(args) > 1 and args[1] == "--abort":
            return Run()
        if key == "diff" and "--cached" in args:
            return Run(returncode=1)          # something is staged
        return self.script.get(key, Run())


REJECTED = Run(1, stderr="! [rejected] main -> main (fetch first)\nerror: failed to push")


def _artifact_repo(tmp_path, monkeypatch):
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts" / "decisions.jsonl").write_text("{}\n")
    monkeypatch.setattr(P, "REPO", tmp_path)
    monkeypatch.setattr(P, "PUBLISHABLE", ("artifacts/decisions.jsonl",))


def test_non_fast_forward_detection_covers_the_real_message():
    assert P._is_non_fast_forward(REJECTED.stderr)
    assert P._is_non_fast_forward("Updates were rejected (non-fast-forward)")
    assert not P._is_non_fast_forward("fatal: unable to access: Could not resolve host")


def test_rejected_push_is_recovered_by_rebasing_then_pushing_again(tmp_path, monkeypatch):
    _artifact_repo(tmp_path, monkeypatch)
    git = ScriptedGit({"push": [REJECTED, Run()], "fetch": Run(), "rebase": Run()})
    monkeypatch.setattr(P, "_git", git)

    res = P.publish()

    assert res.ok and res.action == "pushed"
    assert "after rebase" in res.detail
    ops = [c[0] for c in git.calls]
    assert ops.index("fetch") < ops.index("rebase") < len(ops) - 1
    assert ops.count("push") == 2
    assert ("rebase", "origin/main") in git.calls


def test_conflicting_rebase_is_aborted_and_reported_not_left_in_progress(tmp_path, monkeypatch):
    _artifact_repo(tmp_path, monkeypatch)
    git = ScriptedGit({"push": [REJECTED], "fetch": Run(),
                       "rebase": Run(1, stderr="CONFLICT (content): artifacts/decisions.jsonl")})
    monkeypatch.setattr(P, "_git", git)

    res = P.publish()

    assert not res.ok and res.action == "failed"
    assert "aborted" in res.detail
    assert ("rebase", "--abort") in git.calls
    assert [c[0] for c in git.calls].count("push") == 1


def test_unrelated_push_failure_does_not_trigger_a_rebase(tmp_path, monkeypatch):
    _artifact_repo(tmp_path, monkeypatch)
    dns = Run(1, stderr="fatal: unable to access 'https://github.com/': Could not resolve host")
    git = ScriptedGit({"push": [dns]})
    monkeypatch.setattr(P, "_git", git)

    res = P.publish()

    assert not res.ok and "push failed" in res.detail
    assert all(c[0] != "rebase" for c in git.calls)
