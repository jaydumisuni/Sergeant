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
    "resources/sergeant-command-center-v2.css",
    ".two-col>article.panel .form-grid{grid-template-columns:repeat(2,minmax(0,1fr))}",
    ".two-col>article.panel .form-grid{grid-template-columns:1fr}",
)
replace_once(
    "resources/sergeant-command-center-v2.js",
    "['Council Limits', `${settings.maxRounds || 2} rounds · ${settings.maxMembers || 5} members`],",
    "['Optional Model Limits', `${settings.maxRounds || 2} rounds · ${settings.maxMembers || 5} members`],",
)

spec = read("tests/model-free-product-visual.spec.js")
old = """    for (let index = 0; index < controls.length; index += 1) {
      for (let other = index + 1; other < controls.length; other += 1) {
        const first = controls[index];
        const second = controls[other];
        const overlaps = first.left < second.right && first.right > second.left && first.top < second.bottom && first.bottom > second.top;
        expect(overlaps, `${first.id} overlaps ${second.id}`).toBeFalsy();
      }
    }
    await expectNoDocumentOverflow(page);"""
new = """    for (let index = 0; index < controls.length; index += 1) {
      for (let other = index + 1; other < controls.length; other += 1) {
        const first = controls[index];
        const second = controls[other];
        const overlaps = first.left < second.right && first.right > second.left && first.top < second.bottom && first.bottom > second.top;
        expect(overlaps, `${first.id} overlaps ${second.id}`).toBeFalsy();
      }
    }
    if (view.name === 'desktop') {
      const reasoningWidth = await page.locator('#llmCouncilSelect').evaluate((element) => element.getBoundingClientRect().width);
      expect(reasoningWidth).toBeGreaterThan(230);
    }
    await expect(page.locator('body')).toContainText('Optional Model Limits');
    await expectNoDocumentOverflow(page);"""
if spec.count(old) != 1:
    raise SystemExit("visual readability assertion marker not found")
write("tests/model-free-product-visual.spec.js", spec.replace(old, new, 1))

identity = read("tests/test_model_free_product_identity.py")
old = '    assert "Optional Model Rounds" in script\n'
new = '    assert "Optional Model Rounds" in script\n    assert "Optional Model Limits" in script\n'
if identity.count(old) != 1:
    raise SystemExit("identity optional limits marker not found")
write("tests/test_model_free_product_identity.py", identity.replace(old, new, 1))

(ROOT / ".github/workflows/one-shot-finish-visual-readability.yml").unlink(missing_ok=True)
Path(__file__).unlink(missing_ok=True)
print("Finished model-support visual readability correction.")
