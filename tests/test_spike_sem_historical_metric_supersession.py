from __future__ import annotations

import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFTEST = ROOT / 'tests/conftest.py'
CANDIDATE = ROOT / 'docs/75-spike-sem-feasibility-manifest.json'
CLOSEOUT = ROOT / 'docs/77-spike-sem-proven-lifecycle-closeout-manifest.json'
HISTORICAL_NODE = (
    'tests/spike_sem/test_semantic_feasibility_probe.py::'
    'test_real_sergeant_main_review_semantic_metrics_are_frozen_from_observation'
)
HISTORICAL_PROOF_BLOB = 'b2bf08d7103e490dc816a1a195c05c34b0d0d97d'


def test_spike_sem_metric_snapshot_is_historical_not_current_tree_invariant() -> None:
    candidate = json.loads(CANDIDATE.read_text(encoding='utf-8'))
    closeout = json.loads(CLOSEOUT.read_text(encoding='utf-8'))

    assert candidate['proof_fixture']['blob_sha'] == HISTORICAL_PROOF_BLOB
    assert candidate['corrected_real_sergeant_measurement']['total_relations'] == 14439
    assert closeout['candidate_generation']['probe_proof']['blob_sha'] == HISTORICAL_PROOF_BLOB
    assert closeout['candidate_generation']['historical_candidate_preserved_not_rewritten'] is True
    assert closeout['measurement_history']['corrected_measurement']['total_relations'] == 14439


def test_exact_historical_metric_node_receives_strict_supersession_marker() -> None:
    namespace = runpy.run_path(str(CONFTEST))
    hook = namespace['pytest_collection_modifyitems']

    class FakeItem:
        nodeid = HISTORICAL_NODE

        def __init__(self) -> None:
            self.markers = []

        def add_marker(self, marker) -> None:
            self.markers.append(marker)

    item = FakeItem()
    hook([item])
    assert len(item.markers) == 1
    mark = item.markers[0].mark
    assert mark.name == 'xfail'
    assert mark.kwargs.get('strict') is True
    assert 'historical SPIKE-SEM' in str(mark.kwargs.get('reason', ''))
