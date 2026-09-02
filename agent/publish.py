"""
Publish artifacts to the repo so the deployed dashboard is not stale.

The dashboard renders whatever is COMMITTED, not whatever is on this laptop.
Without this, a judge opening the Application URL on 3 September sees decisions
dated 20 August, on a page whose entire pitch is "here is what the agent
decided". That would undercut the strongest part of the submission.

Three constraints, all deliberate:

  1. **Only `artifacts/` is ever staged.** Never code, never config, never
     anything else the working tree happens to be holding. An automated pusher
     that does `git add -A` will eventually publish something nobody meant to.
  2. **It can never break the trading cycle.** Every failure is caught and
     returned as a status. A git problem must not stop the agent from managing
     real positions.
  3. **It is opt-in.** Publishing pushes to a remote, so it runs only when
     `--publish` is passed, not silently on every local run.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = REPO / "artifacts"

# Exactly what may be published. Anything not on this list is never staged.
# state.json stays gitignored: it holds session bookkeeping, not the decision
# record. positions.json IS published, because the dashboard renders it and a
# dashboard claiming "flat" while the agent holds five condors is worse than
# no dashboard.
PUBLISHABLE = (
    "artifacts/decisions.jsonl",
    "artifacts/merkle_root.json",
    # Added 2026-08-20. Without it the DEPLOYED dashboard rendered "Flat.
    # No open structures." while the agent held five live condors, because
    # dashboard/app.py reads this file and it was gitignored. It holds
    # strikes, expiries and sizes, no secrets.
    "artifacts/positions.json",
    # Added 2026-09-02. Counts and latest verdicts from the D3 shadow
    # comparison (T4/T6/T7 dry-run agents), written by compare_report.py.
    # The per-candidate logs stay gitignored; this holds no orders.
    "artifacts/compare_summary.json",
)


@dataclass
class PublishResult:
    ok: bool
    action: str          # "pushed" | "nothing_to_do" | "failed"
    detail: str = ""

    def to_dict(self) -> dict:
        return {"ok": self.ok, "action": self.action, "detail": self.detail[:300]}


def _git(*args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, timeout=timeout,
    )


def _is_non_fast_forward(stderr: str) -> bool:
    s = (stderr or "").lower()
    return "fetch first" in s or "non-fast-forward" in s or "[rejected]" in s


def _rebase_onto_remote() -> PublishResult:
    """
    Replay the local artifact commits on top of origin/main. Never leaves a
    rebase in progress: a conflict aborts and is reported, so the trading
    loop's next cycle finds a normal working tree.
    """
    fetched = _git("fetch", "origin", timeout=120)
    if fetched.returncode != 0:
        return PublishResult(False, "failed",
                             f"push rejected and fetch failed: "
                             f"{fetched.stderr.strip()[:160]}")
    rebased = _git("rebase", "origin/main", timeout=120)
    if rebased.returncode != 0:
        _git("rebase", "--abort")
        return PublishResult(False, "failed",
                             f"push rejected; rebase onto origin/main "
                             f"conflicted and was aborted: "
                             f"{(rebased.stderr or rebased.stdout).strip()[:160]}")
    return PublishResult(True, "rebased", "replayed local commits onto origin/main")


def publish(note: str = "", push: bool = True) -> PublishResult:
    """
    Stage, commit and push the artifact files. Safe to call every cycle.

    Returns a status rather than raising, because the caller is a live trading
    loop and a failed push is not a reason to stop managing positions.
    """
    try:
        existing = [p for p in PUBLISHABLE if (REPO / p).exists()]
        if not existing:
            return PublishResult(True, "nothing_to_do", "no artifact files yet")

        add = _git("add", "--", *existing)
        if add.returncode != 0:
            return PublishResult(False, "failed", f"git add: {add.stderr.strip()}")

        # Nothing staged means nothing changed since the last publish.
        if _git("diff", "--cached", "--quiet", "--", *existing).returncode == 0:
            return PublishResult(True, "nothing_to_do", "artifacts unchanged")

        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        msg = f"Agent artifacts {stamp}"
        if note:
            msg += f"\n\n{note}"

        commit = _git("commit", "-m", msg)
        if commit.returncode != 0:
            return PublishResult(False, "failed", f"git commit: {commit.stderr.strip()}")

        if not push:
            return PublishResult(True, "committed", "local commit only, push skipped")

        pushed = _git("push", "origin", "HEAD", timeout=180)
        if pushed.returncode != 0 and _is_non_fast_forward(pushed.stderr):
            # 2026-09-02: a README commit pushed from another checkout at
            # 19:09 IST made every publish for the rest of the session fail
            # this way, 42 cycles, and the public dashboard sat 3.5 hours
            # stale while the artifact commits piled up locally. The local
            # commits only ever touch artifacts/, so replaying them on top
            # of the remote is conflict-free unless someone else edited the
            # artifacts, in which case the rebase is abandoned and reported.
            recovered = _rebase_onto_remote()
            if recovered.ok:
                pushed = _git("push", "origin", "HEAD", timeout=180)
                if pushed.returncode == 0:
                    return PublishResult(True, "pushed",
                                         f"{msg.splitlines()[0]} (after rebase "
                                         f"onto origin/main)")
            else:
                return recovered
        if pushed.returncode != 0:
            # Committed locally but not pushed. Recoverable, and the next cycle
            # will carry both commits, so this is a warning rather than a loss.
            return PublishResult(False, "failed",
                                 f"committed locally but push failed: "
                                 f"{pushed.stderr.strip()[:200]}")
        return PublishResult(True, "pushed", msg.splitlines()[0])

    except subprocess.TimeoutExpired:
        return PublishResult(False, "failed", "git timed out")
    except Exception as exc:                       # noqa: BLE001
        return PublishResult(False, "failed", f"{type(exc).__name__}: {exc}"[:200])


def staged_files_are_safe() -> tuple[bool, list[str]]:
    """
    Guard used by tests: confirm nothing outside PUBLISHABLE is staged.

    The failure this prevents is an automated pusher quietly publishing a file
    somebody left in the working tree.
    """
    res = _git("diff", "--cached", "--name-only")
    staged = [f for f in res.stdout.splitlines() if f.strip()]
    unsafe = [f for f in staged if f not in PUBLISHABLE]
    return (not unsafe), unsafe


if __name__ == "__main__":
    import sys
    r = publish(push="--no-push" not in sys.argv)
    print(f"{r.action}: {r.detail}")
    sys.exit(0 if r.ok else 1)
