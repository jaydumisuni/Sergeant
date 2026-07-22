"""Static auth-transition state propagation checks for browser applications."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

_SOURCE_SUFFIXES = {".js", ".jsx", ".ts", ".tsx"}
_CHROME_COMPONENT_RE = re.compile(
    r"(?:export\s+default\s+)?function\s+(?P<decl>(?:Navbar|Topbar|Header|Sidebar|Chrome)[A-Za-z0-9_$]*)\s*\([^)]*\)\s*\{|"
    r"(?:const|let|var)\s+(?P<arrow>(?:Navbar|Topbar|Header|Sidebar|Chrome)[A-Za-z0-9_$]*)\s*=\s*"
    r"(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>\s*\{",
    re.I | re.M,
)
_CACHE_HELPER_RE = re.compile(
    r"function\s+(?P<name>get(?:Cached|Stored|Saved)[A-Za-z0-9_$]*(?:Config|Auth|Account|Session|User)[A-Za-z0-9_$]*)"
    r"\s*\([^)]*\)\s*\{",
    re.I | re.M,
)
_LOCAL_STORAGE_RE = re.compile(
    r"localStorage\.getItem\s*\(\s*[\"'](?P<key>[^\"']*(?:config|auth|account|session|user)[^\"']*)[\"']",
    re.I,
)
_AUTH_UI_RE = re.compile(
    r"(?:auth(?:Mode|Label)?|account(?:Name|Role)?|jellyfinUser|currentUser|profile|avatar|login|logout|sign[- ]?in)",
    re.I,
)
_AUTH_CALL_RE = re.compile(
    r"(?:loginAction|loginUser|signIn|signInWithPassword|authenticate|mutateAsync)\s*\(",
    re.I,
)
_EXPLICIT_AUTH_CONTEXT_RE = re.compile(
    r"(?:loginAction|loginUser|signInWithPassword|authenticate|LoginForm|AuthForm|"
    r"mutationFn\s*:\s*[^\n]{0,240}(?:login|signIn|authenticate))",
    re.I,
)
_CACHE_SYNC_RE = re.compile(
    r"(?:queryClient\.(?:invalidateQueries|refetchQueries|resetQueries|clear)\s*\(|"
    r"authClient[^;\n]*(?:notify|refetch|setSession|update)|"
    r"setSession\s*\(|refreshSession\s*\()",
    re.I,
)


def _safe_text(root: Path, relative: str) -> str:
    try:
        resolved_root = root.resolve()
        path = (resolved_root / relative).resolve()
        if not path.is_relative_to(resolved_root) or not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _line(text: str, offset: int) -> int:
    return text[: max(0, offset)].count("\n") + 1


def _matching_brace(text: str, opening: int) -> int | None:
    depth = 0
    quote: str | None = None
    escaped = False
    line_comment = False
    block_comment = False
    index = opening
    while index < len(text):
        char = text[index]
        nxt = text[index + 1] if index + 1 < len(text) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
            index += 1
            continue
        if block_comment:
            if char == "*" and nxt == "/":
                block_comment = False
                index += 2
            else:
                index += 1
            continue
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue
        if char == "/" and nxt == "/":
            line_comment = True
            index += 2
            continue
        if char == "/" and nxt == "*":
            block_comment = True
            index += 2
            continue
        if char in {"'", '"', "`"}:
            quote = char
            index += 1
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def _block(text: str, match: re.Match[str]) -> tuple[str, int] | None:
    opening = match.end() - 1
    closing = _matching_brace(text, opening)
    if closing is None:
        return None
    return text[opening + 1 : closing], opening + 1


def _finding(
    *,
    root_cause: str,
    path: str,
    line_start: int,
    message: str,
    evidence: str,
    supporting: Iterable[str],
    falsifiers: Iterable[str],
    verification: str,
    confidence: float,
) -> dict[str, Any]:
    return {
        "source": "static-js-auth-transition-officer",
        "officer": "Mechanic",
        "capability": "state_lifecycle",
        "category": "state_lifecycle",
        "severity": "major",
        "root_cause": root_cause,
        "path": path,
        "line_start": line_start,
        "line_end": line_start,
        "evidence_ref": f"{path}:{line_start}",
        "supporting_evidence_refs": list(supporting),
        "message": message,
        "evidence": evidence,
        "falsifiers_checked": list(falsifiers),
        "verification_test": verification,
        "confidence": confidence,
        "direct_evidence": True,
        "admission_hint": "actionable",
    }


def _cache_helpers(text: str) -> dict[str, tuple[str, int, str]]:
    helpers: dict[str, tuple[str, int, str]] = {}
    for match in _CACHE_HELPER_RE.finditer(text):
        block = _block(text, match)
        if block is None:
            continue
        body, offset = block
        storage = _LOCAL_STORAGE_RE.search(body)
        if storage is None:
            continue
        helpers[match.group("name")] = (body, offset, storage.group("key"))
    return helpers


def _external_listener(body: str) -> bool:
    return bool(
        re.search(
            r"addEventListener\s*\(\s*[\"'](?:storage|[^\"']*(?:config|auth|account|session|user)[^\"']*)[\"']",
            body,
            re.I,
        )
    )


def _browser_cache_findings(path: str, text: str) -> list[dict[str, Any]]:
    helpers = _cache_helpers(text)
    if not helpers:
        return []
    findings: list[dict[str, Any]] = []
    for component in _CHROME_COMPONENT_RE.finditer(text):
        block = _block(text, component)
        if block is None:
            continue
        body, body_offset = block
        component_name = component.group("decl") or component.group("arrow") or "chrome component"
        if _AUTH_UI_RE.search(body) is None:
            continue
        for helper_name, (_, _, storage_key) in helpers.items():
            if re.search(r"useSyncExternalStore\s*\(", body):
                continue
            plain = re.search(
                rf"(?:const|let|var)\s+(?P<variable>[A-Za-z_$][\w$]*)\s*=\s*{re.escape(helper_name)}\s*\(\s*\)",
                body,
            )
            state = re.search(
                rf"\[(?P<variable>[A-Za-z_$][\w$]*),\s*(?P<setter>set[A-Za-z_$][\w$]*)\]\s*=\s*"
                rf"useState\s*\(\s*(?:\(\s*\)\s*=>\s*)?{re.escape(helper_name)}\s*\(",
                body,
                re.I,
            )
            if plain is None and state is None:
                continue
            selected = state or plain
            assert selected is not None
            variable = selected.group("variable")
            if state is not None:
                setter = state.group("setter")
                if _external_listener(body) and re.search(rf"\b{re.escape(setter)}\s*\(", body):
                    continue
            assignment_line = _line(text, body_offset + selected.start())
            ownership = "plain render-time value" if plain is not None else "mount-initialized React state without external invalidation"
            findings.append(
                _finding(
                    root_cause="browser-auth-cache-read-without-reactive-owner",
                    path=path,
                    line_start=assignment_line,
                    message="A long-lived React chrome component derives authentication UI from browser storage without reactive invalidation.",
                    evidence=(
                        f"{component_name} reads localStorage key {storage_key!r} through {helper_name} into {variable} at line "
                        f"{assignment_line} as a {ownership}. The value drives auth/account UI, but browser-storage changes do not "
                        "schedule an authoritative refresh of that state."
                    ),
                    supporting=(f"{path}:{assignment_line}",),
                    falsifiers=(
                        "Checked that the component is long-lived application chrome rather than a short-lived leaf.",
                        "Checked that the helper reads an auth/account/session/config browser-storage key.",
                        "Checked that the returned object drives authentication or account presentation.",
                        "Checked for React state ownership plus storage/config/auth event invalidation and setter refresh.",
                        "Checked for useSyncExternalStore ownership.",
                    ),
                    verification=(
                        "Own the cached auth/config object in React state, refresh it from the authoritative source after setup/session "
                        "changes, subscribe to a matching custom or storage event, and prove the navbar updates without reload."
                    ),
                    confidence=0.97,
                )
            )
            break
    return findings


def _next_post_auth_findings(path: str, text: str) -> list[dict[str, Any]]:
    if "next/navigation" not in text or "useRouter" not in text:
        return []
    if _AUTH_CALL_RE.search(text) is None or _EXPLICIT_AUTH_CONTEXT_RE.search(text) is None:
        return []
    findings: list[dict[str, Any]] = []
    for auth_call in _AUTH_CALL_RE.finditer(text):
        token = auth_call.group(0).lower()
        if token.startswith("mutateasync") and re.search(
            r"mutationFn\s*:\s*[^\n]{0,240}(?:login|signIn|authenticate)",
            text,
            re.I,
        ) is None:
            continue
        prefix = text[max(0, auth_call.start() - 120) : auth_call.start()]
        if "await" not in prefix and not token.startswith("mutateasync"):
            continue
        navigation = re.search(
            r"\brouter\.(?P<method>push|replace)\s*\(",
            text[auth_call.end() : auth_call.end() + 1800],
        )
        if navigation is None:
            continue
        nav_offset = auth_call.end() + navigation.start()
        between = text[auth_call.end() : nav_offset]
        if re.search(r"\brouter\.refresh\s*\(", between):
            continue
        if _CACHE_SYNC_RE.search(between):
            continue
        call_line = _line(text, auth_call.start())
        nav_line = _line(text, nav_offset)
        findings.append(
            _finding(
                root_cause="post-auth-navigation-without-server-tree-refresh",
                path=path,
                line_start=nav_line,
                message="A successful Next.js authentication mutation performs soft navigation before refreshing server-rendered auth state.",
                evidence=(
                    f"An auth mutation begins at line {call_line} and router.{navigation.group('method')} runs at line {nav_line}. "
                    "No router.refresh or authoritative client-session synchronization occurs first, so cached Server Component chrome "
                    "can retain the pre-login identity until hard reload."
                ),
                supporting=(f"{path}:{call_line}", f"{path}:{nav_line}"),
                falsifiers=(
                    "Checked that the file uses Next.js next/navigation client routing.",
                    "Checked that the awaited mutation is wired to an explicit login/sign-in/authentication action.",
                    "Checked for router.refresh before router.push/replace.",
                    "Checked for explicit session/query invalidation before navigation.",
                ),
                verification=(
                    "Refresh or invalidate the authoritative auth-backed Server Component tree before dispatching post-login navigation, "
                    "then prove navbar/sidebar identity changes without F5."
                ),
                confidence=0.96,
            )
        )
        break
    return findings


def _supabase_session_findings(path: str, text: str) -> list[dict[str, Any]]:
    if "useNavigate" not in text or "supabase.auth.getSession" not in text:
        return []
    sign_in = re.search(r"await\s+supabase\.auth\.signInWithPassword\s*\(", text)
    if sign_in is None:
        return []
    navigation = re.search(r"\bnavigate\s*\(", text[sign_in.end() : sign_in.end() + 1600])
    if navigation is None:
        return []
    nav_offset = sign_in.end() + navigation.start()
    between = text[sign_in.end() : nav_offset]
    if _CACHE_SYNC_RE.search(between):
        return []
    if re.search(r"await\s+supabase\.auth\.(?:getSession|refreshSession)\s*\(", between):
        return []
    sign_in_line = _line(text, sign_in.start())
    nav_line = _line(text, nav_offset)
    return [
        _finding(
            root_cause="post-auth-navigation-before-session-cache-refresh",
            path=path,
            line_start=sign_in_line,
            message="A client authentication success navigates before the shared session view is synchronized.",
            evidence=(
                f"The component reads Supabase session state through getSession, completes signInWithPassword at line {sign_in_line}, "
                f"and navigates at line {nav_line} without invalidating, refetching, or directly refreshing the authoritative session. "
                "A route guard can therefore consume the stale pre-login session and redirect back to authentication."
            ),
            supporting=(f"{path}:{sign_in_line}", f"{path}:{nav_line}"),
            falsifiers=(
                "Checked that the component consumes Supabase session state and performs a password sign-in.",
                "Checked that navigation follows the successful auth mutation.",
                "Checked for React Query invalidation/refetch/reset/clear before navigation.",
                "Checked for an explicit Supabase getSession/refreshSession synchronization before navigation.",
            ),
            verification=(
                "Await invalidation or refetch of the shared session cache before navigation, then prove the destination guard observes "
                "the new session on the first login attempt."
            ),
            confidence=0.97,
        )
    ]


def run_static_js_auth_transition_review(
    root: str | Path,
    changed_files: Iterable[str],
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    changed = sorted({str(item) for item in changed_files if str(item)})
    findings: list[dict[str, Any]] = []
    readable: list[str] = []
    for path in changed:
        if Path(path).suffix.lower() not in _SOURCE_SUFFIXES:
            continue
        text = _safe_text(root_path, path)
        if not text:
            continue
        readable.append(path)
        findings.extend(_browser_cache_findings(path, text))
        findings.extend(_next_post_auth_findings(path, text))
        findings.extend(_supabase_session_findings(path, text))

    unique: dict[tuple[str, str, int], dict[str, Any]] = {}
    for finding in findings:
        unique[
            (
                str(finding.get("root_cause")),
                str(finding.get("path")),
                int(finding.get("line_start", 0)),
            )
        ] = finding
    return {
        "schema_version": "sergeant.static-js-auth-transition-review.v1",
        "mode": "model_free_static",
        "finding_count": len(unique),
        "findings": list(unique.values()),
        "readable_changed_files": readable,
        "executed_project_code": False,
    }
