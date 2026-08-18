#!/usr/bin/env python3
"""Validate post-council project-learning signal terminalization.

A project-driven PR normally changes exactly one round manifest. A follow-up
closeout PR may instead change zero round manifests only when it terminalizes
one or more previously non-terminal signal files to accepted or rejected.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping

TERMINAL_STATES = {"accepted", "rejected"}
SIGNAL_PREFIX = ".github/self-learning/signals/"


class CloseoutValidationError(ValueError):
    """Raised when a signal closeout does not represent a valid terminal transition."""


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _changed_signals(base_sha: str, authority_head: str) -> list[str]:
    completed = _git(
        "diff",
        "--name-only",
        base_sha,
        authority_head,
        "--",
        f"{SIGNAL_PREFIX}*.json",
    )
    return sorted({line.strip() for line in completed.stdout.splitlines() if line.strip()})


def _base_signal(base_sha: str, path: str) -> dict[str, Any]:
    completed = _git("show", f"{base_sha}:{path}", check=False)
    if completed.returncode != 0:
        raise CloseoutValidationError(
            f"terminal signal closeout requires a pre-existing signal on the base: {path}"
        )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise CloseoutValidationError(f"base signal is invalid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise CloseoutValidationError(f"base signal must be a JSON object: {path}")
    return payload


def validate_terminal_transition(
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
    path: str,
) -> dict[str, str]:
    """Validate one non-terminal -> terminal signal transition."""

    if not path.startswith(SIGNAL_PREFIX) or not path.endswith(".json"):
        raise CloseoutValidationError(f"unsafe project-learning signal path: {path}")

    case_id = str(current.get("case_id") or "").strip()
    if not case_id:
        raise CloseoutValidationError(f"terminal signal closeout requires case_id: {path}")
    if str(previous.get("case_id") or "").strip() != case_id:
        raise CloseoutValidationError(f"terminal signal closeout changed case identity: {path}")

    previous_state = str(previous.get("learning_state") or "").strip()
    state = str(current.get("learning_state") or "").strip()
    if previous_state in TERMINAL_STATES:
        raise CloseoutValidationError(
            f"terminal signal closeout cannot replay an already terminal signal: {path}"
        )
    if state not in TERMINAL_STATES:
        raise CloseoutValidationError(
            f"zero-manifest project-learning change must terminalize signal as accepted/rejected: {path}"
        )

    accepted_lesson = current.get("accepted_lesson")
    if state == "accepted":
        if accepted_lesson is not True:
            raise CloseoutValidationError(f"accepted signal must set accepted_lesson=true: {path}")
        lesson_path = str(current.get("accepted_lesson_path") or "").strip()
        if not lesson_path.startswith(".github/self-learning/lessons/"):
            raise CloseoutValidationError(
                f"accepted signal must bind an accepted lesson path: {path}"
            )
    else:
        if accepted_lesson is not False:
            raise CloseoutValidationError(f"rejected signal must set accepted_lesson=false: {path}")
        if not str(current.get("rejection_reason") or "").strip():
            raise CloseoutValidationError(f"rejected signal requires rejection_reason: {path}")

    authority = current.get("authority")
    if not isinstance(authority, Mapping):
        raise CloseoutValidationError(f"terminal signal closeout requires authority: {path}")
    if authority.get("may_auto_promote") is not False or authority.get("may_auto_merge") is not False:
        raise CloseoutValidationError(
            f"terminal signal closeout must preserve no-auto-promotion/no-auto-merge: {path}"
        )
    if authority.get("final_verdict") != "Sergeant":
        raise CloseoutValidationError(f"terminal signal closeout must preserve Sergeant verdict: {path}")

    return {
        "path": path,
        "case_id": case_id,
        "from_state": previous_state or "unset",
        "to_state": state,
    }


def validate_closeout(
    *,
    base_sha: str,
    authority_head: str,
    output_path: Path,
) -> dict[str, Any]:
    signal_paths = _changed_signals(base_sha, authority_head)
    if not signal_paths:
        raise CloseoutValidationError(
            "project-learning validation requires one changed round manifest or at least one terminal signal closeout"
        )

    transitions: list[dict[str, str]] = []
    for path in signal_paths:
        previous = _base_signal(base_sha, path)
        try:
            current = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CloseoutValidationError(f"head signal is unreadable: {path}") from exc
        if not isinstance(current, dict):
            raise CloseoutValidationError(f"head signal must be a JSON object: {path}")
        transitions.append(validate_terminal_transition(previous, current, path))

    payload = {
        "schema_version": "sergeant.project-learning-closeout-validation.v1",
        "authority_head": authority_head,
        "base_sha": base_sha,
        "terminal_signal_count": len(transitions),
        "terminal_signals": transitions,
        "github_inference_enabled": False,
        "automatic_promotions": 0,
        "automatic_merges": 0,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--authority-head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        payload = validate_closeout(
            base_sha=args.base_sha.strip().lower(),
            authority_head=args.authority_head.strip().lower(),
            output_path=args.output,
        )
    except CloseoutValidationError as exc:
        raise SystemExit(str(exc)) from exc

    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
