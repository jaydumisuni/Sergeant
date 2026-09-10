from pathlib import Path


def test_main_review_does_not_shallow_refetch_base_after_full_checkout():
    workflow = Path(".github/workflows/main-review.yml").read_text(encoding="utf-8")
    assert "fetch-depth: 0" in workflow
    assert "git fetch origin ${{ github.base_ref }} --depth=1" not in workflow
    assert "git diff --name-only origin/${{ github.base_ref }}...HEAD > changed-files.txt" in workflow
