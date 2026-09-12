from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DOC=ROOT/"docs/122-sae100-integration-candidate.md"

def test_sae100_construction_marker_has_no_authority_gain():
    text=DOC.read_text(encoding="utf-8")
    assert "Status: **CANDIDATE CONSTRUCTION**" in text
    assert "No qualification, verdict, Genesis, or downstream authority is created here." in text
    assert "SHADOW_OR_QUALIFICATION_ONLY" in text
    assert "Sergeant alone owns the final automated engineering verdict" in text
    assert "separate PROVEN lifecycle closeout" in text
