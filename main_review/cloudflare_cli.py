"""CLI for connecting Sergeant Cpl to Cloudflare Workers AI."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .cloudflare_gateway import (
    CloudflareGatewayError,
    CloudflareGatewaySettings,
    build_server,
)
from .cpl_runtime import run_cpl_review
from .diff_review import parse_changed_files_text
from .llm_provider import LLMProviderError, LLMRoute, LLMSettings, invoke_json


def cloudflare_route(settings: CloudflareGatewaySettings, *, model: str | None = None) -> LLMRoute:
    settings.validate()
    selected = model or settings.models[0]
    if selected not in settings.models:
        raise CloudflareGatewayError(f"Model is not in the configured Cloudflare roster: {selected!r}")
    return LLMRoute(
        provider="cloudflare-workers-ai",
        base_url=f"https://api.cloudflare.com/client/v4/accounts/{settings.account_id}/ai/v1",
        model=selected,
        protocol="chat_completions",
        api_key=settings.api_token,
        timeout_seconds=settings.timeout_seconds,
        max_output_tokens=5000,
        discovered_models=settings.models,
    )


def _print(payload: object, *, pretty: bool) -> None:
    print(json.dumps(payload, indent=2 if pretty else None, sort_keys=True))


def _proof_prompt(model: str) -> tuple[str, str]:
    return (
        "Return JSON only. You are proving that a model route can follow a structured Sergeant contract.",
        json.dumps(
            {
                "instruction": "Return the exact requested JSON fields without Markdown.",
                "model": model,
                "required": {
                    "status": "ready",
                    "model": model,
                    "capabilities": ["structured_json", "reasoning"],
                },
            }
        ),
    )


def test_models(settings: CloudflareGatewaySettings) -> dict[str, Any]:
    settings.validate()
    results: list[dict[str, Any]] = []
    for model in settings.models:
        route = cloudflare_route(settings, model=model)
        system_prompt, user_prompt = _proof_prompt(model)
        try:
            payload = invoke_json(route, system_prompt=system_prompt, user_prompt=user_prompt)
            passed = payload.get("status") == "ready" and payload.get("model") == model
            results.append({"model": model, "passed": passed, "response": payload})
        except LLMProviderError as error:
            results.append({"model": model, "passed": False, "error": str(error)})
    return {
        "provider": "cloudflare-workers-ai",
        "model_count": len(settings.models),
        "passed_count": sum(bool(item.get("passed")) for item in results),
        "all_passed": bool(results) and all(bool(item.get("passed")) for item in results),
        "models": results,
    }


def _changed_files(value: str, file_list: str | None) -> list[str]:
    if file_list:
        return parse_changed_files_text(Path(file_list).read_text(encoding="utf-8"))
    return parse_changed_files_text(value)


def run_council_proof(
    settings: CloudflareGatewaySettings,
    *,
    root: str | Path,
    changed_files: list[str],
) -> dict[str, Any]:
    settings.validate()
    if len(settings.models) < 2:
        raise CloudflareGatewayError("Council proof requires at least two configured Cloudflare models.")
    context = {
        "proof_type": "cloudflare-live-council",
        "repository_root": str(Path(root).resolve()),
        "changed_files": changed_files,
        "rule": "This proof must report actual model members and must not infer independence from repeated calls to one model.",
    }
    llm_settings = LLMSettings(
        enabled=True,
        policy="required",
        provider="cloudflare-workers-ai",
        base_url=f"https://api.cloudflare.com/client/v4/accounts/{settings.account_id}/ai/v1",
        model=settings.models[0],
        protocol="chat_completions",
        api_key=settings.api_token,
        timeout_seconds=settings.timeout_seconds,
        max_output_tokens=5000,
    )
    result = run_cpl_review(
        root,
        changed_files,
        context,
        settings=llm_settings,
        route=cloudflare_route(settings),
    )
    council = result.get("council", {}) if isinstance(result.get("council"), dict) else {}
    passes = [item for item in result.get("passes", []) if isinstance(item, dict)]
    distinct_models = sorted({str(item.get("model")) for item in passes if item.get("model")})
    passed = (
        result.get("status") in {"completed", "completed_with_warnings"}
        and len(distinct_models) > 1
        and council.get("true_model_independence") is True
    )
    return {
        "schema_version": "sergeant.cloudflare-council-proof.v1",
        "passed": passed,
        "provider": "cloudflare-workers-ai",
        "configured_models": list(settings.models),
        "distinct_models": distinct_models,
        "model_call_count": len(passes),
        "true_model_independence": council.get("true_model_independence", False),
        "council_complete": council.get("complete", False),
        "final_gaps": council.get("final_gaps", []),
        "status": result.get("status"),
        "verdict": result.get("verdict"),
        "errors": result.get("errors", []),
        "council": council,
    }


def _gateway_environment(settings: CloudflareGatewaySettings) -> dict[str, str]:
    return {
        "SERGEANT_CPL_ENABLED": "true",
        "SERGEANT_CPL_POLICY": "required",
        "SERGEANT_CPL_PROVIDER": "configured",
        "SERGEANT_CPL_BASE_URL": f"http://{settings.host}:{settings.port}/v1",
        "SERGEANT_CPL_MODEL": settings.models[0],
        "SERGEANT_CPL_PROTOCOL": "chat_completions",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sergeant-cloudflare")
    parser.add_argument("--pretty", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status", help="Show Cloudflare configuration without revealing credentials.")
    status.add_argument("--require", action="store_true")

    env = sub.add_parser("env", help="Print the Sergeant environment required to use the local gateway.")
    env.add_argument("--shell", choices=["powershell", "bash", "json"], default="json")

    test = sub.add_parser("test-models", help="Call every configured Cloudflare model with a structured-output proof.")
    test.add_argument("--require", action="store_true")

    gateway = sub.add_parser("gateway", help="Run the local OpenAI-compatible Cloudflare gateway.")
    gateway.add_argument("--host")
    gateway.add_argument("--port", type=int)
    gateway.add_argument("--allow-network", action="store_true")

    council = sub.add_parser("council-proof", help="Run a live multi-model Cpl proof through Cloudflare.")
    council.add_argument("path", nargs="?", default=".")
    source = council.add_mutually_exclusive_group(required=True)
    source.add_argument("--files", help="Comma/newline-separated changed files.")
    source.add_argument("--file-list", help="File containing changed paths.")
    council.add_argument("--output")
    council.add_argument("--no-fail", action="store_true")
    return parser


def _render_shell(values: dict[str, str], shell: str) -> str:
    if shell == "json":
        return json.dumps(values, indent=2, sort_keys=True)
    if shell == "powershell":
        return "\n".join(f'$env:{key}="{value}"' for key, value in values.items())
    return "\n".join(f"export {key}={json.dumps(value)}" for key, value in values.items())


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = CloudflareGatewaySettings.from_environment(
        host=getattr(args, "host", None),
        port=getattr(args, "port", None),
        allow_network=bool(getattr(args, "allow_network", False)),
    )

    if args.command == "status":
        payload = settings.public_dict()
        payload["valid"] = True
        try:
            settings.validate()
        except CloudflareGatewayError as error:
            payload["valid"] = False
            payload["error"] = str(error)
        _print(payload, pretty=args.pretty)
        return 0 if payload["valid"] or not args.require else 2

    if args.command == "env":
        settings.validate(require_credentials=False)
        print(_render_shell(_gateway_environment(settings), args.shell))
        return 0

    if args.command == "test-models":
        try:
            payload = test_models(settings)
        except CloudflareGatewayError as error:
            payload = {"provider": "cloudflare-workers-ai", "all_passed": False, "error": str(error)}
        _print(payload, pretty=args.pretty)
        return 0 if payload.get("all_passed") or not args.require else 2

    if args.command == "gateway":
        try:
            server = build_server(settings)
        except CloudflareGatewayError as error:
            parser.error(str(error))
        print(json.dumps({"status": "ready", **settings.public_dict()}, indent=2 if args.pretty else None))
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return 0

    if args.command == "council-proof":
        changed = _changed_files(args.files or "", args.file_list)
        if not changed:
            parser.error("At least one changed file is required.")
        try:
            payload = run_council_proof(settings, root=args.path, changed_files=changed)
        except CloudflareGatewayError as error:
            payload = {"schema_version": "sergeant.cloudflare-council-proof.v1", "passed": False, "error": str(error)}
        text = json.dumps(payload, indent=2 if args.pretty else None, sort_keys=True) + "\n"
        if args.output:
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(text, encoding="utf-8")
        print(text, end="")
        return 0 if payload.get("passed") or args.no_fail else 2

    parser.error("Unsupported command.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
