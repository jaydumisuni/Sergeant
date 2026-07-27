from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    content = target.read_text(encoding="utf-8")
    if content.count(old) != 1:
        raise RuntimeError(f"{path}: expected one exact match for {old!r}")
    target.write_text(content.replace(old, new, 1), encoding="utf-8")


replace_once(
    "resources/sergeant-command-center-v2.js",
    "if (settings.policy === 'disabled' || provider === 'disabled') return 'Model-free · Cpl + officers + privates';",
    "if (settings.policy === 'disabled' || provider === 'disabled') return 'Model-free';",
)

replace_once(
    "tests/command-center-visual.spec.js",
    "  await expect(page.locator('#semanticRoute')).toContainText('Model-free · Cpl + officers + privates');",
    "  await expect(page.locator('#semanticRoute')).toHaveText('Model-free');",
)
