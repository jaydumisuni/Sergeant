from pathlib import Path

path = Path("main_review/llm_provider.py")
text = path.read_text(encoding="utf-8")
text = text.replace(
    "import urllib.error\nimport urllib.request\n",
    "import urllib.error\nimport urllib.parse\nimport urllib.request\n",
)
text = text.replace(
    "    configured_model_roster,\n    public_base_url,\n",
    "    configured_model_roster,\n    is_cloudflare_provider,\n    public_base_url,\n",
)

start = text.index("def _extract_text(")
end = text.index("\ndef _parse_json_text", start)
replacement = '''def _response_shape(payload: dict[str, Any]) -> str:
    """Return a credential-safe summary of a provider response structure."""

    shape: dict[str, object] = {"top_level_keys": sorted(str(key) for key in payload)}
    choices = payload.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        first = choices[0]
        shape["choice_keys"] = sorted(str(key) for key in first)
        message = first.get("message")
        if isinstance(message, dict):
            shape["message_keys"] = sorted(str(key) for key in message)
        if first.get("finish_reason") is not None:
            shape["finish_reason"] = str(first.get("finish_reason"))
    result = payload.get("result")
    if isinstance(result, dict):
        shape["result_keys"] = sorted(str(key) for key in result)
    return json.dumps(shape, sort_keys=True)


def _text_value(value: object) -> str:
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, list):
        parts = [
            str(item.get("text", ""))
            for item in value
            if isinstance(item, dict) and isinstance(item.get("text"), str) and item.get("text")
        ]
        return "\\n".join(parts)
    return ""


def _extract_text(payload: dict[str, Any], protocol: LLMProtocol) -> str:
    if protocol == "chat_completions":
        choices = payload.get("choices", [])
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            first = choices[0]
            message = first.get("message", {})
            if isinstance(message, dict):
                content = _text_value(message.get("content"))
                if content:
                    return content
            choice_text = _text_value(first.get("text"))
            if choice_text:
                return choice_text

    for key in ("response", "output_text", "generated_text", "text"):
        value = _text_value(payload.get(key))
        if value:
            return value

    result = payload.get("result")
    if isinstance(result, dict):
        for key in ("response", "output_text", "generated_text", "text", "output"):
            value = _text_value(result.get(key))
            if value:
                return value

    output = payload.get("output", [])
    if isinstance(output, list):
        parts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content", [])
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and isinstance(part.get("text"), str):
                        parts.append(part["text"])
        if parts:
            return "\\n".join(parts)

    raise LLMProviderError(
        "Cpl model response did not contain text output. "
        f"Response shape: {_response_shape(payload)}"
    )
'''
text = text[:start] + replacement + text[end:]

start = text.index("def invoke_json(")
end = text.index("\n\n# Public Cpl aliases", start)
replacement = '''def _cloudflare_native_endpoint(route: LLMRoute) -> str:
    base = route.base_url.rstrip("/")
    if base.endswith("/ai/v1"):
        base = base[:-3]
    elif base.endswith("/v1"):
        base = base[:-3]
    model = urllib.parse.quote(route.model, safe="@/")
    return f"{base}/run/{model}"


def _invoke_cloudflare_native_text(
    route: LLMRoute,
    *,
    system_prompt: str,
    user_prompt: str,
) -> str:
    body = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0,
        "max_tokens": route.max_output_tokens,
    }
    request = urllib.request.Request(
        _cloudflare_native_endpoint(route),
        data=json.dumps(body).encode("utf-8"),
        headers=_request_headers(route.api_key),
        method="POST",
    )
    response = _load_json_response(request, route.timeout_seconds)
    return _extract_text(response, "chat_completions")


def invoke_json(route: LLMRoute, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
    headers = _request_headers(route.api_key)
    if route.protocol == "responses":
        body: dict[str, Any] = {
            "model": route.model,
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
            ],
            "temperature": 0,
            "max_output_tokens": route.max_output_tokens,
        }
        endpoint = f"{route.base_url}/responses"
    else:
        body = {
            "model": route.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "max_tokens": route.max_output_tokens,
            "response_format": {"type": "json_object"},
        }
        endpoint = f"{route.base_url}/chat/completions"

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        response = _load_json_response(request, route.timeout_seconds)
    except LLMProviderError as first_error:
        if route.protocol != "chat_completions" or "response_format" not in body:
            raise
        body.pop("response_format", None)
        retry = urllib.request.Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            response = _load_json_response(retry, route.timeout_seconds)
        except LLMProviderError:
            raise first_error

    try:
        return _parse_json_text(_extract_text(response, route.protocol))
    except LLMProviderError as compatible_error:
        if not is_cloudflare_provider(route.provider):
            raise
        try:
            native_text = _invoke_cloudflare_native_text(
                route,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            return _parse_json_text(native_text)
        except LLMProviderError as native_error:
            raise LLMProviderError(
                "Cloudflare OpenAI-compatible and native model routes both failed. "
                f"Compatible route: {compatible_error} Native route: {native_error}"
            ) from native_error
'''
text = text[:start] + replacement + text[end:]
path.write_text(text, encoding="utf-8")
