from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(relative: str, old: str, new: str) -> None:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"Expected patch marker not found in {relative}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def append_once(relative: str, marker: str, addition: str) -> None:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    path.write_text(text.rstrip() + "\n\n\n" + addition.strip() + "\n", encoding="utf-8")


replace_once(
    "main_review/workspace_interfaces.py",
    '''def _validate_adapter_evidence(
    result: dict[str, Any],
    task: dict[str, Any],
    *,
    adapter_name: str,
    research: bool,
) -> dict[str, Any] | None:
''',
    '''def _validate_adapter_evidence(
    result: dict[str, Any],
    request: dict[str, Any],
    task: dict[str, Any],
    *,
    adapter_name: str,
    research: bool,
) -> dict[str, Any] | None:
''',
)
replace_once(
    "main_review/workspace_interfaces.py",
    '''    if provenance.get("adapter") != adapter_name:
        raise ValueError("adapter evidence provenance does not match the executing adapter")
    return validate_evidence_packet(packet, task)
''',
    '''    if provenance.get("adapter") != adapter_name:
        raise ValueError("adapter evidence provenance does not match the executing adapter")
    if research:
        allowed_sources = {
            str(item).strip()
            for item in request.get("allowed_sources", [])
            if str(item).strip()
        }
        source = str(provenance.get("source") or "").strip()
        if source not in allowed_sources:
            raise ValueError("research evidence source is not authorized by the originating request")
    return validate_evidence_packet(packet, task)
''',
)
replace_once(
    "main_review/workspace_interfaces.py",
    '''            packet = _validate_adapter_evidence(result, task, adapter_name=workspace.name, research=False)
''',
    '''            packet = _validate_adapter_evidence(
                result,
                request,
                task,
                adapter_name=workspace.name,
                research=False,
            )
''',
)
replace_once(
    "main_review/workspace_interfaces.py",
    '''            packet = _validate_adapter_evidence(result, task, adapter_name=research.name, research=True)
''',
    '''            packet = _validate_adapter_evidence(
                result,
                request,
                task,
                adapter_name=research.name,
                research=True,
            )
''',
)

replace_once(
    "main_review/offline_investigation.py",
    '''        replacements: list[tuple[int, str]] = []
        for match in re.finditer(r"(?:os\\.)?replace\\s*\\(\\s*([^,\\n]+)\\s*,", body):
            replacements.append((match.start(), match.group(1).strip()))
        for match in re.finditer(r"\\b([A-Za-z_][A-Za-z0-9_]*)\\.replace\\s*\\(", body):
            replacements.append((match.start(), match.group(1)))
        if not replacements:
            continue

        non_durable: list[str] = []
        for replace_pos, source in sorted(replacements):
            normalized = source.strip()
            handle: str | None = None
''',
    '''        path_objects: dict[str, str] = {}
        for match in re.finditer(
            r"(?m)^\\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*"
            r"(?:pathlib\\.)?Path\\s*\\(\\s*(?P<source>[^)\\n]+)\\s*\\)",
            body,
        ):
            path_objects[match.group("name")] = match.group("source").strip()
        for match in re.finditer(
            r"(?m)^\\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*"
            r"[A-Za-z_][A-Za-z0-9_]*\\.__class__\\s*\\(\\s*(?P<source>[^)\\n]+)\\s*\\)",
            body,
        ):
            path_objects[match.group("name")] = match.group("source").strip()
        for match in re.finditer(
            r"(?m)^\\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*"
            r"(?P<source>[A-Za-z_][A-Za-z0-9_]*\\.(?:with_suffix|with_name|resolve|absolute)\\s*\\([^\\n]*\\))",
            body,
        ):
            path_objects[match.group("name")] = match.group("source").strip()

        replacements: list[tuple[int, str]] = []
        for match in re.finditer(
            r"(?:\\bos\\.replace|(?<![.\\w])replace)\\s*\\(\\s*([^,\\n]+)\\s*,",
            body,
        ):
            replacements.append((match.start(), match.group(1).strip()))
        for match in re.finditer(r"\\b([A-Za-z_][A-Za-z0-9_]*)\\.replace\\s*\\(", body):
            receiver = match.group(1)
            if receiver in path_objects:
                replacements.append((match.start(), receiver))
        if not replacements:
            continue

        non_durable: list[str] = []
        last_replace_by_identity: dict[str, int] = {}
        for replace_pos, source in sorted(replacements):
            normalized = source.strip()
            if normalized in path_objects:
                normalized = path_objects[normalized]
            handle: str | None = None
''',
)
replace_once(
    "main_review/offline_investigation.py",
    '''            if handle is not None:
                write_positions = [
''',
    '''            if handle is not None:
                identity = f"handle:{handle}"
                boundary = last_replace_by_identity.get(identity, -1)
                write_positions = [
''',
)
replace_once(
    "main_review/offline_investigation.py",
    '''                durable = any(
                    write < flush < fsync < replace_pos
                    for write in write_positions
                    for flush in flush_positions
                    for fsync in fsync_positions
                )
            elif normalized in fd_paths:
                fd = fd_paths[normalized]
''',
    '''                durable = any(
                    boundary < write < flush < fsync < replace_pos
                    for write in write_positions
                    for flush in flush_positions
                    for fsync in fsync_positions
                )
            elif normalized in fd_paths:
                fd = fd_paths[normalized]
                identity = f"fd:{fd}"
                boundary = last_replace_by_identity.get(identity, -1)
''',
)
replace_once(
    "main_review/offline_investigation.py",
    '''                durable = any(write < fsync < replace_pos for write in writes for fsync in fsyncs)
            else:
                durable = False

            if not durable:
                non_durable.append(source)
''',
    '''                durable = any(
                    boundary < write < fsync < replace_pos
                    for write in writes
                    for fsync in fsyncs
                )
            else:
                identity = f"source:{normalized}"
                durable = False

            last_replace_by_identity[identity] = replace_pos
            if not durable:
                non_durable.append(source)
''',
)

append_once(
    "tests/test_workspace_ready_campaign.py",
    "def test_research_evidence_rejects_source_outside_request_allowlist",
    '''def test_research_evidence_rejects_source_outside_request_allowlist(tmp_path: Path) -> None:
    campaign = _campaign(tmp_path)

    class UnauthorizedSourceResearch:
        name = "unauthorized-source-research"

        def capabilities(self) -> set[str]:
            return {"research"}

        def lookup(self, request: dict, task: dict) -> dict:
            return {
                "request_id": request["request_id"],
                "task_id": task["task_id"],
                "evidence_packet": evidence_packet(
                    mission_id=task["mission_id"],
                    task_id=task["task_id"],
                    worker_id="Research-Unauthorized",
                    claims=({"claim": "unapproved source checked"},),
                    evidence_refs=("https://unapproved.invalid/report",),
                    provenance={
                        "adapter": self.name,
                        "observed_at": "2026-07-17T00:00:00Z",
                        "source": "unapproved_blog",
                        "retrieved_at": "2026-07-17T00:00:00Z",
                        "supported_claim": "unapproved source checked",
                        "freshness": "current",
                    },
                    confidence=0.8,
                ),
            }

    result = dispatch_authorized_requests(campaign, research=UnauthorizedSourceResearch())
    assert result["research_results"][0]["status"] == "failed"
    assert result["evidence_packets"] == []


def test_research_evidence_accepts_source_inside_request_allowlist(tmp_path: Path) -> None:
    campaign = _campaign(tmp_path)
    allowed_source = campaign["research_requests"][0]["allowed_sources"][0]

    class AuthorizedSourceResearch:
        name = "authorized-source-research"

        def capabilities(self) -> set[str]:
            return {"research"}

        def lookup(self, request: dict, task: dict) -> dict:
            return {
                "request_id": request["request_id"],
                "task_id": task["task_id"],
                "evidence_packet": evidence_packet(
                    mission_id=task["mission_id"],
                    task_id=task["task_id"],
                    worker_id="Research-Authorized",
                    claims=({"claim": "authorized source checked"},),
                    evidence_refs=("https://official.invalid/reference",),
                    provenance={
                        "adapter": self.name,
                        "observed_at": "2026-07-17T00:00:00Z",
                        "source": allowed_source,
                        "retrieved_at": "2026-07-17T00:00:00Z",
                        "supported_claim": "authorized source checked",
                        "freshness": "current",
                    },
                    confidence=0.8,
                ),
            }

    result = dispatch_authorized_requests(campaign, research=AuthorizedSourceResearch())
    assert result["research_results"][0].get("status") != "failed"
    assert len(result["evidence_packets"]) == 1
''',
)

append_once(
    "tests/test_coderabbit_rematch_regressions.py",
    "def test_string_replace_is_not_treated_as_atomic_file_publication",
    '''def test_string_replace_is_not_treated_as_atomic_file_publication(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/text.py",
        """def normalize(value):
    return value.replace('old', 'new')
""",
    )

    result = run_offline_investigations(tmp_path, ["src/text.py"])

    assert not any(item["root_cause"] == "atomic-replace-durability" for item in result["findings"])


def test_each_publication_requires_a_fresh_durability_sequence(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/ledger.py",
        """import os
import tempfile


def publish_twice(first, second, payload):
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = first.__class__(handle.name)
    temporary.replace(first)
    temporary.replace(second)
""",
    )

    result = run_offline_investigations(tmp_path, ["src/ledger.py"])

    findings = [item for item in result["findings"] if item["root_cause"] == "atomic-replace-durability"]
    assert len(findings) == 1
    assert "temporary" in findings[0]["evidence"]


def test_independent_temporary_publications_each_with_own_sequence_are_clean(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/ledger.py",
        """import os
import tempfile


def publish_two(first, second, payload):
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as first_handle:
        first_handle.write(payload)
        first_handle.flush()
        os.fsync(first_handle.fileno())
        first_temp = first.__class__(first_handle.name)
    first_temp.replace(first)
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as second_handle:
        second_handle.write(payload)
        second_handle.flush()
        os.fsync(second_handle.fileno())
        second_temp = second.__class__(second_handle.name)
    second_temp.replace(second)
""",
    )

    result = run_offline_investigations(tmp_path, ["src/ledger.py"])

    assert not any(item["root_cause"] == "atomic-replace-durability" for item in result["findings"])
''',
)

for relative in (
    "scripts/apply_final_workspace_rematch.py",
    "scripts/postfix_workspace_rematch_product.py",
    ".github/workflows/apply-final-rematch-repair.yml",
):
    (ROOT / relative).unlink(missing_ok=True)
