from pathlib import Path


def collapse_first_duplicate(text: str, marker: str, *, label: str) -> str:
    count = text.count(marker)
    if count == 1:
        return text
    if count != 2:
        raise SystemExit(f"Expected one or two {label} blocks, found {count}.")
    first = text.index(marker)
    second = text.index(marker, first + len(marker))
    return text[:first] + text[second:]


provider = Path("main_review/llm_provider.py")
text = provider.read_text(encoding="utf-8")
text = collapse_first_duplicate(text, "def _response_shape(", label="response-shape helper")
text = collapse_first_duplicate(text, "def _cloudflare_native_endpoint(", label="native-route helper")
unsafe = '''        except LLMProviderError as native_error:\n            raise LLMProviderError(\n                "Cloudflare OpenAI-compatible and native model routes both failed. "\n                f"Compatible route: {compatible_error} Native route: {native_error}"\n            ) from native_error\n'''
safe = '''        except LLMProviderError as native_error:\n            raise LLMProviderError(\n                "Cloudflare OpenAI-compatible and native model routes both failed without a parseable JSON response."\n            ) from native_error\n'''
if unsafe in text:
    text = text.replace(unsafe, safe)
if "Compatible route:" in text or "Native route:" in text:
    raise SystemExit("Unsafe nested provider error text remains in llm_provider.py.")
if text.count("def _response_shape(") != 1:
    raise SystemExit("Response-shape helper was not normalized to one definition.")
if text.count("def _cloudflare_native_endpoint(") != 1:
    raise SystemExit("Native endpoint helper was not normalized to one definition.")
provider.write_text(text, encoding="utf-8")

models = Path("main_review/cloudflare_models.py")
text = models.read_text(encoding="utf-8")
text = collapse_first_duplicate(text, "CLOUDFLARE_REASONING_MODELS = {", label="reasoning-model constants")
text = collapse_first_duplicate(text, "def model_proof_output_tokens(", label="model proof budget helper")
if text.count("CLOUDFLARE_REASONING_MODELS = {") != 1:
    raise SystemExit("Reasoning model constants were not normalized.")
if text.count("def model_proof_output_tokens(") != 1:
    raise SystemExit("Model proof helper was not normalized.")
models.write_text(text, encoding="utf-8")

cli = Path("main_review/cloudflare_cli.py")
text = cli.read_text(encoding="utf-8")
text = collapse_first_duplicate(text, "from .cloudflare_models import (", label="Cloudflare model import")
if text.count("from .cloudflare_models import (") != 1:
    raise SystemExit("Cloudflare model import was not normalized.")
if "MODEL_PROOF_MAX_OUTPUT_TOKENS = DEFAULT_MODEL_PROOF_OUTPUT_TOKENS" not in text:
    raise SystemExit("Public default model-proof constant is missing.")
cli.write_text(text, encoding="utf-8")

tests = Path("tests/test_cloudflare_native_fallback.py")
text = tests.read_text(encoding="utf-8")
if "from pathlib import Path\n" not in text:
    text = text.replace("from __future__ import annotations\n\n", "from __future__ import annotations\n\nfrom pathlib import Path\n\n")
if "def test_dual_route_error_does_not_echo_upstream_body" not in text:
    text += '''\n\ndef test_dual_route_error_does_not_echo_upstream_body(monkeypatch) -> None:\n    responses = iter(\n        [\n            {"choices": [{"message": {"content": ""}}]},\n            llm_provider.LLMProviderError("upstream body: private provider detail"),\n        ]\n    )\n\n    def fake_load(request, timeout):\n        result = next(responses)\n        if isinstance(result, Exception):\n            raise result\n        return result\n\n    monkeypatch.setattr(llm_provider, "_load_json_response", fake_load)\n    with pytest.raises(llm_provider.LLMProviderError) as captured:\n        llm_provider.invoke_json(_route(), system_prompt="system", user_prompt="user")\n\n    message = str(captured.value)\n    assert "private provider detail" not in message\n    assert message == (\n        "Cloudflare OpenAI-compatible and native model routes both failed without a parseable JSON response."\n    )\n\n\ndef test_fallback_helpers_are_defined_once() -> None:\n    provider_source = Path(llm_provider.__file__).read_text(encoding="utf-8")\n    from main_review import cloudflare_cli, cloudflare_models\n\n    model_source = Path(cloudflare_models.__file__).read_text(encoding="utf-8")\n    cli_source = Path(cloudflare_cli.__file__).read_text(encoding="utf-8")\n\n    assert provider_source.count("def _response_shape(") == 1\n    assert provider_source.count("def _cloudflare_native_endpoint(") == 1\n    assert model_source.count("def model_proof_output_tokens(") == 1\n    assert model_source.count("CLOUDFLARE_REASONING_MODELS = {") == 1\n    assert cli_source.count("from .cloudflare_models import (") == 1\n'''
tests.write_text(text, encoding="utf-8")
