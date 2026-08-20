"""
Tests for the artifact log and Merkle verification.

The claim this system makes to a judge is: "you can recompute this yourself and
confirm nothing was edited after the fact." These tests exist to prove that
claim is true, including that TAMPERING IS ACTUALLY DETECTED. A verifier that
returns True unconditionally would pass a naive test suite and be worthless.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

from artifacts import (  # noqa: E402
    ArtifactLog, canonical, leaf_hash, merkle_proof, merkle_root, verify_proof,
)


@pytest.fixture
def log(tmp_path, monkeypatch):
    import artifacts as A
    p = tmp_path / "decisions.jsonl"
    monkeypatch.setattr(A, "ROOT_PATH", tmp_path / "merkle_root.json")
    return ArtifactLog(p)


def rec(i: int, action: str = "refuse") -> dict:
    return {"timestamp": f"2026-08-31T10:{i:02d}:00", "action": action,
            "blocking_gate": "vrp_threshold" if action == "refuse" else None,
            "signals": {"vrp": 0.5 + i}}


# --- canonical form -------------------------------------------------------

def test_canonical_is_key_order_independent():
    a = {"b": 1, "a": 2, "c": {"z": 1, "y": 2}}
    b = {"c": {"y": 2, "z": 1}, "a": 2, "b": 1}
    assert canonical(a) == canonical(b)


def test_canonical_distinguishes_different_values():
    assert canonical({"a": 1}) != canonical({"a": 2})


# --- merkle mechanics -----------------------------------------------------

def test_empty_tree_has_a_defined_root():
    assert isinstance(merkle_root([]), str)
    assert len(merkle_root([])) == 64


def test_single_leaf_root_is_the_leaf():
    h = leaf_hash({"a": 1})
    assert merkle_root([h]) == h


def test_root_changes_when_any_leaf_changes():
    a = [leaf_hash(rec(i)) for i in range(5)]
    b = list(a)
    b[2] = leaf_hash(rec(99))
    assert merkle_root(a) != merkle_root(b)


def test_root_is_order_sensitive():
    a = [leaf_hash(rec(i)) for i in range(4)]
    assert merkle_root(a) != merkle_root(list(reversed(a)))


def test_leaves_and_nodes_are_domain_separated():
    """
    Without domain separation an internal node could be passed off as a leaf.
    Constructing a record whose canonical bytes equal a node concatenation must
    not collide with that node's hash.
    """
    a, b = leaf_hash({"x": 1}), leaf_hash({"x": 2})
    node = merkle_root([a, b])
    assert node != a and node != b


def test_odd_leaf_count_is_handled():
    for n in (1, 2, 3, 5, 7, 9):
        leaves = [leaf_hash(rec(i)) for i in range(n)]
        assert len(merkle_root(leaves)) == 64


def test_proof_verifies_for_every_leaf():
    leaves = [leaf_hash(rec(i)) for i in range(8)]
    root = merkle_root(leaves)
    for i in range(8):
        assert verify_proof(leaves[i], merkle_proof(leaves, i), root) is True


def test_proof_fails_for_a_forged_leaf():
    leaves = [leaf_hash(rec(i)) for i in range(8)]
    root = merkle_root(leaves)
    forged = leaf_hash(rec(1234))
    assert verify_proof(forged, merkle_proof(leaves, 3), root) is False


# --- append and read ------------------------------------------------------

def test_append_assigns_sequential_seq(log):
    for i in range(4):
        log.append(rec(i))
    recs = log.read_all()
    assert [r["seq"] for r in recs] == [0, 1, 2, 3]


def test_append_stores_a_leaf_hash(log):
    h = log.append(rec(0))
    assert log.read_all()[0]["leaf_hash"] == h


def test_count_matches_records(log):
    for i in range(7):
        log.append(rec(i))
    assert log.count() == 7 == len(log.read_all())


def test_refusals_are_logged_as_first_class_artifacts(log):
    log.append(rec(0, "refuse"))
    log.append(rec(1, "enter"))
    log.append(rec(2, "refuse"))
    actions = [r["action"] for r in log.read_all()]
    assert actions.count("refuse") == 2, "refusals must be recorded, not dropped"


# --- seal and verify ------------------------------------------------------

def test_verify_fails_before_sealing(log):
    log.append(rec(0))
    ok, msg = log.verify()
    assert ok is False
    assert "no sealed root" in msg


def test_seal_then_verify_passes(log):
    for i in range(6):
        log.append(rec(i))
    sealed = log.seal()
    ok, msg = log.verify()
    assert ok is True
    assert sealed["merkle_root"] in msg or "VERIFIED" in msg
    assert sealed["n_artifacts"] == 6


def test_tampering_with_a_record_is_detected(log):
    """The load-bearing test. Edit a logged decision and verification must fail."""
    for i in range(5):
        log.append(rec(i))
    log.seal()

    lines = log.path.read_text(encoding="utf-8").strip().splitlines()
    victim = json.loads(lines[2])
    victim["action"] = "enter"                       # rewrite history
    victim["signals"]["vrp"] = 99.0
    lines[2] = json.dumps(victim, default=str)
    log.path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    ok, msg = log.verify()
    assert ok is False
    assert "edited after writing" in msg or "root mismatch" in msg


def test_tampering_that_also_rewrites_the_leaf_hash_is_still_detected(log):
    """
    A smarter forger recomputes the leaf hash too, so the per-record check
    passes. The Merkle root must still catch it, because the sealed root was
    published before the edit.
    """
    for i in range(5):
        log.append(rec(i))
    log.seal()

    lines = log.path.read_text(encoding="utf-8").strip().splitlines()
    victim = json.loads(lines[1])
    victim.pop("leaf_hash")
    victim["action"] = "enter"
    victim["leaf_hash"] = leaf_hash(victim)          # forge consistently
    lines[1] = json.dumps(victim, default=str)
    log.path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    ok, msg = log.verify()
    assert ok is False
    assert "root mismatch" in msg


def test_deleting_a_record_is_detected(log):
    for i in range(5):
        log.append(rec(i))
    log.seal()
    lines = log.path.read_text(encoding="utf-8").strip().splitlines()
    del lines[3]
    log.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ok, msg = log.verify()
    assert ok is False
    # Deletion is now reported distinctly from growth and from tampering, so the
    # reader can tell which happened rather than seeing one generic failure.
    assert "REMOVED" in msg or "root mismatch" in msg


def test_appending_after_sealing_is_detected(log):
    """Adding a flattering trade after the fact must not verify."""
    for i in range(4):
        log.append(rec(i))
    log.seal()
    log.append(rec(99, "enter"))
    ok, msg = log.verify()
    assert ok is False


def test_verify_passes_on_an_untouched_log(log):
    """Guard against a verifier that just always returns False."""
    for i in range(10):
        log.append(rec(i))
    log.seal()
    ok, _ = log.verify()
    assert ok is True


def test_root_is_reproducible_across_instances(log):
    for i in range(5):
        log.append(rec(i))
    first = log.root()
    second = ArtifactLog(log.path).root()
    assert first == second, "a third party must recompute the same root"


# --- grew-since-seal must be distinguishable from tampered ---------------
# Reporting both as the same failure trains the reader to ignore the one that
# matters. An append-only log gaining records between seals is expected.

def test_growth_since_seal_is_reported_as_unsealed_not_tampered(log):
    for i in range(4):
        log.append(rec(i))
    log.seal()
    log.append(rec(99, "enter"))
    ok, msg = log.verify()
    assert ok is False
    assert "UNSEALED" in msg
    assert "verifies unchanged" in msg


def test_growth_plus_edit_of_the_sealed_prefix_is_reported_as_tampered(log):
    """Growth is benign; growth WITH an edited prefix is not, and must say so."""
    for i in range(4):
        log.append(rec(i))
    log.seal()
    log.append(rec(99, "enter"))

    lines = log.path.read_text(encoding="utf-8").strip().splitlines()
    victim = json.loads(lines[1])
    victim.pop("leaf_hash")
    victim["action"] = "enter"
    victim["leaf_hash"] = leaf_hash(victim)
    lines[1] = json.dumps(victim, default=str)
    log.path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    ok, msg = log.verify()
    assert ok is False
    assert "TAMPERED" in msg


def test_removal_is_reported_distinctly(log):
    for i in range(5):
        log.append(rec(i))
    log.seal()
    lines = log.path.read_text(encoding="utf-8").strip().splitlines()
    log.path.write_text("\n".join(lines[:3]) + "\n", encoding="utf-8")
    ok, msg = log.verify()
    assert ok is False
    assert "REMOVED" in msg


def test_resealing_after_growth_restores_verification(log):
    for i in range(4):
        log.append(rec(i))
    log.seal()
    log.append(rec(99, "enter"))
    assert log.verify()[0] is False
    log.seal()
    assert log.verify()[0] is True
