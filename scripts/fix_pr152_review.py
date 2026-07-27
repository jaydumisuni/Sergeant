from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        if new in text:
            return
        raise RuntimeError(f"{path}: expected text was not found")
    if text.count(old) != 1:
        raise RuntimeError(f"{path}: expected exactly one occurrence")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "docs/22-semantic-open-model-review.md",
    "export SERGEANT_CPL_POLICY=preferred\nexport SERGEANT_CPL_PROVIDER=cpl\nexport SERGEANT_CPL_POLICY=preferred\n",
    "export SERGEANT_CPL_POLICY=preferred\nexport SERGEANT_CPL_PROVIDER=cpl\n",
)

replace_once(
    "main_review/llm_provider.py",
    "        enabled = policy != \"disabled\" and enabled_raw not in {\"0\", \"false\", \"no\", \"off\", \"disabled\"}\n\n        cloudflare_base, cloudflare_token = cloudflare_environment()\n",
    "        enabled = policy != \"disabled\" and enabled_raw not in {\"0\", \"false\", \"no\", \"off\", \"disabled\"}\n        if not enabled:\n            provider = \"disabled\"\n\n        cloudflare_base, cloudflare_token = cloudflare_environment()\n",
)

replace_once(
    "tests/test_llm_provider.py",
    '''        "SERGEANT_CPL_PROVIDER",\n        "SERGEANT_LLM_PROVIDER",\n    ]:\n        monkeypatch.delenv(name, raising=False)\n\n    settings = LLMSettings.from_environment()\n\n    assert settings.enabled is False\n    assert settings.policy == "disabled"\n''',
    '''        "SERGEANT_CPL_PROVIDER",\n        "SERGEANT_LLM_PROVIDER",\n        "SERGEANT_CPL_BASE_URL",\n        "SERGEANT_LLM_BASE_URL",\n    ]:\n        monkeypatch.delenv(name, raising=False)\n\n    settings = LLMSettings.from_environment()\n\n    assert settings.enabled is False\n    assert settings.policy == "disabled"\n    assert settings.provider == "disabled"\n''',
)

print("Applied verified PR #152 review repairs.")

# Final trigger; full repository CI will validate the committed head.
