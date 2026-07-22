from __future__ import annotations

from pathlib import Path

from main_review.static_transfer_11_review import run_static_transfer_11_review


RUST_ROOT = "rust-str-sliced-at-unverified-byte-boundary"
TIMER_ROOT = "recurring-timer-created-without-owned-handle"
OWNED_TIMER_ROOT = "owned-recurring-timer-without-teardown"
MAP_ROOT = "empty-retained-container-not-removed-after-member-delete"
TLS_ROOT = "custom-ca-bundle-replaces-public-trust-roots"


def _roots(result: dict) -> set[str]:
    return {str(item.get("root_cause")) for item in result.get("findings", [])}


def test_rust_str_slice_at_numeric_byte_cap_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "graph.rs"
    source.write_text(
        """
fn update_fts(content: &str) {
    let clipped = &content[..content.len().min(4000)];
    write(clipped);
}
        """,
        encoding="utf-8",
    )

    result = run_static_transfer_11_review(tmp_path, ["graph.rs"])

    assert RUST_ROOT in _roots(result)


def test_rust_char_boundary_helper_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "graph.rs"
    source.write_text(
        """
fn truncate_on_char_boundary(s: &str, max_bytes: usize) -> &str {
    let mut end = max_bytes.min(s.len());
    while end > 0 && !s.is_char_boundary(end) { end -= 1; }
    &s[..end]
}
fn update_fts(content: &str) {
    write(truncate_on_char_boundary(content, 4000));
}
        """,
        encoding="utf-8",
    )

    result = run_static_transfer_11_review(tmp_path, ["graph.rs"])

    assert RUST_ROOT not in _roots(result)


def test_rust_byte_buffer_slice_is_not_misclassified_as_utf8(tmp_path: Path) -> None:
    source = tmp_path / "buffer.rs"
    source.write_text(
        """
fn prefix(data: &[u8]) -> &[u8] {
    &data[..data.len().min(4000)]
}
        """,
        encoding="utf-8",
    )

    result = run_static_transfer_11_review(tmp_path, ["buffer.rs"])

    assert RUST_ROOT not in _roots(result)


def test_unowned_interval_and_empty_map_entry_are_reported(tmp_path: Path) -> None:
    source = tmp_path / "WebRTCSignalingServer.js"
    source.write_text(
        """
class WebRTCSignalingServer {
  constructor() {
    this.peers = new Map();
    this.meshes = new Map();
  }
  handleDisconnect(peerId) {
    const peer = this.peers.get(peerId);
    const meshId = peer.meshId;
    this.meshes.get(meshId).delete(peerId);
    this.peers.delete(peerId);
  }
  startDiscovery() {
    setInterval(() => this.broadcast(), 30000);
  }
}
        """,
        encoding="utf-8",
    )

    result = run_static_transfer_11_review(tmp_path, ["WebRTCSignalingServer.js"])
    roots = _roots(result)

    assert TIMER_ROOT in roots
    assert MAP_ROOT in roots


def test_owned_interval_and_empty_map_cleanup_are_clean(tmp_path: Path) -> None:
    source = tmp_path / "WebRTCSignalingServer.js"
    source.write_text(
        """
class WebRTCSignalingServer {
  handleDisconnect(peerId) {
    const peer = this.peers.get(peerId);
    const meshId = peer.meshId;
    this.meshes.get(meshId).delete(peerId);
    if (this.meshes.get(meshId).size === 0) {
      this.meshes.delete(meshId);
    }
    this.peers.delete(peerId);
  }
  startDiscovery() {
    this.discoveryInterval = setInterval(() => this.broadcast(), 30000);
  }
  destroy() {
    clearInterval(this.discoveryInterval);
  }
}
        """,
        encoding="utf-8",
    )

    result = run_static_transfer_11_review(tmp_path, ["WebRTCSignalingServer.js"])
    roots = _roots(result)

    assert TIMER_ROOT not in roots
    assert OWNED_TIMER_ROOT not in roots
    assert MAP_ROOT not in roots


def test_owned_interval_without_clear_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "server.ts"
    source.write_text(
        """
class Server {
  start() {
    this.timer = setInterval(() => this.poll(), 1000);
  }
}
        """,
        encoding="utf-8",
    )

    result = run_static_transfer_11_review(tmp_path, ["server.ts"])

    assert OWNED_TIMER_ROOT in _roots(result)


def test_proxy_only_ca_bundle_replacing_public_roots_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "net.py"
    source.write_text(
        """
import os

CA_BUNDLE = (os.environ.get("REQUESTS_CA_BUNDLE")
             or os.environ.get("CURL_CA_BUNDLE")
             or "/root/proxy/ca-bundle.crt")
VERIFY = CA_BUNDLE if os.path.exists(CA_BUNDLE) else True
        """,
        encoding="utf-8",
    )

    result = run_static_transfer_11_review(tmp_path, ["net.py"])

    assert TLS_ROOT in _roots(result)


def test_combined_public_and_private_ca_roots_are_clean(tmp_path: Path) -> None:
    source = tmp_path / "net.py"
    source.write_text(
        """
import os
import certifi

CA_BUNDLE = (os.environ.get("REQUESTS_CA_BUNDLE")
             or os.environ.get("CURL_CA_BUNDLE")
             or "/root/proxy/ca-bundle.crt")

def build_verify():
    public_roots = certifi.where()
    if os.path.exists(CA_BUNDLE):
        return concatenate(public_roots, CA_BUNDLE)
    return public_roots

VERIFY = build_verify()
        """,
        encoding="utf-8",
    )

    result = run_static_transfer_11_review(tmp_path, ["net.py"])

    assert TLS_ROOT not in _roots(result)
