from __future__ import annotations

from pathlib import Path

from main_review.capability_engine import run_capability_engine
from main_review.pr_reviewer import render_pr_review_markdown, run_independent_pr_review


def _write_project(root: Path) -> None:
    (root / "package.json").write_text('{"scripts":{"test":"node tests/test_api.js"}}\n', encoding="utf-8")
    (root / "README.md").write_text("# Demo\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "db.js").write_text(
        "export function queryDb(sql) { return query(sql); }\n",
        encoding="utf-8",
    )
    (root / "src" / "api.js").write_text(
        "import { queryDb } from './db';\n"
        "export function getUser(req) {\n"
        "  const sql = `SELECT * FROM users WHERE id=${req.query.id}`;\n"
        "  return queryDb(sql);\n"
        "}\n"
        "app.get('/users/:id', getUser);\n",
        encoding="utf-8",
    )
    (root / "src" / "client.js").write_text(
        "export async function loadUser() { return fetch('/users/1'); }\n",
        encoding="utf-8",
    )
    (root / "tests").mkdir()
    (root / "tests" / "test_api.js").write_text("assert.ok(true);\n", encoding="utf-8")


def test_capability_engine_reports_tier1_signals(tmp_path: Path) -> None:
    _write_project(tmp_path)

    report = run_capability_engine(tmp_path, changed_files=["src/db.js", "src/api.js"])

    assert report["verdict"] in {"NEEDS WORK", "BLOCK"}
    assert report["capability_status"]["cross_file"] == "active"
    assert report["capability_status"]["data_flow"] == "active"
    assert report["capability_status"]["call_graph"] == "active"
    capabilities = {finding["capability"] for finding in report["findings"]}
    assert "security_taint" in capabilities
    assert "api_contract" in capabilities
    assert "test_impact" in capabilities


def test_performance_finding_ignores_prose_comment_mentioning_for_twice(tmp_path: Path) -> None:
    """Regression for a real false positive: the performance detector
    used to be a raw-text regex matching any two occurrences of the word
    "for" within 160 characters, including inside comments/docstrings."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "notes.py").write_text(
        "# tionally exists -- confirmed concretely for SC-23\n"
        "# below. Each condition below is genuinely, functionally exercised:\n"
        "# where a dedicated Trust Table row exists for the artifact, admission\n"
        "# is checked via something else entirely\n"
        "def f():\n    return 1\n",
        encoding="utf-8",
    )

    report = run_capability_engine(tmp_path, changed_files=["src/notes.py"])

    assert not any(finding["capability"] == "performance" for finding in report["findings"])


def test_performance_finding_ignores_two_adjacent_unrelated_comprehensions(tmp_path: Path) -> None:
    """Regression for a real false positive: two separate, independent,
    single-level comprehensions sitting near each other in source are not
    nested iteration, even though they each contain the word "for"."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "build.py").write_text(
        "def build(RequirementClass, ObligationClass):\n"
        "    obl = {rc: (rc.value,) for rc in RequirementClass}\n"
        "    obl_to_predicates = {oc: (oc.value,) for oc in ObligationClass}\n"
        "    return obl, obl_to_predicates\n",
        encoding="utf-8",
    )

    report = run_capability_engine(tmp_path, changed_files=["src/build.py"])

    assert not any(finding["capability"] == "performance" for finding in report["findings"])


def test_performance_finding_still_detects_genuine_nested_python_loop(tmp_path: Path) -> None:
    """A real for-loop directly containing another for-loop must still be
    flagged -- the fix must not create a false negative."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "report.py").write_text(
        "def pairs(rows):\n"
        "    for left in rows:\n"
        "        for right in rows:\n"
        "            yield left, right\n",
        encoding="utf-8",
    )

    report = run_capability_engine(tmp_path, changed_files=["src/report.py"])

    assert any(finding["capability"] == "performance" for finding in report["findings"])


def test_performance_finding_still_detects_multi_generator_comprehension(tmp_path: Path) -> None:
    """A single comprehension with two generators is genuine O(n*m) and
    must still be flagged."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "pairs.py").write_text(
        "def pairs(a, b):\n    return [x for x in a for y in b]\n",
        encoding="utf-8",
    )

    report = run_capability_engine(tmp_path, changed_files=["src/pairs.py"])

    assert any(finding["capability"] == "performance" for finding in report["findings"])


def test_performance_finding_ignores_rust_doc_comment_mentioning_for_twice(tmp_path: Path) -> None:
    """Regression for a real false positive found in Rust doc comments
    (``///``), which the old raw-text regex could not distinguish from
    real nested loop code."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "lib.rs").write_text(
        "/// The Trust Table row for this crate's whole artifact family. Each\n"
        "/// artifact family has its own row, checked before admission for use.\n"
        "fn admitted() -> bool { true }\n",
        encoding="utf-8",
    )

    report = run_capability_engine(tmp_path, changed_files=["src/lib.rs"])

    assert not any(finding["capability"] == "performance" for finding in report["findings"])


def test_performance_finding_still_detects_genuine_nested_brace_language_loop(tmp_path: Path) -> None:
    """A real nested for-loop in a brace language (e.g. Rust) must still
    be flagged."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "lib.rs").write_text(
        "fn pairs(rows: &Vec<i32>) {\n"
        "    for left in rows {\n"
        "        for right in rows {\n"
        "            println!(\"{} {}\", left, right);\n"
        "        }\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )

    report = run_capability_engine(tmp_path, changed_files=["src/lib.rs"])

    assert any(finding["capability"] == "performance" for finding in report["findings"])


def test_sergeant_review_includes_capability_review(tmp_path: Path) -> None:
    _write_project(tmp_path)
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")

    packet = run_independent_pr_review(tmp_path, changed_files=["src/api.js"])
    rendered = render_pr_review_markdown(packet)

    assert "capability_review" in packet
    assert packet["capability_review"]["capability_status"]["api_contract"] == "active"
    assert "Tier 1 capabilities" in rendered
    assert "Sergeant Review" in rendered
