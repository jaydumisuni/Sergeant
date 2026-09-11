from __future__ import annotations
import json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"docs/121-sae-r2-proven-lifecycle-closeout-manifest.json"
DOC=ROOT/"docs/120-sae-r2-proven-lifecycle-closeout.md"
def load(): return json.loads(MANIFEST.read_text())
def blob(path): return subprocess.check_output(["git","hash-object",str(ROOT/path)],cwd=ROOT,text=True).strip()
def test_exact_candidate_and_guarded_merge_binding():
 m=load(); g=m["candidate_generation"]; merge=m["canonical_candidate_merge"]
 assert m["node"]=="SAE-R2" and m["lifecycle_state"]=="PROVEN"
 assert g["pull_request"]==217 and g["head"]=="c38dd512ddcb2d8c759d034a1d1c32b9b572b10f"
 assert g["tree"]=="0d19d0c91ee986b771e81eb95efcba5016d1057e"
 assert merge["commit"]=="cc3168f6a5b49a5b4c4d49303a0bd5fb35e7b335" and merge["tree"]==g["tree"]
 assert merge["parents"]==["56157e6ed218bbeb532ad714f652adcb0c5c582a",g["head"]]
 assert merge["exact_head_guard"]==g["head"] and merge["authority_gain_at_candidate_merge"]=="none"
def test_candidate_authority_blobs_are_frozen():
 g=load()["candidate_generation"]
 for path,key in [("docs/118-sae-r2-rust-assurance-kernel-candidate.md","candidate_document_blob"),("docs/119-sae-r2-rust-assurance-kernel-candidate-manifest.json","candidate_manifest_blob"),("rust/sergeant-assurance-kernel/src/lib.rs","kernel_blob"),("rust/sergeant-assurance-kernel/tests/structural_authority.rs","structural_campaign_blob"),(".github/workflows/sae-r2-rust-proof.yml","workflow_blob")]: assert blob(path)==g[key]
def test_closeout_advances_only_rust_kernel_authority():
 m=load(); assert m["produces"]==["QUALIFIED_RUST_ASSURANCE_KERNEL"]; assert m["normal_verdict_authority"] is False; assert m["genesis_activated"] is False; assert m["dependent_nodes_auto_proven"] is False; assert m["partial_generation_activation"] is False
def test_document_keeps_downstream_authority_closed():
 text=DOC.read_text(); assert "Status: **PROVEN**" in text and "conditional on this exact closeout generation" in text; assert "QUALIFIED_RUST_ASSURANCE_KERNEL" in text; assert "does **not**" in text and "activate Genesis" in text and "auto-prove SAE-100" in text
