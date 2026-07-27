from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text.rstrip() + "\n", encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match, found {count}: {old[:140]!r}")
    write(path, text.replace(old, new, 1))


replace_once(
    "resources/sergeant-command-center-v2.html",
    '<label>Policy<select id="llmPolicySelect">',
    '<label>Model Support<select id="llmPolicySelect">',
)
replace_once(
    "resources/sergeant-command-center-v2.html",
    '<label>Engine Route<select id="providerSelect">',
    '<label>Optional Model Route<select id="providerSelect">',
)
replace_once(
    "resources/sergeant-command-center-v2.html",
    '<label>Model<input id="llmModelInput"',
    '<label>Optional Model<input id="llmModelInput"',
)
replace_once(
    "resources/sergeant-command-center-v2.html",
    '<label>Base URL<input id="llmBaseUrlInput"',
    '<label>Optional Base URL<input id="llmBaseUrlInput"',
)
replace_once(
    "resources/sergeant-command-center-v2.html",
    '<label>Reasoning Depth<select id="llmCouncilSelect">',
    '<label>Optional Reasoning Depth<select id="llmCouncilSelect">',
)
replace_once(
    "resources/sergeant-command-center-v2.html",
    '<label><input type="checkbox" checked>Cpl Specialist Reasoning</label>',
    '<label><input type="checkbox" checked>Cpl / Officer Reasoning</label>',
)

replace_once(
    "resources/sergeant-command-center-v2.js",
    "row.innerHTML = '<label>Maximum Council Rounds<input id=\"cplMaxRoundsInput\" type=\"number\" min=\"1\" max=\"6\" value=\"2\"></label><label>Maximum Council Members<input id=\"cplMaxMembersInput\" type=\"number\" min=\"1\" max=\"12\" value=\"5\"></label>';",
    "row.innerHTML = '<label>Optional Model Rounds<input id=\"cplMaxRoundsInput\" type=\"number\" min=\"1\" max=\"6\" value=\"2\"></label><label>Optional Model Members<input id=\"cplMaxMembersInput\" type=\"number\" min=\"1\" max=\"12\" value=\"5\"></label>';",
)
replace_once(
    "resources/sergeant-command-center-v2.js",
    "function page(id) {\n    $$('.page').forEach((element) => element.classList.toggle('active', element.id === id));\n    $$('[data-page]').forEach((button) => button.classList.toggle('active', button.dataset.page === id));\n  }",
    "function page(id) {\n    $$('.page').forEach((element) => element.classList.toggle('active', element.id === id));\n    $$('[data-page]').forEach((button) => button.classList.toggle('active', button.dataset.page === id));\n    const quickActions = $('.quick-actions');\n    if (quickActions) quickActions.hidden = ['orders', 'settings'].includes(id);\n  }",
)

css = read("resources/sergeant-command-center-v2.css")
layout_fix = """
/* Model-support controls must remain readable in the narrow mission side panel. */
.two-col>article.panel>label{display:grid;gap:6px;margin:0 0 10px;min-width:0}
.two-col>article.panel>label input,.two-col>article.panel>label select,.two-col>article.panel .form-grid input,.two-col>article.panel .form-grid select{width:100%;min-width:0;max-width:100%}
.two-col>article.panel .form-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
.quick-actions[hidden]{display:none!important}
@media(max-width:600px){.two-col>article.panel .form-grid{grid-template-columns:1fr}}
""".strip()
if layout_fix not in css:
    css = css.rstrip() + "\n" + layout_fix + "\n"
write("resources/sergeant-command-center-v2.css", css)

spec = read("tests/model-free-product-visual.spec.js")
old = """    await expect(page.locator('body')).toContainText('optional extra-reasoning support only');
    await expectNoDocumentOverflow(page);
    await page.screenshot({"""
new = """    await expect(page.locator('body')).toContainText('optional extra-reasoning support only');
    await expect(page.locator('.quick-actions')).toBeHidden();
    const controls = await page.locator('#orders article.panel').nth(1).locator('input, select').evaluateAll((elements) =>
      elements.map((element) => {
        const box = element.getBoundingClientRect();
        return { id: element.id, left: box.left, right: box.right, top: box.top, bottom: box.bottom };
      }),
    );
    for (let index = 0; index < controls.length; index += 1) {
      for (let other = index + 1; other < controls.length; other += 1) {
        const first = controls[index];
        const second = controls[other];
        const overlaps = first.left < second.right && first.right > second.left && first.top < second.bottom && first.bottom > second.top;
        expect(overlaps, `${first.id} overlaps ${second.id}`).toBeFalsy();
      }
    }
    await expectNoDocumentOverflow(page);
    await page.screenshot({"""
if spec.count(old) != 1:
    raise SystemExit("visual spec insertion marker not found")
write("tests/model-free-product-visual.spec.js", spec.replace(old, new, 1))

identity = read("tests/test_model_free_product_identity.py")
old = """    assert \"Model-free only — no model calls\" in html
    assert \"Model-free Sergeant core\" in script"""
new = """    assert \"Model-free only — no model calls\" in html
    assert \"Cpl / Officer Reasoning\" in html
    assert \"Optional Model Route\" in html
    assert \"Model-free Sergeant core\" in script
    assert \"Optional Model Rounds\" in script"""
if identity.count(old) != 1:
    raise SystemExit("identity UI marker not found")
write("tests/test_model_free_product_identity.py", identity.replace(old, new, 1))

(ROOT / ".github/workflows/one-shot-fix-model-ui-layout.yml").unlink(missing_ok=True)
Path(__file__).unlink(missing_ok=True)
print("Corrected model-support form layout and responsive visual overlap.")
