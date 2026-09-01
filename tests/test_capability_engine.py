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


def test_performance_finding_detects_comprehension_nested_in_for_body(tmp_path: Path) -> None:
    """Codex review finding on PR #169: a single-generator comprehension
    evaluated once per outer iteration is genuine O(n*m), even though no
    single comprehension node itself has two generators."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "report.py").write_text(
        "def f(xs, ys):\n"
        "    for x in xs:\n"
        "        result = [y for y in ys]\n"
        "    return result\n",
        encoding="utf-8",
    )

    report = run_capability_engine(tmp_path, changed_files=["src/report.py"])

    assert any(finding["capability"] == "performance" for finding in report["findings"])


def test_performance_finding_detects_comprehension_nested_in_comprehension(tmp_path: Path) -> None:
    """Codex review finding on PR #169: ``[[y for y in ys] for x in xs]``
    is genuine nested iteration even though each comprehension only has
    one generator of its own."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "report.py").write_text(
        "def f(xs, ys):\n    return [[y for y in ys] for x in xs]\n",
        encoding="utf-8",
    )

    report = run_capability_engine(tmp_path, changed_files=["src/report.py"])

    assert any(finding["capability"] == "performance" for finding in report["findings"])


def test_performance_finding_detects_allman_style_nested_loop(tmp_path: Path) -> None:
    """Codex review finding on PR #169: a brace on its own line (Allman
    style) must still bind to its controlling for/while header."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "Report.cs").write_text(
        "void Pairs(int[] rows)\n"
        "{\n"
        "    for (int i = 0; i < rows.Length; i++)\n"
        "    {\n"
        "        for (int j = 0; j < rows.Length; j++)\n"
        "        {\n"
        "            Console.WriteLine(rows[i] + rows[j]);\n"
        "        }\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )

    report = run_capability_engine(tmp_path, changed_files=["src/Report.cs"])

    assert any(finding["capability"] == "performance" for finding in report["findings"])


def test_performance_finding_detects_nested_loop_in_pyw_file(tmp_path: Path) -> None:
    """Codex review finding on PR #169: ``.pyw`` is a registered Python
    extension (see languages.py) and must route through the Python AST
    check, not the brace-language fallback."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "report.pyw").write_text(
        "def pairs(rows):\n"
        "    for left in rows:\n"
        "        for right in rows:\n"
        "            yield left, right\n",
        encoding="utf-8",
    )

    report = run_capability_engine(tmp_path, changed_files=["src/report.pyw"])

    assert any(finding["capability"] == "performance" for finding in report["findings"])


def test_performance_finding_excludes_loop_else_suite(tmp_path: Path) -> None:
    """Codex review finding on PR #169 (round 2): a for/while ``else``
    suite runs once after normal completion, not once per outer
    iteration -- a loop there is sequential, not nested."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "report.py").write_text(
        "def f(xs, ys):\n"
        "    while xs:\n"
        "        xs.pop()\n"
        "    else:\n"
        "        while ys:\n"
        "            ys.pop()\n",
        encoding="utf-8",
    )

    report = run_capability_engine(tmp_path, changed_files=["src/report.py"])

    assert not any(finding["capability"] == "performance" for finding in report["findings"])


def test_performance_finding_detects_nested_generator_in_comprehension_filter(tmp_path: Path) -> None:
    """Codex review finding on PR #169 (round 2): a comprehension filter
    (``if any(y for y in ys)``) iterates once per outer item just as much
    as the element expression does."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "report.py").write_text(
        "def f(xs, ys):\n    return [x for x in xs if any(y for y in ys)]\n",
        encoding="utf-8",
    )

    report = run_capability_engine(tmp_path, changed_files=["src/report.py"])

    assert any(finding["capability"] == "performance" for finding in report["findings"])


def test_performance_finding_detects_nested_loop_in_c_preprocessor_macro(tmp_path: Path) -> None:
    """Codex review finding on PR #169 (round 2): "#" introduces a
    preprocessor directive in C/C++, not a comment -- a macro body with
    real nested loops must not be blanked out before structural analysis."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "macro.c").write_text(
        "#define PAIRS(N) for(int i=0;i<N;i++){for(int j=0;j<N;j++){}}\n"
        "int main(void) { return 0; }\n",
        encoding="utf-8",
    )

    report = run_capability_engine(tmp_path, changed_files=["src/macro.c"])

    assert any(finding["capability"] == "performance" for finding in report["findings"])


def test_performance_finding_ignores_plain_c_macro_with_no_loops(tmp_path: Path) -> None:
    """Sanity check for the preprocessor-comment fix: an ordinary
    #include/#define with no loops must not falsely trigger."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "plain.c").write_text(
        "#include <stdio.h>\n#define MAX(a,b) ((a) > (b) ? (a) : (b))\n"
        "int main(void) { return 0; }\n",
        encoding="utf-8",
    )

    report = run_capability_engine(tmp_path, changed_files=["src/plain.c"])

    assert not any(finding["capability"] == "performance" for finding in report["findings"])


def test_performance_finding_ignores_non_loop_for_keyword_in_body(tmp_path: Path) -> None:
    """Codex review finding on PR #169 (round 2): a bare "for"/"while"
    token inside a loop body that is NOT itself a genuine loop header
    (e.g. a JS object key ``{for: value}``) must not count as nesting."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "queue.js").write_text(
        "function consume(queue) {\n"
        "    while (queue.length) {\n"
        "        consume2({for: queue.pop()});\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )

    report = run_capability_engine(tmp_path, changed_files=["src/queue.js"])

    assert not any(finding["capability"] == "performance" for finding in report["findings"])


def test_performance_finding_ignores_rust_impl_for_trait_syntax(tmp_path: Path) -> None:
    """Codex review finding on PR #169 (round 3): Rust's ``impl X for Y``
    contains the word "for" but is not a loop header -- a single genuine
    while-loop inside must not be reported as nested."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "worker.rs").write_text(
        "impl Worker for Thing {\n"
        "    fn run(&self) {\n"
        "        while ready() {\n"
        "        }\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )

    report = run_capability_engine(tmp_path, changed_files=["src/worker.rs"])

    assert not any(finding["capability"] == "performance" for finding in report["findings"])


def test_performance_finding_detects_nested_map_inside_template_interpolation(tmp_path: Path) -> None:
    """Codex review finding on PR #169 (round 3): a ``${...}`` template
    interpolation is executable code, not string content -- nested
    .map() calls inside one must still be detected."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "report.js").write_text(
        "const report = `${xs.map(x => ys.map(y => y))}`;\n",
        encoding="utf-8",
    )

    report = run_capability_engine(tmp_path, changed_files=["src/report.js"])

    assert any(finding["capability"] == "performance" for finding in report["findings"])


def test_performance_finding_detects_nested_loop_using_js_private_fields(tmp_path: Path) -> None:
    """Codex review finding on PR #169 (round 3): "#" is not a comment
    marker in JavaScript/TypeScript -- a private field access
    (``this.#items``) must not have the rest of its line erased."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "report.js").write_text(
        "class Report {\n"
        "  sum() {\n"
        "    for (const x of this.#items) {\n"
        "      for (const y of this.#items) {\n"
        "        console.log(x, y);\n"
        "      }\n"
        "    }\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    report = run_capability_engine(tmp_path, changed_files=["src/report.js"])

    assert any(finding["capability"] == "performance" for finding in report["findings"])


def test_performance_finding_detects_eager_default_value_comprehension(tmp_path: Path) -> None:
    """Codex review finding on PR #169 (round 3): a function's default
    value expression is evaluated once per enclosing loop iteration
    (at def-time), unlike its body, which is deferred until called."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "report.py").write_text(
        "def outer(xs, ys):\n"
        "    for x in xs:\n"
        "        def g(values=[y for y in ys]):\n"
        "            return values\n"
        "        g()\n",
        encoding="utf-8",
    )

    report = run_capability_engine(tmp_path, changed_files=["src/report.py"])

    assert any(finding["capability"] == "performance" for finding in report["findings"])


def test_performance_finding_still_ignores_loop_defining_but_not_calling_nested_function(tmp_path: Path) -> None:
    """Sanity check for the eager-default-value fix: a function merely
    DEFINED (not called) inside a loop, with a genuinely deferred body
    loop and no eager default, must still not be flagged -- matches the
    round-1 loop-boundary test, now that visit_FunctionDef visits
    decorators/defaults instead of returning unconditionally."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "report.py").write_text(
        "def outer(rows):\n"
        "    for row in rows:\n"
        "        def helper(items):\n"
        "            for item in items:\n"
        "                print(item)\n"
        "        helper(row)\n",
        encoding="utf-8",
    )

    report = run_capability_engine(tmp_path, changed_files=["src/report.py"])

    assert not any(finding["capability"] == "performance" for finding in report["findings"])


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
