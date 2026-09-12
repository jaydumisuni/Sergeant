from __future__ import annotations
import json
from pathlib import Path
from main_review.genesis_qualification import REQUIRED_MUTATIONS, REQUIRED_NODES
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"docs/161-sae150-genesis-qualification-candidate-manifest.json"

def test_required_inventory_and_dependency_generations_are_bound():
 m=json.loads(MANIFEST.read_text())
 for rel in m["required_surfaces"]: assert (ROOT/rel).is_file()
 assert set(m["proof_requires"])==set(REQUIRED_NODES)
 assert set(m["required_mutation_families"])==set(REQUIRED_MUTATIONS)

def test_current_candidate_fails_closed_on_real_external_lane_gap():
 m=json.loads(MANIFEST.read_text())
 assert m["lifecycle_state"]=="GENESIS_PROVISIONAL"
 assert m["mandatory_independent_lane"]["required"] is True
 assert m["mandatory_independent_lane"]["currently_satisfied"] is False
 assert m["candidate_merge_authorized"] is False
 assert m["authority_gain"]=="none" and m["genesis_activated"] is False

def test_spike_ext_proven_artifact_itself_records_open_external_gap():
 spike=json.loads((ROOT/"docs/69-spike-ext-proven-lifecycle-closeout-manifest.json").read_text())
 assert spike["lifecycle_state"]=="PROVEN"
 assert spike["sourcing_disposition"]["status"]=="OPEN_GAP"
 assert spike["sourcing_disposition"]["genesis_external_lane_satisfied"] is False
