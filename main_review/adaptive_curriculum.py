"""Evidence-gated multilingual curriculum planning for Sergeant."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .operational_contracts import private_force_size

SCHEMA_VERSION = "sergeant.adaptive-curriculum.v1"
MIN_PROMOTION_SAMPLES = 3
PROMOTION_RECALL = 0.80
MAX_FALSE_POSITIVE_RATE = 0.10
MAX_RUST_PER_TEN = 2


@dataclass(frozen=True)
class DifficultyTier:
    name: str
    files: int | None
    lines: int | None
    packages: int | None
    depth: int | None


TIERS: tuple[DifficultyTier, ...] = (
    DifficultyTier("focused", 4, 500, 1, 2),
    DifficultyTier("component", 12, 2_500, 2, 4),
    DifficultyTier("subsystem", 30, 8_000, 4, 6),
    DifficultyTier("system", 100, 25_000, 10, 10),
    DifficultyTier("large-system", None, None, None, None),
)

ALIASES = {
    "c++": "cpp", "cxx": "cpp", "objective-c": "objective_c",
    "objective c": "objective_c", "c#": "csharp", "f#": "fsharp",
    "js": "javascript", "ts": "typescript", "golang": "go",
}
FAMILIES = {
    "rust": "systems", "c": "systems", "cpp": "systems", "zig": "systems", "go": "systems",
    "swift": "native-mobile", "objective_c": "native-mobile",
    "kotlin": "managed", "java": "managed", "scala": "managed", "csharp": "managed",
    "javascript": "web-runtime", "typescript": "web-runtime", "dart": "web-runtime",
    "python": "dynamic", "ruby": "dynamic", "perl": "dynamic", "php": "dynamic", "lua": "dynamic",
    "elixir": "functional-runtime", "erlang": "functional-runtime",
    "ocaml": "functional", "fsharp": "functional", "haskell": "functional", "clojure": "functional",
    "julia": "scientific", "r": "scientific", "nim": "compiled-multiparadigm", "crystal": "compiled-multiparadigm",
}


def normalize_language(value: object) -> str:
    language = str(value or "unknown").strip().lower().replace("-", "_")
    return ALIASES.get(language, language)


def language_family(value: object) -> str:
    language = normalize_language(value)
    return FAMILIES.get(language, f"other:{language}")


def _within(value: int, maximum: int | None) -> bool:
    return maximum is None or value <= maximum


def repository_difficulty(candidate: Mapping[str, Any]) -> int:
    files = max(1, int(candidate.get("changed_files", 1) or 1))
    lines = max(1, int(candidate.get("changed_lines", 1) or 1))
    packages = max(1, int(candidate.get("package_count", 1) or 1))
    depth = max(0, int(candidate.get("dependency_depth", 0) or 0))
    tier = len(TIERS) - 1
    for index, limit in enumerate(TIERS):
        if all((
            _within(files, limit.files), _within(lines, limit.lines),
            _within(packages, limit.packages), _within(depth, limit.depth),
        )):
            tier = index
            break
    semantic = any((
        bool(candidate.get("cross_component")),
        bool(candidate.get("concurrency_or_lifecycle")),
        float(candidate.get("defect_novelty", 0.0) or 0.0) >= 0.75,
    ))
    return min(len(TIERS) - 1, tier + int(semantic))


def performance_window(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    window = list(results[-MIN_PROMOTION_SAMPLES:])
    confirmed = found = false_positives = 0
    integrity = bool(window)
    for row in window:
        row_confirmed = max(0, int(row.get("confirmed_defects", 0) or 0))
        confirmed += row_confirmed
        found += min(row_confirmed, max(0, int(row.get("confirmed_defects_found", 0) or 0)))
        false_positives += max(0, int(row.get("false_positives", 0) or 0))
        integrity = integrity and row.get("provenance_complete") is True
        integrity = integrity and row.get("evidence_integrity") is True
    claims = found + false_positives
    return {
        "sample_count": len(window),
        "confirmed_defects": confirmed,
        "confirmed_defects_found": found,
        "false_positives": false_positives,
        "recall": found / confirmed if confirmed else 0.0,
        "false_positive_rate": false_positives / claims if claims else 0.0,
        "integrity_complete": integrity,
    }


def next_difficulty_tier(current_tier: int, recent_results: Sequence[Mapping[str, Any]]) -> int:
    current = max(0, min(len(TIERS) - 1, int(current_tier)))
    metrics = performance_window(recent_results)
    qualified = (
        metrics["sample_count"] >= MIN_PROMOTION_SAMPLES
        and metrics["confirmed_defects"] > 0
        and metrics["recall"] >= PROMOTION_RECALL
        and metrics["false_positive_rate"] <= MAX_FALSE_POSITIVE_RATE
        and metrics["integrity_complete"] is True
    )
    return min(len(TIERS) - 1, current + 1) if qualified else current


def human_equivalent_workers(candidate: Mapping[str, Any]) -> int:
    workers = 2 + repository_difficulty(candidate) * 2
    workers += int(bool(candidate.get("cross_component")))
    workers += int(bool(candidate.get("concurrency_or_lifecycle")))
    workers += int(float(candidate.get("defect_novelty", 0.0) or 0.0) >= 0.75)
    return max(2, min(12, workers))


def _allowed(language: str, history: Sequence[str]) -> bool:
    normalized = [normalize_language(item) for item in history]
    if normalized and normalized[-1] == language:
        return False
    if language == "rust" and normalized[-10:].count("rust") >= MAX_RUST_PER_TEN:
        return False
    family = language_family(language)
    if [language_family(item) for item in normalized[-5:]].count(family) >= 2:
        return False
    return True


def select_multilingual_candidates(
    candidates: Iterable[Mapping[str, Any]], *, target_tier: int,
    language_history: Sequence[str], count: int = 3,
) -> list[dict[str, Any]]:
    required = max(0, min(len(TIERS) - 1, int(target_tier)))
    remaining = [dict(row) for row in candidates if row.get("provenance_complete") is True and repository_difficulty(row) >= required]
    history = [normalize_language(item) for item in language_history]
    selected: list[dict[str, Any]] = []
    while remaining and len(selected) < max(1, int(count)):
        remaining.sort(key=lambda row: (
            repository_difficulty(row) - required,
            -float(row.get("defect_novelty", 0.0) or 0.0),
            -int(row.get("changed_files", 0) or 0),
            str(row.get("repository") or ""),
        ))
        position = next((index for index, row in enumerate(remaining) if _allowed(normalize_language(row.get("language")), history)), None)
        if position is None:
            break
        row = remaining.pop(position)
        language = normalize_language(row.get("language"))
        tier = repository_difficulty(row)
        human_workers = human_equivalent_workers(row)
        row.update({
            "language": language,
            "language_family": language_family(language),
            "difficulty_tier": tier,
            "difficulty_name": TIERS[tier].name,
            "human_equivalent_workers": human_workers,
            "private_count": private_force_size(human_workers),
        })
        selected.append(row)
        history.append(language)
    return selected


def plan_curriculum_round(
    *, candidates: Iterable[Mapping[str, Any]], current_tier: int,
    recent_results: Sequence[Mapping[str, Any]], language_history: Sequence[str], count: int = 3,
) -> dict[str, Any]:
    target = next_difficulty_tier(current_tier, recent_results)
    selected = select_multilingual_candidates(candidates, target_tier=target, language_history=language_history, count=count)
    return {
        "schema_version": SCHEMA_VERSION,
        "current_tier": max(0, min(len(TIERS) - 1, int(current_tier))),
        "target_tier": target,
        "target_difficulty": TIERS[target].name,
        "promotion_metrics": performance_window(recent_results),
        "language_policy": {"same_language_consecutively": False, "max_same_family_per_five": 2, "max_rust_per_ten": MAX_RUST_PER_TEN},
        "cases": selected,
        "candidate_shortfall": len(selected) < max(1, int(count)),
        "planned_private_count": sum(int(row["private_count"]) for row in selected),
        "authority": {"may_promote_lessons": False, "may_merge": False, "final_verdict": "Sergeant"},
    }
