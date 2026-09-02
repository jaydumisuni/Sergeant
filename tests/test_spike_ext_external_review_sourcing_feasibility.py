from __future__ import annotations

import json
import subprocess
from collections import defaultdict, deque
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs/65-spike-ext-external-review-sourcing-feasibility-manifest.json"
DOC_PATH = ROOT / "docs/64-spike-ext-external-review-sourcing-feasibility.md"
ROADMAP_PATH = ROOT / "docs/59-sergeant-assurance-evolution-roadmap.md"
FOUNDING_ARCHITECTURE_PATH = ROOT / "docs/58-sergeant-assurance-evolution-founding-architecture.md"

REQUIRED_OUTPUT_KEYS = {
    "acceptable_external_source_classes",
    "authentication_provenance_route",
    "independence_control_lineage_criteria",
    "expected_mandatory_external_review_lane_cardinality_proposal",
    "sourcing_logistics_disposition",
}


def _git_blob_sha(path: Path) -> str:
    """Canonical git blob SHA via git itself rather than raw-byte hashing.

    A raw-byte hash is fragile on any Windows checkout with
    core.autocrlf=true, which rewrites LF line endings to CRLF in the
    working tree without changing the tracked git blob content. This is
    the exact false-failure class documented in
    docs/62-sae00-founding-authority-and-preservation-reference.md
    section 4.4/5 and reproduced live by
    tests/test_assurance_evolution_roadmap_freeze.py on Windows checkouts.
    `git hash-object` asks git itself what the blob identity is, so it
    agrees with the actual tracked content on every platform.
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


def _load_doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


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


def test_spike_ext_is_charter_matched_to_roadmap_section_6() -> None:
    """Independently re-derive that SPIKE-EXT's proof dependency is exactly
    [SAE-00], rather than trusting the manifest's own claim about itself."""
    dependencies = _dependency_registry()
    assert dependencies["SPIKE-EXT"] == ["SAE-00"]

    roadmap_text = ROADMAP_PATH.read_text(encoding="utf-8")
    assert "### SPIKE-EXT — Genuine external-review sourcing feasibility" in roadmap_text
    assert "Authority gain: none." in roadmap_text.split("SPIKE-EXT", 1)[1].split("SPIKE-SEM", 1)[0]


def test_spike_ext_manifest_binds_documents_by_real_git_blob_sha() -> None:
    manifest = _load_manifest()

    assert manifest["schema_version"] == "sergeant.spike-ext-external-review-sourcing-feasibility-manifest.v1"
    assert manifest["node"] == "SPIKE-EXT"
    assert manifest["proof_requires"] == ["SAE-00"]
    assert manifest["authority_gain"] == "none"
    # Forbidden equivalence (docs/59 sec.3): TESTS GREEN != QUALIFIED. SAE-00
    # had not merged to canonical main at write time, so this node must not
    # self-declare QUALIFIED or PROVEN.
    assert manifest["lifecycle_state"] in {"AUTHORIZED", "CANDIDATE", "REVIEWED", "QUALIFIED", "PROVEN"}
    assert manifest["lifecycle_state"] == "CANDIDATE"
    assert manifest["lifecycle_note"]

    assert manifest["sae00_state_at_write_time"]["merged_to_canonical_main"] is False
    for candidate_path in manifest["sae00_state_at_write_time"]["candidate_documents_not_bound_here"]:
        # These SAE-00 candidate files must genuinely be absent from this
        # branch -- if one now exists, the manifest's honesty claim is stale.
        assert not (ROOT / candidate_path).is_file(), candidate_path

    documents = manifest["documents"]
    assert len(documents) >= 10
    seen_paths: set[str] = set()
    for document in documents:
        path = ROOT / document["path"]
        assert path.is_file(), document["path"]
        assert _git_blob_sha(path) == document["blob_sha"], document["path"]
        assert document["role"], document["path"]
        seen_paths.add(document["path"])
    assert len(seen_paths) == len(documents)

    fixtures = manifest["proof_fixtures"]
    assert len(fixtures) == 1
    assert (ROOT / fixtures[0]["path"]).is_file()
    assert fixtures[0]["assurance_evolution_runtime_implementation"] is False


def test_spike_ext_produces_all_five_required_outputs() -> None:
    manifest = _load_manifest()
    required_outputs = manifest["required_outputs"]
    assert set(required_outputs.keys()) == REQUIRED_OUTPUT_KEYS
    assert all(required_outputs.values())


def test_spike_ext_source_classes_are_present_in_doc_and_named_distinctly() -> None:
    manifest = _load_manifest()
    doc = _load_doc()

    source_classes = manifest["source_classes"]
    assert len(source_classes) == 6

    ids = [entry["id"] for entry in source_classes]
    assert len(set(ids)) == len(ids), "source class ids must be distinct"

    doc_sections = [entry["doc_section"] for entry in source_classes]
    assert len(set(doc_sections)) == len(doc_sections), "doc sections must be distinct"

    for entry in source_classes:
        section_heading = f"### {entry['doc_section']} "
        assert section_heading in doc, entry["id"]

    # The false-positive trap (different AI vendor/account alone) must be
    # explicitly marked as not establishing independence by itself, both in
    # the manifest and in the doc's own prose.
    sc5 = next(entry for entry in source_classes if entry["id"] == "SC-5")
    assert sc5["does_not_by_itself_establish_independence"] is True
    assert "does not, by itself, establish independence" in doc

    # The most logistically ready class (CodeRabbit) must honestly record
    # its current doctrinal role rather than overclaiming readiness.
    sc6 = next(entry for entry in source_classes if entry["id"] == "SC-6")
    assert sc6["current_role_per_repo_doctrine"] == "training_material_not_qualification_authority_per_docs_12"
    assert sc6["currently_engaged"] is False

    # No source class may be marked as currently engaged -- this spike is
    # analysis-only and must not have contacted a real reviewer.
    assert all(entry["currently_engaged"] is False for entry in source_classes)


def test_spike_ext_independence_criteria_are_distinct_and_present_in_doc() -> None:
    manifest = _load_manifest()
    doc = _load_doc()

    criteria = manifest["independence_criteria"]
    assert len(criteria) == 9
    assert len(set(criteria)) == 9, "independence criteria must be distinct list entries"

    for criterion in criteria:
        assert criterion in doc, criterion

    rule = manifest["independence_disposition_rule"]
    assert set(rule.keys()) == {"INDEPENDENT", "NOT_INDEPENDENT", "UNKNOWN_INDEPENDENCE"}

    # These three states are recovered from docs/58 section 13, not invented
    # here -- confirm the founding architecture actually defines them.
    architecture_text = FOUNDING_ARCHITECTURE_PATH.read_text(encoding="utf-8")
    for state in ("`INDEPENDENT`", "`NOT_INDEPENDENT`", "`UNKNOWN_INDEPENDENCE`"):
        assert state in architecture_text


def test_spike_ext_authentication_provenance_route_is_not_blocked_on_spike_id() -> None:
    manifest = _load_manifest()
    doc = _load_doc()

    route = manifest["authentication_provenance_route"]
    assert len(route["steps"]) == 6
    assert len(set(route["steps"])) == 6
    assert route["identity_technology_required_first"] is False
    assert route["blocked_on_spike_id"] is False
    assert route["compatible_with_spike_id"] is True

    assert "SPIKE-ID" in doc
    assert "content-addressed" in doc.lower()


def test_spike_ext_cardinality_proposal_is_a_reasoned_positive_integer_range() -> None:
    manifest = _load_manifest()
    doc = _load_doc()

    cardinality = manifest["cardinality_proposal"]
    minimum = cardinality["minimum"]
    target = cardinality["target"]

    assert isinstance(minimum, int) and minimum > 0
    assert isinstance(target, int) and target >= minimum
    assert minimum >= 2, "a single lane is explicitly rejected as fragile in docs/59 sec.6 spirit"

    assert isinstance(cardinality["minimum_distinct_source_classes"], int)
    assert cardinality["minimum_distinct_source_classes"] >= 2
    assert cardinality["excluded_source_class_for_cardinality_purposes"] == "SC-5"

    assert cardinality["status"] == "proposal_for_sae20_acr_authoring_audit_not_binding_law"
    assert cardinality["reasoning_summary"]

    # The reasoning must actually appear in the doc, not only in the
    # manifest's own summary of itself.
    assert f"minimum {minimum}" in doc.lower() or "minimum 2, target 3" in doc.lower()
    assert "single point of failure" in doc.lower()

    # SAE-20 is the roadmap node explicitly chartered to audit external-
    # review-lane cardinality (docs/59 sec.7) -- confirm that charter is
    # real, not asserted, before this proposal claims to feed it.
    roadmap_text = ROADMAP_PATH.read_text(encoding="utf-8")
    assert "mandatory external-review-lane-cardinality attacks" in roadmap_text


def test_spike_ext_sourcing_disposition_is_honest_open_gap_not_false_positive() -> None:
    manifest = _load_manifest()
    doc = _load_doc()

    disposition = manifest["sourcing_disposition"]
    assert disposition["status"] == "open_gap_no_independent_lane_currently_active"
    assert disposition["this_spike_initiated_any_real_engagement"] is False
    assert len(disposition["evidence"]) >= 3
    assert len(disposition["nearest_practical_path_ranked"]) >= 1

    assert "open gap" in doc.lower()
    assert "no genuinely independent external-review source is currently" in doc.lower()

    # Cross-check the disposition's own evidence claim against the live
    # source registry rather than trusting the manifest's assertion about
    # it: every confirmed cross-repository source must actually be
    # owner-owned for the "open gap" claim to be honest.
    sources = json.loads(
        (ROOT / ".github/self-learning/cross-repository-sources.json").read_text(encoding="utf-8")
    )
    confirmed = sources["confirmed_sources"]
    assert len(confirmed) > 0
    assert all(entry["source_class"] == "thetechguy-owned" for entry in confirmed)


def test_spike_ext_does_not_overclaim_and_prohibitions_preserve_scope() -> None:
    manifest = _load_manifest()

    not_established = manifest["what_this_spike_does_not_establish"]
    assert len(not_established) >= 5
    assert "no source class currently satisfies INDEPENDENT disposition" in not_established
    assert "different_ai_vendor_account_alone_never_satisfies_independence" in not_established
    assert "no_real_external_reviewer_was_contacted_hired_or_contracted" in not_established

    prohibitions = set(manifest["prohibitions"])
    assert "do_not_treat_this_node_as_a_solved_independent_lane" in prohibitions
    assert "do_not_claim_a_different_ai_vendor_account_alone_is_independent" in prohibitions
    assert "do_not_engage_or_contact_a_real_external_reviewer_from_this_node" in prohibitions
    assert "do_not_grant_normal_sergeant_verdict_authority_from_this_node" in prohibitions
    assert "do_not_treat_project_controlled_ai_hostile_review_rounds_as_independent" in prohibitions
    assert "do_not_retrofit_pr_167" in prohibitions


def test_spike_ext_dependency_dag_remains_closed_and_acyclic_with_spike_ext_present() -> None:
    """Re-run the same structural closure/acyclic proof
    tests/test_assurance_evolution_roadmap_freeze.py performs, confirming
    this spike's document did not (and structurally cannot, since it is
    docs-only) alter the frozen roadmap's dependency graph."""
    dependencies = _dependency_registry()

    assert len(dependencies) == 28
    referenced = {dependency for values in dependencies.values() for dependency in values}
    assert referenced <= set(dependencies)

    roots = sorted(name for name, values in dependencies.items() if not values)
    assert roots == ["SAE-00"]

    children: dict[str, list[str]] = defaultdict(list)
    indegree = {name: len(values) for name, values in dependencies.items()}
    for name, values in dependencies.items():
        for dependency in values:
            children[dependency].append(name)

    queue = deque(roots)
    ordered: list[str] = []
    while queue:
        node = queue.popleft()
        ordered.append(node)
        for child in children[node]:
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)

    assert len(ordered) == len(dependencies), "dependency graph must remain acyclic"
