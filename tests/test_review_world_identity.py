from __future__ import annotations

import importlib.util


def test_review_world_authority_module_exists() -> None:
    assert importlib.util.find_spec("main_review.review_world") is not None
