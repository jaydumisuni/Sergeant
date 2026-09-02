from __future__ import annotations

from pathlib import Path

import pytest


# This exact assertion belongs to the frozen SAE-00 candidate generation in
# docs/63. It intentionally asserted that the candidate tree at that time
# collected exactly 1040 tests. After SAE-00 became PROVEN and downstream
# roadmap nodes added their own tests, reinterpreting that historical snapshot
# as an eternal current-tree invariant became impossible by construction.
#
# Keep the historical fixture byte-identical so docs/63's blob binding remains
# truthful. Supersede only this obsolete runtime interpretation from outside
# the frozen generation. strict=True makes an unexpected XPASS a suite failure.
_HISTORICAL_SAE00_CURRENT_COUNT_NODEID = (
    "tests/test_sae00_founding_authority_reference.py::"
    "test_sae00_exact_candidate_tree_collection_count_is_current"
)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if item.nodeid == _HISTORICAL_SAE00_CURRENT_COUNT_NODEID:
            item.add_marker(
                pytest.mark.xfail(
                    strict=True,
                    reason=(
                        "docs/63 is the immutable SAE-00 CANDIDATE snapshot; "
                        "its 1040-test exact-tree count is historical evidence, "
                        "not an invariant over later PROVEN/downstream trees"
                    ),
                )
            )


@pytest.fixture(autouse=True)
def _isolate_model_routes_and_usage_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Keep unit tests off live routes and away from the user's usage ledger."""

    monkeypatch.setenv("SERGEANT_LLM_ENABLED", "false")
    monkeypatch.setenv(
        "SERGEANT_CLOUDFLARE_USAGE_STATE",
        str(tmp_path / "cloudflare-usage.json"),
    )
