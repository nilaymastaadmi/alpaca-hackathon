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
        ROOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        ROOT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    def verify(self) -> tuple[bool, str]:
        """Recompute and compare against the sealed root."""
        if not ROOT_PATH.exists():
            return False, "no sealed root found; nothing to verify against"
        sealed = json.loads(ROOT_PATH.read_text())
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
        if len(recs) != sealed["n_artifacts"]:
            return False, (f"artifact count changed: sealed {sealed['n_artifacts']}, "
                           f"found {len(recs)}")
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
        for r in recs:
            actions[r.get("action", "?")] = actions.get(r.get("action", "?"), 0) + 1
            bg = r.get("blocking_gate")
            if bg:
                blocking[bg] = blocking.get(bg, 0) + 1
        print(f"artifacts: {len(recs)}")
        print(f"root     : {log.root()}")
        print("\nactions:")
        for k, v in sorted(actions.items(), key=lambda x: -x[1]):
            print(f"  {k:<10} {v:>5}")
        if blocking:
            total_ref = sum(blocking.values())
            print(f"\nrefusals by blocking gate ({total_ref} total):")
            for k, v in sorted(blocking.items(), key=lambda x: -x[1]):
                print(f"  {k:<20} {v:>5}  ({v / total_ref * 100:.1f}%)")
    else:
        print(f"unknown command {cmd!r}; use seal | verify | summary")
        sys.exit(2)


if __name__ == "__main__":
    _cli()
