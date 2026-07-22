from __future__ import annotations

from pathlib import Path

from main_review.static_js_controller_epoch_review import run_static_js_controller_epoch_review


def _roots(result: dict) -> set[str]:
    return {str(item.get("root_cause")) for item in result.get("findings", [])}


def test_multiline_cancellable_then_unowned_await_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "banking.js"
    source.write_text(
        """
const banks = new Map();
let bankCtl = null;

async function bankOne(idx) {
  const ctl = new AbortController();
  bankCtl = ctl;
  const blob = await fetchAudio({
    signal: ctl.signal,
    onProgress: () => {},
  });
  const persisted = await bufferTrack(
    currentBook,
    idx,
    blob
  );
  if (!persisted) banks.set(idx, blob);
}
        """,
        encoding="utf-8",
    )
    result = run_static_js_controller_epoch_review(tmp_path, ["banking.js"])
    assert "ownership-token-not-revalidated-after-await" in _roots(result)


def test_multiline_owner_check_after_second_await_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "banking.js"
    source.write_text(
        """
const banks = new Map();
let bankCtl = null;

async function bankOne(idx) {
  const ctl = new AbortController();
  bankCtl = ctl;
  const blob = await fetchAudio({
    signal: ctl.signal,
    onProgress: () => {},
  });
  const persisted = await bufferTrack(
    currentBook,
    idx,
    blob
  );
  if (bankCtl !== ctl) return;
  if (!persisted) banks.set(idx, blob);
}
        """,
        encoding="utf-8",
    )
    result = run_static_js_controller_epoch_review(tmp_path, ["banking.js"])
    assert "ownership-token-not-revalidated-after-await" not in _roots(result)
