from __future__ import annotations

from pathlib import Path

from main_review.static_js_remote_state_review import run_static_js_remote_state_review


def _roots(result: dict) -> set[str]:
    return {str(item.get("root_cause")) for item in result.get("findings", [])}


def test_inline_remote_record_before_local_claim_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "app.js"
    source.write_text(
        """
let liveCall = null;

function openJitsiModal() {
  if (!liveCall?.roomName) return;
  connectToRoom(liveCall.roomName);
}

async function startBrotherhoodCall(profile) {
  const roomName = `room-${Date.now()}`;
  await setDoc(doc(db, 'meta', 'liveCall'), {
    active: true,
    roomName,
    startedByName: profile.name,
  });
  openJitsiModal();
}
        """,
        encoding="utf-8",
    )
    result = run_static_js_remote_state_review(tmp_path, ["app.js"])
    assert "local-state-not-established-before-await" in _roots(result)


def test_local_claim_before_remote_record_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "app.js"
    source.write_text(
        """
let liveCall = null;

function openJitsiModal() {
  if (!liveCall?.roomName) return;
  connectToRoom(liveCall.roomName);
}

async function startBrotherhoodCall(profile) {
  const roomName = `room-${Date.now()}`;
  const callData = { active: true, roomName, startedByName: profile.name };
  liveCall = callData;
  await setDoc(doc(db, 'meta', 'liveCall'), callData);
  openJitsiModal();
}
        """,
        encoding="utf-8",
    )
    result = run_static_js_remote_state_review(tmp_path, ["app.js"])
    assert "local-state-not-established-before-await" not in _roots(result)


def test_unrelated_remote_resource_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "app.js"
    source.write_text(
        """
let liveCall = null;

function openJitsiModal() {
  connectToRoom(liveCall.roomName);
}

async function saveProfile(profile) {
  await setDoc(doc(db, 'profiles', profile.id), profile);
  openJitsiModal();
}
        """,
        encoding="utf-8",
    )
    result = run_static_js_remote_state_review(tmp_path, ["app.js"])
    assert "local-state-not-established-before-await" not in _roots(result)


def test_reentrant_map_refresh_without_request_epoch_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "MapView.tsx"
    source.write_text(
        """
const mapRef = useRef(null);
const loadedRef = useRef(false);

async function refreshStates() {
  const map = mapRef.current;
  if (!map || !loadedRef.current) return;
  const data = await fetchStates(profile, weights);
  map.getSource('states-src')?.setData(data);
}

map.on('load', () => refreshStates());
useEffect(() => {
  refreshStates();
}, [profile, JSON.stringify(weights)]);
        """,
        encoding="utf-8",
    )
    result = run_static_js_remote_state_review(tmp_path, ["MapView.tsx"])
    assert "superseded-request-publishes-imperative-state" in _roots(result)


def test_reentrant_map_refresh_with_request_epoch_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "MapView.tsx"
    source.write_text(
        """
const mapRef = useRef(null);
const loadedRef = useRef(false);
const statesReqRef = useRef(0);

async function refreshStates() {
  const map = mapRef.current;
  if (!map || !loadedRef.current) return;
  const id = ++statesReqRef.current;
  const data = await fetchStates(profile, weights);
  if (id !== statesReqRef.current) return;
  map.getSource('states-src')?.setData(data);
}

map.on('load', () => refreshStates());
useEffect(() => {
  const timer = window.setTimeout(refreshStates, 300);
  return () => clearTimeout(timer);
}, [profile, JSON.stringify(weights)]);
        """,
        encoding="utf-8",
    )
    result = run_static_js_remote_state_review(tmp_path, ["MapView.tsx"])
    assert "superseded-request-publishes-imperative-state" not in _roots(result)


def test_auth_mutation_without_principal_cache_invalidation_is_reported(tmp_path: Path) -> None:
    hook = tmp_path / "useFetchMe.ts"
    hook.write_text(
        """
export function useFetchMe() {
  const [me, setMe] = useState(null);
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
    auth = tmp_path / "auth.ts"
    auth.write_text(
        """
export async function login(email, password) {
  const response = await fetch('/api/auth/login', { method: 'POST' });
  if (!response.ok) throw new Error('login failed');
}

export async function logout() {
  const response = await fetch('/api/auth/logout', { method: 'POST' });
  if (!response.ok) throw new Error('logout failed');
}
        """,
        encoding="utf-8",
    )
    result = run_static_js_remote_state_review(
        tmp_path,
        ["useFetchMe.ts", "auth.ts"],
    )
    assert "auth-session-change-not-invalidating-client-principal" in _roots(result)


def test_auth_event_and_latest_request_guard_are_clean(tmp_path: Path) -> None:
    hook = tmp_path / "useFetchMe.ts"
    hook.write_text(
        """
export function useFetchMe() {
  const [me, setMe] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    let latestRequest = 0;
    const run = () => {
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
    auth = tmp_path / "auth.ts"
    auth.write_text(
        """
export const AUTH_CHANGED_EVENT = 'auth-changed';
function dispatchAuthChanged() {
  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
}

export async function login(email, password) {
  const response = await fetch('/api/auth/login', { method: 'POST' });
  if (!response.ok) throw new Error('login failed');
  dispatchAuthChanged();
}

export async function logout() {
  const response = await fetch('/api/auth/logout', { method: 'POST' });
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


def test_mount_only_non_auth_fetch_without_auth_mutations_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "useSettings.ts"
    source.write_text(
        """
export function useSettings() {
  const [settings, setSettings] = useState(null);
  useEffect(() => {
    fetchSettings().then(setSettings);
  }, []);
  return settings;
}
        """,
        encoding="utf-8",
    )
    result = run_static_js_remote_state_review(tmp_path, ["useSettings.ts"])
    assert "auth-session-change-not-invalidating-client-principal" not in _roots(result)
