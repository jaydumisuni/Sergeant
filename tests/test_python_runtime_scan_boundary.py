from __future__ import annotations

from pathlib import Path

from main_review.static_checksum_namespace_review import run_static_checksum_namespace_review


CWD_ROOT = "checksum-manifest-resolved-from-process-cwd"


def _roots(result: dict) -> set[str]:
    return {str(item.get("root_cause")) for item in result.get("findings", [])}


def test_python_fixture_literal_with_process_cwd_is_not_runtime_code(tmp_path: Path) -> None:
    test_file = tmp_path / "tests" / "test_generated_verifier.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(
        '''from pathlib import Path

def test_generated_verifier(tmp_path: Path):
    consumer = tmp_path / "verify.js"
    consumer.write_text(
        "async function verifyChecksumManifest() {\\n"
        "  const manifest = await fs.readFile('SHA256SUMS', 'utf8');\\n"
        "  const target = path.join(process.cwd(), entry.path);\\n"
        "}\\n",
        encoding="utf-8",
    )
''',
        encoding="utf-8",
    )

    result = run_static_checksum_namespace_review(
        tmp_path,
        ["tests/test_generated_verifier.py"],
    )

    assert CWD_ROOT not in _roots(result)


def test_python_executable_cwd_checksum_resolution_is_reported(tmp_path: Path) -> None:
    verifier = tmp_path / "verify.py"
    verifier.write_text(
        '''from pathlib import Path

def verify_checksum_manifest(entries):
    manifest = Path("SHA256SUMS").read_text()
    for entry in entries:
        target = Path.cwd() / entry.path
        verify_sha256(target, entry.sha256)
''',
        encoding="utf-8",
    )

    result = run_static_checksum_namespace_review(tmp_path, ["verify.py"])

    assert CWD_ROOT in _roots(result)


def test_python_comment_with_cwd_example_is_not_runtime_code(tmp_path: Path) -> None:
    verifier = tmp_path / "verify.py"
    verifier.write_text(
        '''from pathlib import Path

def verify_checksum_manifest(manifest_path: Path):
    # Never resolve SHA256SUMS entries with process.cwd(); use the manifest base.
    manifest = manifest_path.read_text()
    for entry in parse_checksums(manifest):
        target = manifest_path.parent / entry.path
        verify_sha256(target, entry.sha256)
''',
        encoding="utf-8",
    )

    result = run_static_checksum_namespace_review(tmp_path, ["verify.py"])

    assert CWD_ROOT not in _roots(result)
