from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    content = target.read_text(encoding="utf-8")
    if content.count(old) != 1:
        raise RuntimeError(f"{path}: expected one exact match for {old!r}")
    target.write_text(content.replace(old, new, 1), encoding="utf-8")


replace_once(
    "resources/sergeant-command-center-v2.css",
    ".quick-grid{display:grid;grid-template-columns:1.2fr 1fr 1fr;gap:14px;margin:14px 0}.row{",
    ".quick-grid{display:grid;grid-template-columns:1.2fr 1fr 1fr;gap:14px;margin:14px 0}.quick-grid>article:last-child{padding-right:175px}.row{",
)

replace_once(
    "resources/sergeant-command-center-v2.css",
    "@media(max-width:1100px){.app{",
    "@media(max-width:1100px){.quick-grid>article:last-child{padding-right:20px}.app{",
)

replace_once(
    "tests/command-center-visual.spec.js",
    "  await expect(page.locator('#semanticRoute')).toHaveText('Model-free');\n  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);",
    "  await expect(page.locator('#semanticRoute')).toHaveText('Model-free');\n  const quickActions = page.locator('.quick-actions');\n  if (await quickActions.isVisible()) {\n    const routeBox = await page.locator('#semanticRoute').boundingBox();\n    const actionsBox = await quickActions.boundingBox();\n    expect(routeBox).not.toBeNull();\n    expect(actionsBox).not.toBeNull();\n    expect(routeBox.x + routeBox.width).toBeLessThanOrEqual(actionsBox.x - 4);\n  }\n  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);",
)
