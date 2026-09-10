from __future__ import annotations

import json
from pathlib import Path

from scripts.verify_frozen_transfer_replay import validate_archive, validate_changed_paths


def test_auth7_archive_is_exact_and_intact():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "evidence/frozen-transfer-replay/manifest.json").read_text())
    rec = manifest["sets"]["model-free-core-auth-transfer-7"]
    validate_archive(root, rec)
    assert rec["source_run_id"] == 34135754257
    assert rec["source_head"] == "8a25dbd69e9498b38c6f3f137e8140313a04a335"
    assert rec["fixture_repository"] == "jraversbcn21/PlayQAcademy"
    assert rec["fixture_fixing_ref"] == "90418d017ce04b41e643a044a52ead93c6fd03a0"


def test_await5_archive_is_exact_and_intact():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "evidence/frozen-transfer-replay/manifest.json").read_text())
    rec = manifest["sets"]["model-free-core-await-transfer-5"]
    validate_archive(root, rec)
    assert rec["source_run_id"] == 34453497537
    assert rec["source_head"] == "6ad9b816f09fe26031305efa37548fbf701a9940"
    assert rec["fixture_repository"] == "shantanuchandra/cardcompass"
    assert rec["fixture_fixing_ref"] == "8941b53d4a016535c018540b4c1df0394614e061"


def test_replay_path_gate_rejects_review_engine_change():
    allowed = ["docs/", "main_review/proof_world.py", "tests/test_proof_world.py"]
    validate_changed_paths(["docs/x.md", "main_review/proof_world.py"], allowed)
    try:
        validate_changed_paths(["main_review/engine.py"], allowed)
    except ValueError as exc:
        assert "main_review/engine.py" in str(exc)
    else:
        raise AssertionError("review-engine drift must fail closed")
