from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "main_review" / "llm_provider.py"
text = TARGET.read_text(encoding="utf-8")
old = '''        if not enabled:\n            provider = "disabled"\n'''
new = '''        if not enabled and not explicit_route:\n            provider = "disabled"\n'''
if old not in text:
    if new in text:
        raise SystemExit(0)
    raise RuntimeError("Expected provider boundary was not found")
if text.count(old) != 1:
    raise RuntimeError("Provider boundary is ambiguous")
TARGET.write_text(text.replace(old, new, 1), encoding="utf-8")
print("Preserved explicit providers while keeping a clean environment model-free.")

# Trigger after the safe one-use workflow is installed.
