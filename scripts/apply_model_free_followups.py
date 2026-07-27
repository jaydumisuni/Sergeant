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
    "  setInterval(() => { $('#clock').textContent = new Date().toLocaleTimeString(); }, 1000);",
    "  const clockInterval = setInterval(() => { $('#clock').textContent = new Date().toLocaleTimeString(); }, 1000);\n  const stopClock = () => clearInterval(clockInterval);\n  window.addEventListener('pagehide', stopClock, { once: true });\n  window.addEventListener('beforeunload', stopClock, { once: true });",
)

replace_once(
    "tests/test_vscode_extension_package.py",
    "    assert \"Math.random\" not in command_center_js\n    assert \"sgtTimer\" not in command_center_js",
    "    assert \"Math.random\" not in command_center_js\n    assert \"sgtTimer\" not in command_center_js\n    assert \"const clockInterval = setInterval\" in command_center_js\n    assert \"clearInterval(clockInterval)\" in command_center_js",
)
