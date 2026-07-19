#!/usr/bin/env python3
"""Validate a frozen review-training manifest before Sergeant sees the targets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from main_review.training_manifest_provenance import (
    ProvenanceError,
    validate_training_manifest,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        result = validate_training_manifest(manifest)
    except (OSError, json.JSONDecodeError, ProvenanceError) as exc:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "error": str(exc),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2

    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
