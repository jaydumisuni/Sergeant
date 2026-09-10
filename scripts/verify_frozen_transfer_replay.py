from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ALLOWED_REPLAY_DRIFT = (
    'docs/108-sae70-proven-lifecycle-closeout.md',
    'docs/109-sae70-proven-lifecycle-closeout-manifest.json',
    'docs/110-sae80-evidence-proof-world-candidate.md',
    'docs/111-sae80-evidence-proof-world-candidate-manifest.json',
    'docs/112-sae90-mandatory-falsification-candidate.md',
    'docs/113-sae90-mandatory-falsification-candidate-manifest.json',
    'docs/112-sae80-proven-lifecycle-closeout.md',
    'docs/113-sae80-proven-lifecycle-closeout-manifest.json',
    'docs/114-sae90-falsification-frontier-candidate.md',
    'docs/115-sae90-falsification-frontier-candidate-manifest.json',
    'main_review/proof_world.py',
    'main_review/proof_world_authority.py',
    'main_review/proof_world_protocol.py',
    'main_review/falsification_frontier.py',
    'main_review/falsification_frontier_protocol.py',
    'tests/sae80_authority_fixtures.py',
    'tests/test_proof_world.py',
    'tests/test_sae70_proven_lifecycle_closeout.py',
    'tests/test_sae80_authority_hardening.py',
    'tests/test_sae80_derived_qualification_forgery.py',
    'tests/test_sae80_qualified_authority_path.py',
    'tests/test_sae80_qualification_campaign.py',
    'tests/test_sae90_falsification_campaign.py',
    'tests/test_sae90_candidate_record_integrity.py',
    'tests/test_sae90_qualification_campaign.py',
    'tests/test_sae80_proven_lifecycle_closeout.py',
    'tests/test_main_review_workflow_merge_base.py',
    '.github/workflows/main-review.yml',
    '.github/workflows/model-free-core-auth-transfer-7.yml',
    '.github/workflows/model-free-core-await-transfer-5.yml',
    'scripts/verify_frozen_transfer_replay.py',
    'tests/test_frozen_transfer_durable_replay.py',
    'evidence/frozen-transfer-replay/',
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_changed_paths(paths: list[str], allowed: list[str] | tuple[str, ...]) -> None:
    bad = [p for p in paths if not any(p == a or (a.endswith('/') and p.startswith(a)) for a in allowed)]
    if bad:
        raise ValueError('replay forbidden: review-engine or unrelated drift detected: ' + ', '.join(sorted(bad)))


def validate_archive(root: Path, rec: dict) -> None:
    for name, meta in rec['files'].items():
        path = root / meta['path']
        if not path.is_file():
            raise ValueError(f'missing archived evidence: {path}')
        if path.stat().st_size != meta['bytes']:
            raise ValueError(f'archive size mismatch: {path}')
        if sha256(path) != meta['sha256']:
            raise ValueError(f'archive digest mismatch: {path}')
    runtime = json.loads((root / rec['files']['runtime-manifest.json']['path']).read_text())
    result = json.loads((root / rec['files']['frozen-result.json']['path']).read_text())
    if runtime['set_id'] != result['set_id']:
        raise ValueError('archive set mismatch')
    cases = runtime['cases']
    match = [c for c in cases if c['repository'] == rec['fixture_repository']]
    if len(match) != 1:
        raise ValueError('archived fixture repository mismatch')
    case = match[0]
    if case['fixing_ref'] != rec['fixture_fixing_ref'] or case['defective_ref'] != rec['fixture_defective_ref']:
        raise ValueError('archived fixture lineage mismatch')
    if result.get('case_count') != len(runtime['cases']):
        raise ValueError('archived case count mismatch')
    if any(item.get('result', {}).get('unavailable_requested_files') for item in result.get('full_results', [])):
        raise ValueError('archived run had unavailable requested files')


def git_changed_paths(root: Path, baseline: str) -> list[str]:
    out = subprocess.check_output(['git', 'diff', '--name-only', f'{baseline}..HEAD'], cwd=root, text=True)
    return [line.strip() for line in out.splitlines() if line.strip()]


def replay(root: Path, set_id: str, output: Path) -> dict:
    manifest = json.loads((root / 'evidence/frozen-transfer-replay/manifest.json').read_text())
    rec = manifest['sets'][set_id]
    validate_archive(root, rec)
    changed = git_changed_paths(root, rec['source_head'])
    validate_changed_paths(changed, ALLOWED_REPLAY_DRIFT)
    output.mkdir(parents=True, exist_ok=True)
    for name, meta in rec['files'].items():
        shutil.copy2(root / meta['path'], output / name)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    attestation = {
        'schema': 'sergeant.frozen-transfer-replay-attestation.v1',
        'set_id': set_id,
        'mode': 'durable_exact_artifact_replay',
        'current_head': head,
        'source_success_head': rec['source_head'],
        'source_run_id': rec['source_run_id'],
        'source_artifact_id': rec['artifact_id'],
        'source_artifact_digest': rec['artifact_digest'],
        'unavailable_fixture_repository': rec['fixture_repository'],
        'unavailable_fixture_fixing_ref': rec['fixture_fixing_ref'],
        'changed_paths_from_source_success': changed,
        'claim': 'Historical exact successful transfer evidence replayed because its frozen external fixture is unavailable. This is not a fresh execution.',
    }
    (output / 'replay-attestation.json').write_text(json.dumps(attestation, indent=2, sort_keys=True) + '\n')
    return attestation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--set-id', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    print(json.dumps(replay(root, args.set_id, root / args.output), indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
