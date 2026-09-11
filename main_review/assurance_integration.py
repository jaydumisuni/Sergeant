from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

SHADOW_MODE = "SHADOW_OR_QUALIFICATION_ONLY"
_AUTHORITY_OWNERS = {
    "schedule": "Cpl",
    "specialist": "Officers",
    "falsification": "Challenger",
    "admission": "Judge",
    "constitutional_admissibility": "Rust",
    "engineering_verdict": "Sergeant",
}

@dataclass(frozen=True)
class AssuranceCampaign:
    mode: str
    open_frontier: tuple[str, ...]
    authority_owners: dict[str, str]
    review_world: Mapping[str, Any]
    registry: Mapping[str, Any]
    ledger: Mapping[str, Any]
    capabilities: Mapping[str, Any]
    proof_world: Mapping[str, Any]
    falsification: Mapping[str, Any]
    genesis_activated: bool = False

@dataclass(frozen=True)
class ShadowAssuranceResult:
    mode: str
    status: str
    admissible: bool | None
    genesis_activated: bool = False
    normal_verdict_override: None = None

def compile_assurance_frontier(review_world, registry, ledger, capabilities, proof_world, falsification) -> AssuranceCampaign:
    deps = {"review_world": review_world, "registry": registry, "ledger": ledger, "capabilities": capabilities, "proof_world": proof_world, "falsification": falsification}
    for name, value in deps.items():
        if value is None:
            raise ValueError(f"missing assurance dependency: {name}")
    if review_world.get("authority_owner") not in (None, "Sergeant"):
        raise ValueError("engineering verdict authority inversion")
    if ledger.get("judge_admission_required") is not True:
        raise ValueError("Judge admission cannot be bypassed")
    if falsification.get("challenger_owned") is not True:
        raise ValueError("Challenger falsification ownership required")
    frontier = tuple(str(item) for item in review_world.get("open_assurance_frontier", ()) if str(item))
    return AssuranceCampaign(SHADOW_MODE, frontier, dict(_AUTHORITY_OWNERS), review_world, registry, ledger, capabilities, proof_world, falsification)

def run_shadow_assurance(campaign: AssuranceCampaign, rust_kernel: Callable[[AssuranceCampaign], Mapping[str, Any]]) -> ShadowAssuranceResult:
    if campaign.mode != SHADOW_MODE or campaign.genesis_activated:
        raise ValueError("assurance campaign attempted accidental activation")
    raw = dict(rust_kernel(campaign))
    if any(key in raw for key in ("verdict", "engineering_verdict", "normal_verdict_override")):
        raise ValueError("Rust kernel attempted verdict authority")
    admissible = raw.get("admissible")
    if admissible not in (True, False, None):
        raise ValueError("invalid Rust admissibility result")
    status = str(raw.get("status") or ("QUALIFIED" if admissible is True else "REJECTED" if admissible is False else "UNKNOWN")).upper()
    if status not in {"QUALIFIED", "REJECTED", "UNKNOWN"}:
        raise ValueError("unknown assurance status")
    if admissible is None:
        status = "UNKNOWN"
    return ShadowAssuranceResult(SHADOW_MODE, status, admissible)
