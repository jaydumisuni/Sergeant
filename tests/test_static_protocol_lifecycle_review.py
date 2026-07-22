from __future__ import annotations

from pathlib import Path

from main_review.static_protocol_lifecycle_review import run_static_protocol_lifecycle_review
from main_review.static_status_review import run_static_status_review

ROOT = "protocol-operation-uses-resource-before-open-identity"


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _roots(result: dict) -> set[str]:
    return {str(item.get("root_cause")) for item in result.get("findings", [])}


def test_prefixed_protocol_action_requires_open_identity(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "http2.c",
        r'''
static CURLcode h2_progress_egress(struct Curl_cfilter *cf,
                                   struct Curl_easy *data)
{
  struct stream_ctx *stream = H2_STREAM_CTX(data);
  if(weight_changed(data) || parent_changed(data)) {
    nghttp2_priority_spec pri_spec;
    build_priority(data, &pri_spec);
    DEBUGASSERT(stream->id != -1);
    nghttp2_submit_priority(cf->ctx, 0, stream->id, &pri_spec);
  }
  return CURLE_OK;
}
''',
    )

    result = run_static_protocol_lifecycle_review(tmp_path, ["http2.c"])

    assert ROOT in _roots(result)


def test_prefixed_protocol_action_with_pointer_and_identity_guard_is_clean(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "http2.c",
        r'''
static CURLcode h2_progress_egress(struct Curl_cfilter *cf,
                                   struct Curl_easy *data)
{
  struct stream_ctx *stream = H2_STREAM_CTX(data);
  if(stream && stream->id > 0 &&
     (weight_changed(data) || parent_changed(data))) {
    nghttp2_priority_spec pri_spec;
    build_priority(data, &pri_spec);
    nghttp2_submit_priority(cf->ctx, 0, stream->id, &pri_spec);
  }
  return CURLE_OK;
}
''',
    )

    result = run_static_protocol_lifecycle_review(tmp_path, ["http2.c"])

    assert ROOT not in _roots(result)


def test_prefixed_protocol_action_after_fail_fast_guard_is_clean(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "http2.c",
        r'''
static CURLcode h2_progress_egress(struct Curl_cfilter *cf,
                                   struct Curl_easy *data)
{
  struct stream_ctx *stream = H2_STREAM_CTX(data);
  if(!stream)
    return CURLE_AGAIN;

  if(stream->id > 0 && weight_changed(data)) {
    nghttp2_submit_priority(cf->ctx, 0, stream->id, NULL);
  }
  return CURLE_OK;
}
''',
    )

    result = run_static_protocol_lifecycle_review(tmp_path, ["http2.c"])

    assert ROOT not in _roots(result)


def test_normal_status_path_admits_prefixed_protocol_root(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "http2.c",
        r'''
static int progress(struct owner *owner)
{
  struct stream_ctx *stream = H2_STREAM_CTX(owner);
  if(priority_changed(owner)) {
    nghttp2_submit_priority(owner->session, 0, stream->id, NULL);
  }
  return 0;
}
''',
    )

    result = run_static_status_review(tmp_path, ["http2.c"])

    assert ROOT in _roots(result)
