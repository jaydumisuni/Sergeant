from __future__ import annotations

from pathlib import Path

from main_review.static_js_remote_state_review import run_static_js_remote_state_review


def _roots(result: dict) -> set[str]:
    return {str(item.get("root_cause")) for item in result.get("findings", [])}


def test_annotated_auth_mutations_without_cache_signal_are_reported(tmp_path: Path) -> None:
    (tmp_path / "useFetchMe.ts").write_text(
        """
export interface UseFetchMeResult {
  me: MeResponse | null;
  loading: boolean;
}

export function useFetchMe(): UseFetchMeResult {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    fetchMe()
      .then(result => { if (active) setMe(result); })
      .catch(() => { if (active) setMe(null); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  return { me, loading };
}
        """,
        encoding="utf-8",
    )
    (tmp_path / "auth.ts").write_text(
        """
export async function login(email: string, password: string): Promise<void> {
  const response = await fetch('/api/proxy/api/auth/login', { method: 'POST' });
  if (!response.ok) throw new Error('login failed');
}

export async function logout(): Promise<void> {
  const response = await fetch('/api/proxy/api/auth/logout', { method: 'POST' });
  if (!response.ok) throw new Error('logout failed');
}

export async function loginWithPasskey(email: string): Promise<void> {
  const response = await fetch('/api/proxy/api/auth/webauthn/login/finish', { method: 'POST' });
  if (!response.ok) throw new Error('passkey failed');
}
        """,
        encoding="utf-8",
    )

    result = run_static_js_remote_state_review(
        tmp_path,
        ["useFetchMe.ts", "auth.ts"],
    )

    assert "auth-session-change-not-invalidating-client-principal" in _roots(result)


def test_annotated_auth_mutations_with_event_and_request_epoch_are_clean(tmp_path: Path) -> None:
    (tmp_path / "useFetchMe.ts").write_text(
        """
export function useFetchMe(): UseFetchMeResult {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    let latestRequest = 0;
    const run = (): void => {
      const requestId = ++latestRequest;
      const isCurrent = () => active && requestId === latestRequest;
      fetchMe()
        .then(result => { if (isCurrent()) setMe(result); })
        .catch(() => { if (isCurrent()) setMe(null); })
        .finally(() => { if (isCurrent()) setLoading(false); });
    };
    run();
    window.addEventListener(AUTH_CHANGED_EVENT, run);
    return () => {
      active = false;
      window.removeEventListener(AUTH_CHANGED_EVENT, run);
    };
  }, []);
  return { me, loading };
}
        """,
        encoding="utf-8",
    )
    (tmp_path / "auth.ts").write_text(
        """
export const AUTH_CHANGED_EVENT = 'auth-changed';
function dispatchAuthChanged(): void {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
  }
}

export async function login(email: string, password: string): Promise<void> {
  const response = await fetch('/api/proxy/api/auth/login', { method: 'POST' });
  if (!response.ok) throw new Error('login failed');
  dispatchAuthChanged();
}

export async function logout(): Promise<void> {
  const response = await fetch('/api/proxy/api/auth/logout', { method: 'POST' });
  if (!response.ok) throw new Error('logout failed');
  dispatchAuthChanged();
}
        """,
        encoding="utf-8",
    )

    result = run_static_js_remote_state_review(
        tmp_path,
        ["useFetchMe.ts", "auth.ts"],
    )

    assert "auth-session-change-not-invalidating-client-principal" not in _roots(result)
