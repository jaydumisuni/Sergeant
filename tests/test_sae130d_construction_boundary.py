from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'docs/149-sae130d-semantic-mutation-construction-manifest.json'
def test_construction_fails_closed_until_required_candidate_inventory_exists():
 m=json.loads(MANIFEST.read_text())
 assert m['lifecycle_state']=='CONSTRUCTION'
 assert m['base_proven']=='4b3a59117c6ccfac5d6d6d47f795cb4333566b69'
 assert m['candidate_merge_authorized'] is False
 assert m['authority_gain']=='none'
 assert set(m['required_mutants'])=={'guard_deletion','authority_substitution','route_addition','missing_binding_or_member','recovery_breakage','generation_or_state_mutation','evidence_omission','no_op_detection'}
 assert not all((ROOT/path).is_file() for path in m['required_candidate_surfaces'])
