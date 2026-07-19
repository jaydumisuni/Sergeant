from __future__ import annotations

from pathlib import Path

from main_review.static_js_await_ownership_review import (
    run_static_js_await_ownership_review,
)


def _roots(result: dict) -> set[str]:
    return {str(item.get("root_cause")) for item in result.get("findings", [])}


def test_inline_remote_payload_before_optional_chain_consumer_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "app.js"
    source.write_text(
        """
let liveCall = null;

function openJitsiModal() {
  if (!liveCall?.roomName) return;
  frame.src = `https://meet.example/${liveCall.roomName}`;
}

async function startBrotherhoodCall(profile) {
  const roomName = `room-${Date.now()}`;
  const hostName = profile?.name || "Mentor";
  await setDoc(doc(db, "meta", "liveCall"), {
    active: true,
    roomName,
    startedByName: hostName,
  });
  openJitsiModal();
}
        """,
        encoding="utf-8",
    )

    result = run_static_js_await_ownership_review(tmp_path, ["app.js"])

    assert "local-state-not-established-before-await" in _roots(result)


def test_state_assignment_before_remote_write_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "app.js"
    source.write_text(
        """
let liveCall = null;

function openJitsiModal() {
  if (!liveCall?.roomName) return;
  frame.src = `https://meet.example/${liveCall.roomName}`;
}

async function startBrotherhoodCall(profile) {
  const callData = {
    active: true,
    roomName: `room-${Date.now()}`,
    startedByName: profile?.name || "Mentor",
  };
  liveCall = callData;
  await setDoc(doc(db, "meta", "liveCall"), callData);
  openJitsiModal();
}
        """,
        encoding="utf-8",
    )

    result = run_static_js_await_ownership_review(tmp_path, ["app.js"])

    assert "local-state-not-established-before-await" not in _roots(result)


def test_unrelated_helper_state_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "app.js"
    source.write_text(
        """
let liveCall = null;

function showToast() {
  toast("Saved");
}

async function saveProfile(profile) {
  await setDoc(doc(db, "profiles", profile.id), { name: profile.name });
  showToast();
}
        """,
        encoding="utf-8",
    )

    result = run_static_js_await_ownership_review(tmp_path, ["app.js"])

    assert "local-state-not-established-before-await" not in _roots(result)
