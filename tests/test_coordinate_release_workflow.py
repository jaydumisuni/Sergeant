from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "coordinate-release.yml"
ASSURANCE = ROOT / "docs" / "49-coordinate-0.4.1-release-assurance.md"
NOTES = ROOT / "docs" / "releases" / "v0.4.1.md"


def test_coordinate_release_verifies_versions_and_pins_one_release_identity() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "NPM_VERSION=$(node -p" in workflow
    assert "PYTHON_VERSION=$(python" in workflow
    assert "JETBRAINS_VERSION=$(grep '^pluginVersion='" in workflow
    assert 'NOTES="docs/releases/v${NPM_VERSION}.md"' in workflow
    assert 'test "$NPM_VERSION" = "$PYTHON_VERSION"' in workflow
    assert 'test "$JETBRAINS_VERSION" = "$NPM_VERSION-preview"' in workflow
    assert 'test -s "$NOTES"' in workflow
    assert 'echo "tag=v$NPM_VERSION"' in workflow
    assert 'echo "release_sha=$GITHUB_SHA"' in workflow

    assert "Check out immutable release commit" in workflow
    assert "ref: ${{ github.sha }}" in workflow
    assert "fetch-depth: 0" in workflow
    assert "--target \"$RELEASE_SHA\"" in workflow
    assert "--target main" not in workflow
    assert "--ref main" not in workflow


def test_existing_tag_must_match_the_proven_commit() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert 'git show-ref --tags --verify --quiet "refs/tags/$TAG"' in workflow
    assert 'TAG_SHA=$(git rev-list -n 1 "$TAG")' in workflow
    assert 'test "$TAG_SHA" = "$RELEASE_SHA"' in workflow
    assert "Existing tag $TAG points to $TAG_SHA, expected proven commit $RELEASE_SHA." in workflow
    assert "Release $TAG exists without a resolvable matching tag." in workflow
    assert "--verify-tag" in workflow
    assert 'CREATED_TAG_SHA=$(git rev-list -n 1 "$TAG")' in workflow
    assert 'test "$CREATED_TAG_SHA" = "$RELEASE_SHA"' in workflow


def test_new_release_uses_release_event_and_existing_release_recovers_from_tag() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "gh release create \"$TAG\"" in workflow
    assert '--title "Sergeant v$VERSION — Useful Model-Free Baseline"' in workflow
    assert '--notes-file "$NOTES"' in workflow
    assert "if: steps.release.outputs.created == 'false'" in workflow
    assert "if: steps.release.outputs.created == 'true'" in workflow
    assert "gh workflow run publish-vscode-marketplace.yml" in workflow
    assert "gh workflow run publish-pypi.yml" in workflow
    assert "gh workflow run publish-jetbrains-marketplace.yml" in workflow
    assert workflow.count('--ref "$TAG"') == 3
    assert workflow.count('--field release_tag="$TAG"') == 3
    assert "release:published event dispatches all three publishers" in workflow
    assert "duplicate manual dispatch is intentionally skipped" in workflow


def test_coordinate_release_keeps_tokens_isolated_and_checkout_uncredentialed() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "persist-credentials: false" in workflow
    assert "contents: write" in workflow
    assert "actions: write" in workflow
    assert "VSCE_PAT" not in workflow
    assert "OVSX_PAT" not in workflow
    assert "JETBRAINS_MARKETPLACE_TOKEN" not in workflow
    assert "SERGEANT_CPL_API_KEY" not in workflow
    assert "SERGEANT_LLM_API_KEY" not in workflow


def test_coordinate_release_has_explicit_operational_assurance_and_notes() -> None:
    assurance = ASSURANCE.read_text(encoding="utf-8")
    notes = NOTES.read_text(encoding="utf-8")

    assert ".github/workflows/coordinate-release.yml" in assurance
    for heading in ["## Purpose", "## Permissions", "## Secrets", "## Rollback", "## Proof"]:
        assert heading in assurance
    assert "v0.4.1" in assurance
    assert "immutable triggering commit" in assurance
    assert "mismatched existing tag" in assurance
    assert "published registry versions are immutable" in assurance
    assert "Visual Studio Marketplace and Open VSX expose `0.4.1`" in assurance
    assert "PyPI exposes both the `0.4.1` wheel and source distribution" in assurance
    assert "JetBrains publisher accepts or confirms `0.4.1-preview`" in assurance

    assert "# Sergeant 0.4.1 — Useful Model-Free Baseline" in notes
    assert "Useful without an AI account" in notes
    assert "does not include the adaptive self-learning queue" in notes
