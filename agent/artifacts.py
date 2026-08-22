"""
Append-only decision log with independent verifiability.

Every decision the agent makes, INCLUDING REFUSALS, is written as a structured
artifact carrying the inputs that produced it. The artifact set is then covered
by a SHA-256 Merkle tree so anyone can recompute the root hash themselves and
confirm nothing was edited after the fact.

Why this exists rather than a plain log file: a log is a claim. A Merkle root
published before the outcome is known, and recomputable by a third party, is
evidence. The judge does not have to trust the operator, which is the whole
point when the operator has an incentive to look good.

Verify with:  python agent/artifacts.py verify
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ARTIFACT_DIR = Path(__file__).resolve().parent.parent / "artifacts"
LOG_PATH = ARTIFACT_DIR / "decisions.jsonl"
ROOT_PATH = ARTIFACT_DIR / "merkle_root.json"


def canonical(obj: Any) -> bytes:
    """
    Deterministic serialisation. Key order and separators are pinned because a
    Merkle root over non-canonical JSON is not reproducible, which would make
    the whole exercise theatre.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str).encode("utf-8")


def leaf_hash(record: dict) -> str:
    # Domain-separated leaves. Without the 0x00 prefix an attacker could pass an
    # internal node off as a leaf (the classic second-preimage attack on Merkle
    # trees). Cheap to prevent, embarrassing to explain afterwards.
    return hashlib.sha256(b"\x00" + canonical(record)).hexdigest()


def _pair_hash(a: str, b: str) -> str:
    return hashlib.sha256(b"\x01" + bytes.fromhex(a) + bytes.fromhex(b)).hexdigest()


def merkle_root(leaves: list[str]) -> str:
    if not leaves:
        return hashlib.sha256(b"\x02empty").hexdigest()
    level = list(leaves)
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            if i + 1 < len(level):
                nxt.append(_pair_hash(level[i], level[i + 1]))
            else:
                # Odd node promotes unchanged rather than duplicating itself,
                # which avoids the CVE-2012-2459 duplicate-leaf ambiguity.
                nxt.append(level[i])
        level = nxt
    return level[0]


def merkle_proof(leaves: list[str], index: int) -> list[dict]:
    """Sibling path proving one leaf is in the tree, for spot checking."""
    proof, level, idx = [], list(leaves), index
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            if i + 1 < len(level):
                if i == idx:
                    proof.append({"side": "right", "hash": level[i + 1]})
                elif i + 1 == idx:
                    proof.append({"side": "left", "hash": level[i]})
                nxt.append(_pair_hash(level[i], level[i + 1]))
            else:
                nxt.append(level[i])
        idx //= 2
        level = nxt
    return proof


def verify_proof(leaf: str, proof: list[dict], root: str) -> bool:
    h = leaf
    for step in proof:
        h = (_pair_hash(step["hash"], h) if step["side"] == "left"
             else _pair_hash(h, step["hash"]))
    return h == root


class ArtifactLog:
    def __init__(self, path: Path = LOG_PATH):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Instance-scoped, not the module-level ROOT_PATH: seal() and verify()
        # used to write/read that global directly, so any second ArtifactLog
        # pointed at a different directory (e.g. an isolated comparison run)
        # would seal its root on top of every OTHER instance's, including the
        # real deployment's. dashboard/app.py already had to monkeypatch
        # ROOT_PATH before calling verify() to work around exactly this; this
        # makes the workaround unnecessary rather than adding a second one.
        self.root_path = path.parent / "merkle_root.json"

    def append(self, record: dict) -> str:
        """Write one artifact and return its leaf hash."""
        record = dict(record)
        record.setdefault("logged_at",
                          datetime.now(timezone.utc).isoformat(timespec="seconds"))
        record["seq"] = self.count()
        h = leaf_hash(record)
        record_with_hash = dict(record)
        record_with_hash["leaf_hash"] = h
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record_with_hash, ensure_ascii=False, default=str) + "\n")
        return h

    def count(self) -> int:
        if not self.path.exists():
            return 0
        with self.path.open("r", encoding="utf-8") as f:
            return sum(1 for _ in f)

    def read_all(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out

    def leaves(self) -> list[str]:
        """
        Recompute every leaf from its record rather than trusting the stored
        leaf_hash. If a record was edited, the recomputed hash diverges and the
        root changes, which is exactly what we want to be detectable.
        """
        leaves = []
        for rec in self.read_all():
            rec = dict(rec)
            rec.pop("leaf_hash", None)
            leaves.append(leaf_hash(rec))
        return leaves

    def root(self) -> str:
        return merkle_root(self.leaves())

    def seal(self) -> dict:
        """Publish the current root. Call at the end of each session."""
        recs = self.read_all()
        payload = {
            "sealed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "n_artifacts": len(recs),
            "merkle_root": self.root(),
            "first_seq": recs[0]["seq"] if recs else None,
            "last_seq": recs[-1]["seq"] if recs else None,
            "algorithm": "sha256, domain-separated leaves (0x00) and nodes (0x01), "
                         "odd node promoted unchanged",
        }
        self.root_path.parent.mkdir(parents=True, exist_ok=True)
        self.root_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    def verify(self) -> tuple[bool, str]:
        """Recompute and compare against the sealed root."""
        if not self.root_path.exists():
            return False, "no sealed root found; nothing to verify against"
        sealed = json.loads(self.root_path.read_text())
        recs = self.read_all()

        tampered = []
        for rec in recs:
            stored = rec.get("leaf_hash")
            clean = {k: v for k, v in rec.items() if k != "leaf_hash"}
            if stored and leaf_hash(clean) != stored:
                tampered.append(rec.get("seq"))

        recomputed = self.root()
        if tampered:
            return False, (f"{len(tampered)} artifact(s) fail their own leaf hash "
                           f"(seq {tampered[:10]}); the log was edited after writing")

        # Distinguish "grew since the seal" from "was altered". An append-only
        # log gaining records is expected between seals and is benign; the
        # sealed prefix must still verify unchanged. Reporting both as the same
        # failure would train the reader to ignore the one that matters.
        n_sealed = sealed["n_artifacts"]
        if len(recs) > n_sealed:
            prefix_root = merkle_root(self.leaves()[:n_sealed])
            if prefix_root != sealed["merkle_root"]:
                return False, (
                    f"TAMPERED: the first {n_sealed} sealed artifacts no longer "
                    f"reproduce their sealed root\n  sealed:     "
                    f"{sealed['merkle_root']}\n  recomputed: {prefix_root}")
            return False, (
                f"UNSEALED: {len(recs) - n_sealed} new artifact(s) since the seal. "
                f"The sealed prefix of {n_sealed} verifies unchanged, so nothing was "
                f"altered. Run `make seal` to publish the current root.")
        if len(recs) < n_sealed:
            return False, (f"artifacts REMOVED: sealed {n_sealed}, found {len(recs)}")
        if recomputed != sealed["merkle_root"]:
            return False, (f"root mismatch\n  sealed:     {sealed['merkle_root']}\n"
                           f"  recomputed: {recomputed}")
        return True, (f"VERIFIED: {len(recs)} artifacts, root {recomputed[:16]}... "
                      f"matches the seal written {sealed['sealed_at']}")


def _cli() -> None:
    log = ArtifactLog()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "verify"
    if cmd == "seal":
        print(json.dumps(log.seal(), indent=2))
    elif cmd == "verify":
        ok, msg = log.verify()
        print(msg)
        sys.exit(0 if ok else 1)
    elif cmd == "summary":
        recs = log.read_all()
        actions: dict[str, int] = {}
        blocking: dict[str, int] = {}
        env: dict[str, int] = {}
        opportunities = 0
        # Gates describing the ENVIRONMENT rather than a judgement. Kept in sync
        # with risk.Decision.ENVIRONMENTAL_GATES, duplicated here so the reader
        # has no import dependency on the agent package.
        environmental = ("market_open", "session_window")

        for r in recs:
            actions[r.get("action", "?")] = actions.get(r.get("action", "?"), 0) + 1

            bg = r.get("blocking_gate")
            eb = r.get("environmental_block")

            # LEGACY records predate the split and recorded an environmental
            # gate as the blocking one. Reclassify at READ time. The sealed log
            # is never rewritten: doing so would break the Merkle chain and
            # would be exactly the tampering the whole design exists to detect.
            if eb is None and bg in environmental:
                eb, bg = bg, None

            was_opportunity = r.get("was_an_opportunity")
            if was_opportunity is None:
                was_opportunity = eb is None

            if was_opportunity:
                opportunities += 1
                if bg:
                    blocking[bg] = blocking.get(bg, 0) + 1
            if eb:
                env[eb] = env.get(eb, 0) + 1

        print(f"artifacts: {len(recs)}")
        print(f"root     : {log.root()}")
        print("\nactions:")
        for k, v in sorted(actions.items(), key=lambda x: -x[1]):
            print(f"  {k:<10} {v:>5}")

        # Only cycles where the market was open and we were in the trading
        # window count as decisions the agent actually made. Mixing in "market
        # was closed" would make the refusal rate meaningless.
        print(f"\ndecision opportunities (market open, in window): {opportunities}")
        if blocking:
            total = sum(blocking.values())
            print(f"refusals by blocking gate ({total} of {opportunities} "
                  f"opportunities):")
            for k, v in sorted(blocking.items(), key=lambda x: -x[1]):
                pct = v / opportunities * 100 if opportunities else 0.0
                print(f"  {k:<20} {v:>5}  ({pct:.1f}% of opportunities)")
        elif opportunities:
            print("  no substantive refusals")
        if env:
            print(f"\nnot decisions, environment only:")
            for k, v in sorted(env.items(), key=lambda x: -x[1]):
                print(f"  {k:<20} {v:>5}")
    else:
        print(f"unknown command {cmd!r}; use seal | verify | summary")
        sys.exit(2)


if __name__ == "__main__":
    _cli()
