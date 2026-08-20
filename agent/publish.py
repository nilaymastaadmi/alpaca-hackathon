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
# state.json and positions.json are gitignored: they hold live operational state,
# not the decision record, and republishing them adds nothing a judge can use.
PUBLISHABLE = ("artifacts/decisions.jsonl", "artifacts/merkle_root.json")


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
