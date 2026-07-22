from __future__ import annotations

from pathlib import Path

from main_review.static_status_review import run_static_status_review
from main_review.static_transfer_26_review import run_static_transfer_26_review

C_ROOT = "protocol-operation-uses-resource-before-open-identity"
HASKELL_ROOT = "prepended-diagnostics-published-in-reverse-order"


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _roots(result: dict) -> set[str]:
    return {str(item.get("root_cause")) for item in result.get("findings", [])}


def test_c_protocol_work_must_require_open_stream_identity(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "http2.c",
        r'''
static CURLcode progress(struct filter *cf, struct easy *data)
{
  struct stream_ctx *stream = STREAM_CTX(data);

  if(weight_changed(data) || parent_changed(data)) {
    struct priority_spec spec;
    build_priority(data, &spec);
    LOG("stream=%d", stream->id);
    submit_priority(cf->session, stream->id, &spec);
  }
  return OK;
}
''',
    )

    result = run_static_transfer_26_review(tmp_path, ["http2.c"])

    assert C_ROOT in _roots(result)


def test_c_protocol_work_guarding_pointer_and_identity_is_clean(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "http2.c",
        r'''
static CURLcode progress(struct filter *cf, struct easy *data)
{
  struct stream_ctx *stream = STREAM_CTX(data);

  if(stream && stream->id > 0 &&
     (weight_changed(data) || parent_changed(data))) {
    struct priority_spec spec;
    build_priority(data, &spec);
    LOG("stream=%d", stream->id);
    submit_priority(cf->session, stream->id, &spec);
  }
  return OK;
}
''',
    )

    result = run_static_transfer_26_review(tmp_path, ["http2.c"])

    assert C_ROOT not in _roots(result)


def test_c_protocol_work_with_fail_fast_null_guard_is_clean(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "channel.c",
        r'''
static int flush_channel(struct owner *owner)
{
  struct channel_ctx *channel = CHANNEL_CTX(owner);
  if(!channel)
    return NOT_READY;

  if(channel->id > 0 && pending(owner)) {
    send_frame(owner->session, channel->id);
  }
  return OK;
}
''',
    )

    result = run_static_transfer_26_review(tmp_path, ["channel.c"])

    assert C_ROOT not in _roots(result)


def test_haskell_prepend_accumulator_must_not_be_published_directly(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "ParseResult.hs",
        r'''
data ParseState = ParseState [Warning] [Error]

runParseResult parser = execute parser emptyState failure success
  where
    failure (ParseState warns errors) = (warns, Left errors)
    success (ParseState warns []) value = (warns, Right value)
    success (ParseState warns errors) _ = (warns, Left errors)

parseWarning warning = update $ \(ParseState warns errors) ->
  ParseState (warning : warns) errors

parseWarnings newWarns = update $ \(ParseState warns errors) ->
  ParseState (newWarns ++ warns) errors
''',
    )

    result = run_static_transfer_26_review(tmp_path, ["ParseResult.hs"])

    assert HASKELL_ROOT in _roots(result)


def test_haskell_prepend_accumulator_reversed_at_boundary_is_clean(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "ParseResult.hs",
        r'''
data ParseState = ParseState [Warning] [Error]

runParseResult parser = execute parser emptyState failure success
  where
    failure (ParseState warns errors) = (reverse warns, Left errors)
    success (ParseState warns []) value = (reverse warns, Right value)

parseWarning warning = update $ \(ParseState warns errors) ->
  ParseState (warning : warns) errors
''',
    )

    result = run_static_transfer_26_review(tmp_path, ["ParseResult.hs"])

    assert HASKELL_ROOT not in _roots(result)


def test_haskell_prepend_accumulator_sorted_by_helper_is_clean(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "ParseResult.hs",
        r'''
data ParseState = ParseState [Warning] [Error]

runParseResult parser = execute parser emptyState failure success
  where
    failure (ParseState warns errors) = (sortWarns warns, Left errors)
    success (ParseState warns []) value = (sortWarns warns, Right value)
    sortWarns = sortBy (comparing warningPosition)

parseWarning warning = update $ \(ParseState warns errors) ->
  ParseState (warning : warns) errors
''',
    )

    result = run_static_transfer_26_review(tmp_path, ["ParseResult.hs"])

    assert HASKELL_ROOT not in _roots(result)


def test_haskell_append_in_source_order_is_clean(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "ParseResult.hs",
        r'''
data ParseState = ParseState [Warning] [Error]

runParseResult parser = execute parser emptyState failure success
  where
    failure (ParseState warnings errors) = (warnings, Left errors)
    success (ParseState warnings []) value = (warnings, Right value)

parseWarning warning = update $ \(ParseState warnings errors) ->
  ParseState (warnings ++ [warning]) errors
''',
    )

    result = run_static_transfer_26_review(tmp_path, ["ParseResult.hs"])

    assert HASKELL_ROOT not in _roots(result)


def test_normal_static_status_path_admits_transfer_26_roots(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "http2.c",
        r'''
static int progress(struct owner *owner)
{
  struct stream_ctx *stream = STREAM_CTX(owner);
  if(priority_changed(owner)) {
    queue_priority(owner->session, stream->id);
  }
  return 0;
}
''',
    )
    _write(
        tmp_path,
        "ParseResult.hs",
        r'''
data ParseState = ParseState [Warning] [Error]
runParseResult parser = execute parser emptyState failure success
  where
    failure (ParseState warnings errors) = (warnings, Left errors)
    success (ParseState warnings []) value = (warnings, Right value)
parseWarning warning = update $ \(ParseState warnings errors) ->
  ParseState (warning : warnings) errors
''',
    )

    result = run_static_status_review(tmp_path, ["http2.c", "ParseResult.hs"])

    roots = _roots(result)
    assert C_ROOT in roots
    assert HASKELL_ROOT in roots
