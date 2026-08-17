from __future__ import annotations

from pathlib import Path

from main_review.static_checksum_namespace_review import run_static_checksum_namespace_review
from main_review.static_status_review import run_static_status_review


DROP_ROOT = "checksum-manifest-drops-relative-directory"
CWD_ROOT = "checksum-manifest-resolved-from-process-cwd"


def _roots(result: dict) -> set[str]:
    return {str(item.get("root_cause")) for item in result.get("findings", [])}


def _write_workflow(tmp_path: Path, *, artifact: str, command: str = "python3 tools/make_receipt.py") -> str:
    workflow = tmp_path / ".github" / "workflows" / "build.yml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text(
        f'''name: build
jobs:
  build:
    steps:
      - run: |
          OUT="$BUILD_ROOT/out"
          {command} --output-dir "$OUT" --artifact "{artifact}"
          cd "$OUT"
          shasum -a 256 -c SHA256SUMS
''',
        encoding="utf-8",
    )
    return ".github/workflows/build.yml"


def test_bare_checksum_basename_for_nested_artifact_is_reported(tmp_path: Path) -> None:
    producer = tmp_path / "tools" / "make_receipt.py"
    producer.parent.mkdir(parents=True)
    producer.write_text(
        '''from pathlib import Path

def make_record(path: Path):
    return {"filename": path.name, "sha256": sha256_file(path)}

def write_manifest(output_dir: Path, records):
    sums = "\\n".join(f"{item['sha256']}  {item['filename']}" for item in records) + "\\n"
    (output_dir / "SHA256SUMS").write_text(sums)
''',
        encoding="utf-8",
    )
    workflow = _write_workflow(tmp_path, artifact="$OUT/bin/tool")

    result = run_static_checksum_namespace_review(
        tmp_path,
        ["tools/make_receipt.py", workflow],
    )

    assert DROP_ROOT in _roots(result)


def test_explicit_relative_path_for_nested_artifact_is_clean(tmp_path: Path) -> None:
    producer = tmp_path / "tools" / "make_receipt.py"
    producer.parent.mkdir(parents=True)
    producer.write_text(
        '''from pathlib import Path

def make_record(path: Path, relative_path: str):
    return {"filename": path.name, "relative_path": relative_path, "sha256": sha256_file(path)}

def write_manifest(output_dir: Path, records):
    sums = "\\n".join(f"{item['sha256']}  {item['relative_path']}" for item in records) + "\\n"
    (output_dir / "SHA256SUMS").write_text(sums)
''',
        encoding="utf-8",
    )
    workflow = _write_workflow(tmp_path, artifact="$OUT/bin/tool")

    result = run_static_checksum_namespace_review(
        tmp_path,
        ["tools/make_receipt.py", workflow],
    )

    assert DROP_ROOT not in _roots(result)


def test_basename_is_clean_when_artifact_is_colocated_with_manifest(tmp_path: Path) -> None:
    producer = tmp_path / "tools" / "make_receipt.py"
    producer.parent.mkdir(parents=True)
    producer.write_text(
        '''from pathlib import Path

def write_manifest(output_dir: Path, artifact: Path):
    line = f"{sha256_file(artifact)}  {artifact.name}\\n"
    (output_dir / "SHA256SUMS").write_text(line)
''',
        encoding="utf-8",
    )
    workflow = _write_workflow(tmp_path, artifact="$OUT/tool")

    result = run_static_checksum_namespace_review(
        tmp_path,
        ["tools/make_receipt.py", workflow],
    )

    assert DROP_ROOT not in _roots(result)


def test_javascript_bare_basename_transfer_is_reported(tmp_path: Path) -> None:
    producer = tmp_path / "tools" / "make_manifest.js"
    producer.parent.mkdir(parents=True)
    producer.write_text(
        '''export function writeManifest(outputDir, records) {
  const lines = records.map((item) => `${item.sha256}  ${item.filename}`).join("\\n");
  fs.writeFileSync(path.join(outputDir, "SHA256SUMS"), `${lines}\\n`);
}
''',
        encoding="utf-8",
    )
    workflow = _write_workflow(
        tmp_path,
        artifact="$OUT/assets/app.js",
        command="node tools/make_manifest.js",
    )

    result = run_static_checksum_namespace_review(
        tmp_path,
        ["tools/make_manifest.js", workflow],
    )

    assert DROP_ROOT in _roots(result)



def test_display_filename_metadata_far_from_relative_manifest_is_clean(tmp_path: Path) -> None:
    producer = tmp_path / "tools" / "make_receipt.py"
    producer.parent.mkdir(parents=True)
    producer.write_text(
        """from pathlib import Path

def binary_record(path: Path, relative_path: str):
    return {
        "role": "tool",
        "filename": path.name,
        "relative_path": relative_path,
        "byte_len": path.stat().st_size,
        "sha256": sha256_file(path),
        "description": "display metadata only",
    }

def unrelated_receipt_metadata():
    return {
        "builder": "fixture",
        "host": "fixture",
        "source_pins": ["one", "two", "three"],
        "review_checks": {
            "source_commits_exact": True,
            "binaries_nonempty": True,
            "sha256_recorded": True,
        },
    }

def write_manifest(output_dir: Path, records):
    sums = "\\n".join(
        f"{item['sha256']}  {item['relative_path']}" for item in records
    ) + "\\n"
    (output_dir / "SHA256SUMS").write_text(sums)
""",
        encoding="utf-8",
    )
    workflow = _write_workflow(tmp_path, artifact="$OUT/bin/tool")

    result = run_static_checksum_namespace_review(
        tmp_path,
        ["tools/make_receipt.py", workflow],
    )

    assert DROP_ROOT not in _roots(result)


def test_relative_path_metadata_does_not_mask_filename_manifest_entry(tmp_path: Path) -> None:
    producer = tmp_path / "tools" / "make_receipt.py"
    producer.parent.mkdir(parents=True)
    producer.write_text(
        """from pathlib import Path

def binary_record(path: Path, relative_path: str):
    return {
        "filename": path.name,
        "relative_path": relative_path,
        "sha256": sha256_file(path),
    }

def write_manifest(output_dir: Path, records):
    sums = "\\n".join(
        f"{item['sha256']}  {item['filename']}" for item in records
    ) + "\\n"
    (output_dir / "SHA256SUMS").write_text(sums)
""",
        encoding="utf-8",
    )
    workflow = _write_workflow(tmp_path, artifact="$OUT/bin/tool")

    result = run_static_checksum_namespace_review(
        tmp_path,
        ["tools/make_receipt.py", workflow],
    )

    assert DROP_ROOT in _roots(result)

def test_checksum_consumer_resolving_from_process_cwd_is_reported(tmp_path: Path) -> None:
    consumer = tmp_path / "verify.js"
    consumer.write_text(
        '''async function verifyChecksumManifest() {
  const manifest = await fs.readFile("SHA256SUMS", "utf8");
  for (const entry of parseChecksums(manifest)) {
    const target = path.join(process.cwd(), entry.path);
    await verifySha256(target, entry.sha256);
  }
}
''',
        encoding="utf-8",
    )

    result = run_static_checksum_namespace_review(tmp_path, ["verify.js"])

    assert CWD_ROOT in _roots(result)


def test_checksum_consumer_anchored_to_manifest_directory_is_clean(tmp_path: Path) -> None:
    consumer = tmp_path / "verify.py"
    consumer.write_text(
        '''from pathlib import Path

def verify_checksum_manifest(manifest_path: Path):
    manifest = manifest_path.read_text()
    for entry in parse_checksums(manifest):
        target = manifest_path.parent / entry.path
        verify_sha256(target, entry.sha256)
''',
        encoding="utf-8",
    )

    result = run_static_checksum_namespace_review(tmp_path, ["verify.py"])

    assert CWD_ROOT not in _roots(result)
    assert DROP_ROOT not in _roots(result)


def test_static_status_pipeline_exposes_checksum_namespace_finding(tmp_path: Path) -> None:
    producer = tmp_path / "tools" / "make_receipt.py"
    producer.parent.mkdir(parents=True)
    producer.write_text(
        '''from pathlib import Path

def write_manifest(output_dir: Path, records):
    sums = "\\n".join(f"{item['sha256']}  {item['filename']}" for item in records) + "\\n"
    (output_dir / "SHA256SUMS").write_text(sums)
''',
        encoding="utf-8",
    )
    workflow = _write_workflow(tmp_path, artifact="$OUT/bin/tool")

    result = run_static_status_review(tmp_path, ["tools/make_receipt.py", workflow])

    assert DROP_ROOT in _roots(result)
