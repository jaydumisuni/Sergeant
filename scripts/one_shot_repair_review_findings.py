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
        raise SystemExit(f"{path}: expected one match, found {count}: {old[:180]!r}")
    write(path, text.replace(old, new, 1))


replace_once(
    "main_review/llm_provider.py",
    '''def _request_headers(api_key: str) -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "sergeant-reviewer/cpl-router",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _load_json_response(request: urllib.request.Request, timeout: float) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
''',
    '''def _effective_origin(value: str) -> tuple[str, str, int] | None:
    try:
        parsed = urllib.parse.urlsplit(value)
        port = parsed.port
    except ValueError:
        return None
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()
    if scheme not in {"http", "https"} or not hostname or parsed.username or parsed.password:
        return None
    if port is None:
        port = 443 if scheme == "https" else 80
    return scheme, hostname, port


def _same_origin(request_url: str, trusted_url: str) -> bool:
    try:
        request_parsed = urllib.parse.urlsplit(request_url)
        trusted_parsed = urllib.parse.urlsplit(trusted_url)
    except ValueError:
        return False
    # Keep the direct scheme/netloc comparison visible for audit and static proof,
    # then normalize default ports so https://host and https://host:443 agree.
    if (request_parsed.scheme, request_parsed.netloc) == (
        trusted_parsed.scheme,
        trusted_parsed.netloc,
    ):
        return _effective_origin(request_url) is not None
    return _effective_origin(request_url) == _effective_origin(trusted_url) is not None


def _request_headers(api_key: str, *, endpoint: str, trusted_base_url: str) -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "sergeant-reviewer/cpl-router",
    }
    if api_key:
        if not _same_origin(endpoint, trusted_base_url):
            raise LLMProviderError(
                "Cpl refused to attach credentials because the request destination does not match the configured origin."
            )
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


class _CredentialSafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Allow credentialed redirects only when the exact origin is unchanged."""

    def redirect_request(self, request, fp, code, message, headers, new_url):  # type: ignore[override]
        if request.get_header("Authorization") and not _same_origin(request.full_url, new_url):
            raise LLMProviderError("Cpl refused a cross-origin redirect for a credentialed request.")
        return super().redirect_request(request, fp, code, message, headers, new_url)


def _load_json_response(request: urllib.request.Request, timeout: float) -> dict[str, Any]:
    opener = urllib.request.build_opener(_CredentialSafeRedirectHandler())
    try:
        with opener.open(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
''',
)

replace_once(
    "main_review/llm_provider.py",
    '''def list_models(base_url: str, *, api_key: str = "", timeout_seconds: float = 3.0) -> tuple[str, ...]:
    request = urllib.request.Request(
        f"{_normalize_base_url(base_url)}/models",
        headers=_request_headers(api_key),
        method="GET",
    )
''',
    '''def list_models(base_url: str, *, api_key: str = "", timeout_seconds: float = 3.0) -> tuple[str, ...]:
    trusted_base_url = _normalize_base_url(base_url)
    endpoint = f"{trusted_base_url}/models"
    request = urllib.request.Request(
        endpoint,
        headers=_request_headers(api_key, endpoint=endpoint, trusted_base_url=trusted_base_url),
        method="GET",
    )
''',
)

replace_once(
    "main_review/llm_provider.py",
    '''    request = urllib.request.Request(
        _cloudflare_native_endpoint(route),
        data=json.dumps(body).encode("utf-8"),
        headers=_request_headers(route.api_key),
        method="POST",
    )
''',
    '''    endpoint = _cloudflare_native_endpoint(route)
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers=_request_headers(
            route.api_key,
            endpoint=endpoint,
            trusted_base_url=route.base_url,
        ),
        method="POST",
    )
''',
)

replace_once(
    "main_review/llm_provider.py",
    '''def invoke_json(route: LLMRoute, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
    headers = _request_headers(route.api_key)
    if route.protocol == "responses":
''',
    '''def invoke_json(route: LLMRoute, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
    if route.protocol == "responses":
''',
)
replace_once(
    "main_review/llm_provider.py",
    '''        endpoint = f"{route.base_url}/chat/completions"

    request = urllib.request.Request(
''',
    '''        endpoint = f"{route.base_url}/chat/completions"

    headers = _request_headers(
        route.api_key,
        endpoint=endpoint,
        trusted_base_url=route.base_url,
    )
    request = urllib.request.Request(
''',
)

replace_once(
    "resources/sergeant-command-center-v2.js",
    '''  setInterval(() => { $('#clock').textContent = new Date().toLocaleTimeString(); }, 1000);

  renderOfficers();
''',
    '''  const clockTimer = setInterval(() => { $('#clock').textContent = new Date().toLocaleTimeString(); }, 1000);
  window.addEventListener('beforeunload', () => clearInterval(clockTimer), { once: true });

  renderOfficers();
''',
)

provider_tests = read("tests/test_llm_provider.py")
provider_tests = provider_tests.replace(
    '''from __future__ import annotations

from main_review.llm_provider import (
''',
    '''from __future__ import annotations

import urllib.request

import pytest

from main_review.llm_provider import (
''',
    1,
)
provider_tests = provider_tests.replace(
    '''    LLMSettings,
    discover_route,
    select_model,
''',
    '''    LLMSettings,
    LLMProviderError,
    _CredentialSafeRedirectHandler,
    _request_headers,
    discover_route,
    select_model,
''',
    1,
)
append = '''

def test_credentials_require_exact_configured_origin() -> None:
    headers = _request_headers(
        "token",
        endpoint="https://models.example/v1/chat/completions",
        trusted_base_url="https://models.example:443/v1",
    )
    assert headers["Authorization"] == "Bearer token"

    with pytest.raises(LLMProviderError, match="configured origin"):
        _request_headers(
            "token",
            endpoint="https://evil.example/v1/chat/completions",
            trusted_base_url="https://models.example/v1",
        )


def test_credentialed_cross_origin_redirect_is_rejected() -> None:
    request = urllib.request.Request(
        "https://models.example/v1/chat/completions",
        headers={"Authorization": "Bearer token"},
    )
    handler = _CredentialSafeRedirectHandler()

    with pytest.raises(LLMProviderError, match="cross-origin redirect"):
        handler.redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "https://evil.example/v1/chat/completions",
        )
'''
if "test_credentials_require_exact_configured_origin" not in provider_tests:
    provider_tests = provider_tests.rstrip() + append + "\n"
write("tests/test_llm_provider.py", provider_tests)

identity = read("tests/test_model_free_product_identity.py")
replace = '''    assert "Optional Model Assistance" in script
    assert "Cross-check Independence" in script
'''
with_lifecycle = '''    assert "Optional Model Assistance" in script
    assert "Cross-check Independence" in script
    assert "const clockTimer = setInterval" in script
    assert "clearInterval(clockTimer)" in script
'''
if identity.count(replace) != 1:
    raise SystemExit("identity lifecycle marker missing")
write("tests/test_model_free_product_identity.py", identity.replace(replace, with_lifecycle, 1))

(ROOT / ".github/workflows/one-shot-repair-review-findings.yml").unlink(missing_ok=True)
Path(__file__).unlink(missing_ok=True)
print("Repaired exact-origin credential binding, redirect safety, and timer lifecycle ownership.")
