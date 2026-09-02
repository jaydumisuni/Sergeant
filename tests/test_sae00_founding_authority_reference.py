from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs/63-sae00-founding-authority-reference-manifest.json"
RECORD_PATH = ROOT / "docs/62-sae00-founding-authority-and-preservation-reference.md"
ROADMAP_PATH = ROOT / "docs/59-sergeant-assurance-evolution-roadmap.md"
FREEZE_MANIFEST_PATH = ROOT / "docs/61-sergeant-assurance-evolution-freeze-manifest.json"

REQUIRED_BINDING_KEYS = {
    "approved_founding_architecture",
    "approved_roadmap_generation",
    "freshly_recovered_live_sergeant_main",
    "preservation_constitution",
    "current_model_free_benchmark",
    "current_security_boundary",
    "existing_learning_state",
    "existing_cpl_officer_hierarchy",
    "existing_proof_behavior",
    "pr_167_fence",
}

REQUIRED_PROOF_KEYS = {
    "no_rejected_lesson_revived",
    "normal_sergeant_baseline_reproducible",
    "security_baseline_reproducible",
}


def _git_blob_sha(path: Path) -> str:
    """Canonical git blob SHA via git itself.

    Deliberately uses `git hash-object` (subprocess) rather than hashing raw
    working-tree bytes. A raw-byte hash is fragile on any Windows checkout
    with `core.autocrlf=true`, which rewrites LF line endings to CRLF in the
    working tree without changing the tracked git blob content -- this is
    the exact false-failure class documented in
    docs/62-sae00-founding-authority-and-preservation-reference.md section 4.4
    and section 5, observed live in
    tests/test_assurance_evolution_roadmap_freeze.py on this construction
    machine. `git hash-object` asks git itself what the blob identity is,
    so it agrees with the actual tracked content on every platform.
    """
    result = subprocess.run(
        ["git", "hash-object", str(path)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _dependency_registry() -> dict[str, list[str]]:
    text = ROADMAP_PATH.read_text(encoding="utf-8")
    marker = "## 15. Dependency registry v1.1"
    assert marker in text
    section = text.split(marker, 1)[1]
    block = section.split("```yaml", 1)[1].split("```", 1)[0]

    dependencies: dict[str, list[str]] = {}
    current: str | None = None
    for raw in block.splitlines():
        if not raw.strip():
            continue
        if raw == raw.lstrip():
            key, remainder = raw.split(":", 1)
            key = key.strip()
            remainder = remainder.strip()
            if remainder.startswith("["):
                inner = remainder[1:-1].strip()
                dependencies[key] = [item.strip() for item in inner.split(",") if item.strip()]
                current = None
            else:
                dependencies[key] = []
                current = key
            continue
        if current and raw.strip().startswith("- "):
            dependencies[current].append(raw.strip()[2:].strip())
    return dependencies


def test_sae00_manifest_binds_authority_documents_by_real_git_blob_sha() -> None:
    manifest = _load_manifest()

    assert manifest["schema_version"] == "sergeant.sae00-founding-authority-reference-manifest.v1"
    assert manifest["node"] == "SAE-00"
    assert manifest["authority_state"] == "sae00_candidate_proof_attached_awaiting_owner_review"
    assert manifest["lifecycle_state"] in {"AUTHORIZED", "CANDIDATE", "REVIEWED", "QUALIFIED", "PROVEN"}
    # Forbidden equivalence (docs/59 sec.3): TESTS GREEN != QUALIFIED. This PR is
    # self-reviewed and CI-green but not yet Owner-reviewed/merged, so it must not
    # self-declare QUALIFIED or PROVEN.
    assert manifest["lifecycle_state"] == "CANDIDATE"
    assert manifest["lifecycle_note"]

    documents = manifest["documents"]
    assert len(documents) >= 20
    seen_paths: set[str] = set()
    for document in documents:
        path = ROOT / document["path"]
        assert path.is_file(), document["path"]
        assert _git_blob_sha(path) == document["blob_sha"], document["path"]
        assert document["role"], document["path"]
        seen_paths.add(document["path"])

    # No duplicate document entries.
    assert len(seen_paths) == len(documents)

    fixtures = manifest["proof_fixtures"]
    assert len(fixtures) == 1
    fixture_path = ROOT / fixtures[0]["path"]
    assert fixture_path.is_file()
    assert fixtures[0]["assurance_evolution_runtime_implementation"] is False
    assert fixtures[0]["blob_sha"]
    assert _git_blob_sha(fixture_path) == fixtures[0]["blob_sha"], fixtures[0]["path"]


def test_sae00_proof_fixture_self_hash_matches_manifest() -> None:
    """This test file is its own proof fixture (docs/63's proof_fixtures
    entry). Verify its own current on-disk content still matches the hash
    the manifest records for it -- an edit to this file that isn't matched
    by a manifest update should be caught here, mirroring how docs/61
    hash-binds tests/test_assurance_evolution_roadmap_freeze.py."""
    manifest = _load_manifest()
    fixture = manifest["proof_fixtures"][0]
    this_file = ROOT / fixture["path"]
    assert this_file.resolve() == Path(__file__).resolve()
    assert _git_blob_sha(this_file) == fixture["blob_sha"]


def test_sae00_ten_required_bindings_are_present_and_point_to_real_artifacts() -> None:
    manifest = _load_manifest()
    bindings = manifest["bindings"]

    assert set(bindings.keys()) == REQUIRED_BINDING_KEYS

    # 1: approved founding architecture.
    assert (ROOT / bindings["approved_founding_architecture"]["path"]).is_file()

    # 2: approved roadmap generation.
    roadmap_binding = bindings["approved_roadmap_generation"]
    for key in ("path", "freeze_record", "freeze_manifest", "freeze_proof_test"):
        assert (ROOT / roadmap_binding[key]).is_file(), key

    # 3: freshly recovered live Sergeant main -- must be a real 40-char SHA,
    # distinct from the stale roadmap planning-base SHA.
    live_main = bindings["freshly_recovered_live_sergeant_main"]
    assert len(live_main["sha"]) == 40
    assert all(c in "0123456789abcdef" for c in live_main["sha"])
    assert live_main["sha"] != live_main["superseded_planning_sha"]

    # 4: preservation constitution -- explicit judgment call, joint binding.
    preservation = bindings["preservation_constitution"]
    assert preservation["judgment_call"] is True
    assert len(preservation["paths"]) >= 2
    for raw_path in preservation["paths"]:
        real_path = raw_path.split("#", 1)[0]
        assert (ROOT / real_path).is_file(), real_path

    # 5: current model-free benchmark.
    benchmark = bindings["current_model_free_benchmark"]
    assert (ROOT / benchmark["path"]).is_file()
    assert benchmark["fabricated"] is False
    assert "passed" in benchmark["result"]

    # 6: current security boundary. The actual detector lives in
    # main_review/evidence.py (SECRET_PATTERNS / SecretEvidenceProvider);
    # main_review/officer_council.py only routes an already-produced finding
    # to the Medic officer label and must not be mistaken for the detector.
    security = bindings["current_security_boundary"]
    assert (ROOT / security["specification_path"]).is_file()
    assert (ROOT / security["implementation_path"]).is_file()
    assert security["implementation_path"] == "main_review/evidence.py"
    impl_source = (ROOT / security["implementation_path"]).read_text(encoding="utf-8")
    assert "SECRET_PATTERNS" in impl_source
    assert "class SecretEvidenceProvider" in impl_source
    assert (ROOT / security["routing_path"]).is_file()
    assert (ROOT / security["proof_test_path"]).is_file()
    assert security["fabricated"] is False
    test_source = (ROOT / security["proof_test_path"]).read_text(encoding="utf-8")
    assert f"def {security['proof_test_name']}(" in test_source

    # 7: existing learning state -- all six accepted lessons hash-bound and
    # verified accepted, not only the two PICKUP.md names by path in prose.
    learning = bindings["existing_learning_state"]
    assert (ROOT / learning["path"]).is_file()
    for lesson_path in learning["verified_accepted_lesson_paths"]:
        assert (ROOT / lesson_path).is_file(), lesson_path
        lesson = json.loads((ROOT / lesson_path).read_text(encoding="utf-8"))
        assert lesson.get("status") == "accepted", lesson_path
    lessons_dir = ROOT / learning["lessons_directory"]
    assert lessons_dir.is_dir()
    actual_lesson_files = sorted(p.name for p in lessons_dir.glob("*.json"))
    assert len(actual_lesson_files) == learning["lessons_directory_file_count"]
    all_bound = learning["all_hash_bound_accepted_lesson_paths"]
    assert len(all_bound) == learning["lessons_directory_file_count"]
    assert sorted(Path(p).name for p in all_bound) == actual_lesson_files
    for lesson_path in all_bound:
        lesson = json.loads((ROOT / lesson_path).read_text(encoding="utf-8"))
        assert lesson.get("status") == "accepted", lesson_path

    # 8: existing Cpl/officer hierarchy.
    hierarchy = bindings["existing_cpl_officer_hierarchy"]
    for doctrine_path in hierarchy["doctrine_paths"]:
        assert (ROOT / doctrine_path).is_file(), doctrine_path
    assert (ROOT / hierarchy["implementation_path"]).is_file()

    # 9: existing proof behavior -- including the verification/scanner
    # dependency chain final_proof.py actually delegates to, not just the
    # two top-level entry-point files.
    proof_behavior = bindings["existing_proof_behavior"]
    assert (ROOT / proof_behavior["verdict_engine_path"]).is_file()
    assert (ROOT / proof_behavior["final_proof_gate_path"]).is_file()
    assert (ROOT / proof_behavior["verification_path"]).is_file()
    assert (ROOT / proof_behavior["scanner_path"]).is_file()
    final_proof_source = (ROOT / proof_behavior["final_proof_gate_path"]).read_text(encoding="utf-8")
    assert "from .verification import verify_repository_standard" in final_proof_source
    verification_source = (ROOT / proof_behavior["verification_path"]).read_text(encoding="utf-8")
    assert "from .scanner import scan_repository" in verification_source
    assert proof_behavior["fabricated"] is False
    assert proof_behavior["result"]["passed"] is True
    assert proof_behavior["result"]["blockers"] == []
    assert proof_behavior["result"]["verdict"] == "PASS"

    # 10: PR #167 non-retrofit fence.
    fence = bindings["pr_167_fence"]
    assert fence["pr"] == 167
    assert fence["state"] == "OPEN"
    assert fence["draft"] is True
    assert fence["merged"] is False
    assert fence["retrofit_assurance_evolution"] is False
    assert fence["sae00_touched_pr_167"] is False


def test_sae00_pr_167_fence_is_unchanged_since_roadmap_freeze() -> None:
    """PR #167's identity recorded at SAE-00 binding must match the identity
    recorded at roadmap freeze (docs/61) exactly -- proving live recovery
    found the same fence, not a drifted or reinterpreted one."""
    manifest = _load_manifest()
    freeze_manifest = json.loads(FREEZE_MANIFEST_PATH.read_text(encoding="utf-8"))

    fence = manifest["bindings"]["pr_167_fence"]
    frozen_fence = freeze_manifest["live_fence_at_freeze"]

    assert fence["pr"] == frozen_fence["pr"]
    assert fence["base_sha"] == frozen_fence["base_sha"]
    assert fence["head_sha"] == frozen_fence["head_sha"]
    assert fence["draft"] == frozen_fence["draft"]
    assert fence["merged"] == frozen_fence["merged"]
    assert fence["retrofit_assurance_evolution"] == frozen_fence["retrofit_assurance_evolution"]
    assert fence["unchanged_since_freeze"] is True


def test_sae00_required_proofs_are_recorded_with_real_methodology_not_fabricated() -> None:
    manifest = _load_manifest()
    proofs = manifest["proofs"]

    assert set(proofs.keys()) == REQUIRED_PROOF_KEYS

    no_revival = proofs["no_rejected_lesson_revived"]
    assert no_revival["accepted_lessons_directory_grep_result"] == "no_match"
    assert no_revival["rejected_candidate_disposition_confirmed"] is True
    assert len(no_revival["rejected_candidates_checked"]) == 2

    baseline = proofs["normal_sergeant_baseline_reproducible"]
    assert isinstance(baseline["total_collected"], int) and baseline["total_collected"] > 0
    assert isinstance(baseline["passed"], int) and baseline["passed"] > 0
    assert isinstance(baseline["failed"], int) and baseline["failed"] >= 0
    assert baseline["total_collected"] == baseline["passed"] + baseline["failed"]
    assert baseline["invocation"] == "python -m pytest -q -ra"
    assert baseline["matches_ci_invocation"] == "repository continuous-integration test job (pytest -q -ra)"
    assert baseline["fabricated"] is False
    if baseline["failed"] > 0:
        # A non-zero failure count must be honestly explained, not hidden.
        assert baseline["failure_is_pre_existing_and_explained"] is True
        assert baseline["failing_test"]
        assert baseline["failure_root_cause"]
        assert baseline["failure_confirmed_not_a_content_divergence"] is True

    security_proof = proofs["security_baseline_reproducible"]
    assert security_proof["result"] == "1 passed"
    assert security_proof["fabricated"] is False


def test_sae00_ci_invocation_claim_matches_live_ci_workflow() -> None:
    """Cross-check the manifest's claimed CI-equivalent invocation against
    the actual CI workflow file, rather than trusting the manifest's own
    assertion about itself."""
    ci_workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "pytest -q -ra" in ci_workflow


def test_sae00_officer_hierarchy_binding_matches_live_implementation() -> None:
    """The Cpl/officer hierarchy binding must point at code that genuinely
    implements the documented ten-officer formation, not just a doc that
    describes it."""
    import main_review.officer_council as officer_council

    assert officer_council.OFFICER_ORDER == (
        "Quartermaster",
        "Scout",
        "Engineer",
        "Medic",
        "Mechanic",
        "Analyst",
        "Challenger",
        "Archivist",
        "Judge",
        "Hermes",
    )
    assert officer_council.OFFICER_BY_CAPABILITY["security"] == "Medic"
    assert officer_council.OFFICER_BY_CAPABILITY["security_taint"] == "Medic"
    assert callable(officer_council.run_officer_council)


def test_sae00_no_rejected_lesson_is_present_in_accepted_lessons_directory() -> None:
    """Independently re-derive the no-revival proof rather than trusting the
    manifest's own claim about it."""
    lessons_dir = ROOT / ".github/self-learning/lessons"
    lesson_files = list(lessons_dir.glob("*.json"))
    assert len(lesson_files) == 6

    combined_text = "\n".join(p.read_text(encoding="utf-8") for p in lesson_files)
    assert "checkout-credential-boundary" not in combined_text
    assert "oracle-oidc-workflow-identity" not in combined_text

    oracle_result = json.loads(
        (ROOT / ".github/self-learning/results/project-oracle-oidc-workflow-20260818.json").read_text(
            encoding="utf-8"
        )
    )
    assert oracle_result["state"] == "rejected"
    assert oracle_result["accepted_lesson"] is False
    assert oracle_result["sergeant_verdict"] == "reject"


def test_sae00_produces_exactly_the_three_required_authority_artifacts() -> None:
    manifest = _load_manifest()
    assert manifest["produces"] == [
        "SERGEANT_PRESERVATION_REFERENCE",
        "FOUNDING_ARCHITECTURE_AUTHORITY",
        "ROADMAP_EXECUTION_AUTHORITY",
    ]
    assert manifest["authority_gain"] == "isolated_assurance_evolution_construction_only_no_normal_verdict_authority"


def test_sae00_is_the_true_dependency_root_and_lists_only_direct_dependents() -> None:
    """direct_dependent_nodes_in_dag is a structural DAG fact, not an
    authority grant -- see lifecycle_note. This test only re-derives the DAG
    topology independently and checks the manifest's list matches it."""
    dependencies = _dependency_registry()
    assert dependencies["SAE-00"] == []

    direct_dependents = sorted(
        name for name, deps in dependencies.items() if deps == ["SAE-00"]
    )

    manifest = _load_manifest()
    assert sorted(manifest["direct_dependent_nodes_in_dag"]) == direct_dependents
    # The manifest must not claim a stronger lifecycle state than CANDIDATE
    # while simultaneously listing dependents -- that would let a reader
    # mistake DAG topology for granted downstream proof authority.
    assert manifest["lifecycle_state"] == "CANDIDATE"


def test_sae00_record_document_states_five_required_assurances() -> None:
    record = RECORD_PATH.read_text(encoding="utf-8")
    for heading in (
        "recovered without chat authority",
        "no existing mechanism was misclassified as missing",
        "No rejected lesson was revived",
        "Normal Sergeant baseline is reproducible",
        "Security baseline is reproducible",
    ):
        assert heading.lower() in record.lower(), heading


def test_sae00_prohibitions_preserve_no_normal_verdict_authority_transfer() -> None:
    manifest = _load_manifest()
    prohibitions = set(manifest["prohibitions"])
    assert "do_not_grant_normal_sergeant_verdict_authority_from_this_node" in prohibitions
    assert "do_not_retrofit_pr_167" in prohibitions
    assert "do_not_activate_partial_assurance_evolution" in prohibitions
    assert "do_not_revive_a_terminally_rejected_lesson_from_the_same_evidence" in prohibitions
