from pathlib import Path


def test_kilocode_is_recorded_as_donor_without_replacing_sergeant():
    text = Path("docs/01-research-sources.md").read_text(encoding="utf-8")

    assert "https://github.com/Kilo-Org/kilocode" in text
    assert "https://github.com/jaydumisuni/kilocode" in text
    assert "pin the exact mirror commit" in text
    assert "docs/51-cross-repository-learning-intake.md" in text
    assert "owner-controlled promotion gates" in text
    assert "not a replacement for Sergeant" in text
    assert "preserve Sergeant as the independent engineering reviewer" in text
    assert "do not replace Sergeant with KiloCode" in text
