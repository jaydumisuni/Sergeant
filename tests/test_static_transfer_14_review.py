from __future__ import annotations

from pathlib import Path

from main_review.static_status_review import run_static_status_review
from main_review.static_transfer_14_review import run_static_transfer_14_review


MEASUREMENT_ROOT = "unknown-external-entity-assigned-synthetic-measurement"
PROXY_ROOT = "generic-proxy-exact-path-policy-cannot-authorize-parameterized-routes"
CACHE_ROOT = "read-through-cache-writeback-not-ordered-with-invalidation"


def _roots(result: dict) -> set[str]:
    return {str(item.get("root_cause")) for item in result.get("findings", [])}


def test_unknown_model_borrowing_numeric_default_price_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "costs.py"
    source.write_text(
        '''
MODEL_PRICES = {
    "known": {"input": 2.0, "output": 8.0},
    "default": {"input": 1.0, "output": 3.0},
}

def estimate_cost_usd(model: str | None, input_tokens: int, output_tokens: int) -> float:
    price = MODEL_PRICES.get(model or "default", MODEL_PRICES["default"])
    return input_tokens * price["input"] + output_tokens * price["output"]
        ''',
        encoding="utf-8",
    )

    result = run_static_transfer_14_review(tmp_path, ["costs.py"])

    assert MEASUREMENT_ROOT in _roots(result)


def test_unknown_price_returning_explicit_none_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "costs.py"
    source.write_text(
        '''
MODEL_PRICES = {"known": {"input": 2.0, "output": 8.0}}

def estimate_cost_usd(model: str | None, input_tokens: int, output_tokens: int) -> float | None:
    price = MODEL_PRICES.get(model or "")
    if price is None:
        return None
    return input_tokens * price["input"] + output_tokens * price["output"]
        ''',
        encoding="utf-8",
    )

    result = run_static_transfer_14_review(tmp_path, ["costs.py"])

    assert MEASUREMENT_ROOT not in _roots(result)


def test_non_measurement_default_lookup_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "themes.py"
    source.write_text(
        '''
THEMES = {"default": {"padding": 12}, "compact": {"padding": 4}}

def resolve_theme(name: str):
    return THEMES.get(name, THEMES["default"])
        ''',
        encoding="utf-8",
    )

    result = run_static_transfer_14_review(tmp_path, ["themes.py"])

    assert MEASUREMENT_ROOT not in _roots(result)


def test_generic_proxy_with_literal_path_set_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "route.ts"
    source.write_text(
        '''
const ALLOWED_PATHS = new Set<string>([
  "/api/agents",
  "/api/repo",
  "/api/system/pause",
]);

// Universal action proxy: callers provide { path, body }.
export async function POST(req: NextRequest) {
  const { path, body } = await req.json();
  if (!ALLOWED_PATHS.has(path)) return forbidden();
  return fetch(`${base}${path}`, { method: "POST", body: JSON.stringify(body) });
}
        ''',
        encoding="utf-8",
    )

    result = run_static_transfer_14_review(tmp_path, ["route.ts"])

    assert PROXY_ROOT in _roots(result)


def test_generic_proxy_with_anchored_route_patterns_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "route.ts"
    source.write_text(
        '''
const ALLOWED_PATH_PATTERNS: RegExp[] = [
  /^\\/api\\/agents\\/[\\w.-]+\\/toggle$/,
  /^\\/api\\/repo\\/[\\w.-]+\\/audit$/,
];

// Universal action proxy: callers provide { path, body }.
export async function POST(req: NextRequest) {
  const { path, body } = await req.json();
  if (!ALLOWED_PATH_PATTERNS.some((pattern) => pattern.test(path))) return forbidden();
  return fetch(`${base}${path}`, { method: "POST", body: JSON.stringify(body) });
}
        ''',
        encoding="utf-8",
    )

    result = run_static_transfer_14_review(tmp_path, ["route.ts"])

    assert PROXY_ROOT not in _roots(result)


def test_fixed_endpoint_adapter_is_not_misclassified_as_generic_proxy(tmp_path: Path) -> None:
    source = tmp_path / "route.ts"
    source.write_text(
        '''
const ALLOWED_PATHS = new Set(["/api/system/pause", "/api/system/resume"]);
export async function POST(req: NextRequest) {
  const body = await req.json();
  return fetch(`${base}/api/system/pause`, { method: "POST", body: JSON.stringify(body) });
}
        ''',
        encoding="utf-8",
    )

    result = run_static_transfer_14_review(tmp_path, ["route.ts"])

    assert PROXY_ROOT not in _roots(result)


def test_explicit_static_only_proxy_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "route.ts"
    source.write_text(
        '''
// Universal proxy for only static routes; resource-specific endpoints are intentionally excluded.
const ALLOWED_PATHS = new Set(["/api/pause", "/api/resume"]);
export async function POST(req: NextRequest) {
  const { path, body } = await req.json();
  if (!ALLOWED_PATHS.has(path)) return forbidden();
  return fetch(`${base}${path}`, { method: "POST", body: JSON.stringify(body) });
}
        ''',
        encoding="utf-8",
    )

    result = run_static_transfer_14_review(tmp_path, ["route.ts"])

    assert PROXY_ROOT not in _roots(result)


def test_cache_fill_without_generation_ordering_is_reported(tmp_path: Path) -> None:
    resolve = tmp_path / "resolve.go"
    resolve.write_text(
        '''
package cache

func (m *Manager) lookup(ctx context.Context, code string) (Link, error) {
    link, err := m.store.Get(ctx, code)
    if err != nil { return Link{}, err }
    m.cacheSet(ctx, code, link)
    return link, nil
}

func (m *Manager) cacheSet(ctx context.Context, code string, link Link) {
    _ = m.cacheStore.Set(ctx, code, link)
}
        ''',
        encoding="utf-8",
    )
    lifecycle = tmp_path / "manager.go"
    lifecycle.write_text(
        '''
package cache

func (m *Manager) Delete(ctx context.Context, code string) error {
    if err := m.store.Delete(ctx, code); err != nil { return err }
    m.invalidateCache(ctx, code)
    return nil
}

func (m *Manager) invalidateCache(ctx context.Context, code string) {
    _ = m.cacheStore.Delete(ctx, code)
}
        ''',
        encoding="utf-8",
    )

    result = run_static_transfer_14_review(tmp_path, ["resolve.go", "manager.go"])

    assert CACHE_ROOT in _roots(result)


def test_cache_fill_with_generation_snapshot_and_compare_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "resolve.go"
    source.write_text(
        '''
package cache

func (m *Manager) lookup(ctx context.Context, code string) (Link, error) {
    gen := m.cacheGen.Load()
    link, err := m.store.Get(ctx, code)
    if err != nil { return Link{}, err }
    m.cacheSet(ctx, code, link)
    if m.cacheGen.Load() != gen { _ = m.cacheStore.Delete(ctx, code) }
    return link, nil
}

func (m *Manager) invalidateCache(ctx context.Context, code string) {
    m.cacheGen.Add(1)
    _ = m.cacheStore.Delete(ctx, code)
}
        ''',
        encoding="utf-8",
    )

    result = run_static_transfer_14_review(tmp_path, ["resolve.go"])

    assert CACHE_ROOT not in _roots(result)


def test_cache_without_mutation_invalidation_path_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "lookup.go"
    source.write_text(
        '''
package cache

func lookup(ctx context.Context, key string) (Item, error) {
    item, err := store.Get(ctx, key)
    if err != nil { return Item{}, err }
    cacheSet(ctx, key, item)
    return item, nil
}
        ''',
        encoding="utf-8",
    )

    result = run_static_transfer_14_review(tmp_path, ["lookup.go"])

    assert CACHE_ROOT not in _roots(result)


def test_status_bundle_exposes_all_transfer_14_roots(tmp_path: Path) -> None:
    costs = tmp_path / "costs.py"
    costs.write_text(
        '''
SERVICE_RATES = {"known": {"unit": 2.0}, "fallback": {"unit": 1.0}}
def estimate_charge(service: str) -> float:
    rate = SERVICE_RATES.get(service, SERVICE_RATES["fallback"])
    return rate["unit"]
        ''',
        encoding="utf-8",
    )
    route = tmp_path / "route.ts"
    route.write_text(
        '''
const ALLOWED_ROUTES = new Set(["/api/items", "/api/jobs"]);
// Generic proxy for action calls.
async function POST(req: Request) {
  const { path, body } = await req.json();
  if (!ALLOWED_ROUTES.has(path)) return forbidden();
  return fetch(`${base}${path}`, { method: "POST", body });
}
        ''',
        encoding="utf-8",
    )
    resolve = tmp_path / "resolve.go"
    resolve.write_text(
        '''
package cache
func lookup(ctx context.Context, key string) (Item, error) {
    item, err := store.Get(ctx, key)
    if err != nil { return Item{}, err }
    cacheSet(ctx, key, item)
    return item, nil
}
func invalidateCache(ctx context.Context, key string) { _ = cacheStore.Delete(ctx, key) }
        ''',
        encoding="utf-8",
    )

    result = run_static_status_review(tmp_path, ["costs.py", "route.ts", "resolve.go"])

    assert {MEASUREMENT_ROOT, PROXY_ROOT, CACHE_ROOT}.issubset(_roots(result))
    assert result["static_transfer_14_review"]["finding_count"] == 3
