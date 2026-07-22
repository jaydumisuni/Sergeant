from __future__ import annotations

from pathlib import Path

from main_review.static_transfer_29_review import run_static_transfer_29_review


def _run(tmp_path: Path, files: dict[str, str]):
    for relative, source in files.items():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
    return run_static_transfer_29_review(tmp_path, files)


def _roots(result: dict) -> set[str]:
    return {str(item["root_cause"]) for item in result["findings"]}


def test_specialized_namespaces_cannot_share_plain_type_uid_lookup(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        {
            "typing/env.ml": '''
let find_type_data path env =
  match path with
  | Pextra_ty (p, Pcstr_ty s) -> type_of_cstr path (find_cstr p s env)
  | Pident _ | Pdot _ -> find_type_data path env

let find_cstr path name env = find_constructor path name env
let find_ident_label id env = TycompTbl.find_same id env.labels

let find_uid namespace path env =
  try Option.some @@ match namespace with
  | Value -> (find_value path env).val_uid
  | Type | Extension_constructor | Constructor | Label ->
      let path = normalize_type_path None env path in
      let td = find_type path env in
      td.type_uid
  | Module -> (find_module path env).md_uid
  with Not_found -> None
'''
        },
    )

    assert "specialized-namespace-paths-collapsed-into-ordinary-type-lookup" in _roots(result)


def test_specialized_namespace_dispatch_is_clean_when_split(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        {
            "typing/env.ml": '''
let find_type_data path env =
  match path with
  | Pextra_ty (p, Pcstr_ty s) -> type_of_cstr path (find_cstr p s env)
  | Pident _ | Pdot _ -> find_type_data path env

let find_uid namespace path env =
  try Option.some @@ match namespace with
  | Type -> (find_type (normalize_type_path None env path) env).type_uid
  | Extension_constructor -> (find_extension_full path env).cda_description.cstr_uid
  | Constructor ->
      let ty, name = find_path_extra path in
      (find_cstr ty name env).cstr_uid
  | Label ->
      let ty, name = find_path_extra path in
      (find_label ty name env).lbl_uid
  | Value -> (find_value path env).val_uid
  with Not_found -> None
'''
        },
    )

    assert result["finding_count"] == 0


def test_julia_string_boundary_and_count_contracts_are_actionable(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        {
            "base/strings/string.jl": '''
function thisind(s::String, i::Int)
    n = ncodeunits(s)
    i == n + 1 && return i
    @boundscheck between(i, 0, n) || throw(BoundsError(s, i))
    @inbounds b = codeunit(s, i)
    b & 0xc0 == 0x80 || return i
    @inbounds b = codeunit(s, i-1)
    between(b, 0xc0, 0xf7) && return i-1
    return i
end

function length(s::String, i::Int, j::Int)
    j < i && return 0
    c = j - i + 1
    @inbounds i, k = thisind(s, i), i
    c -= i < k
    _length(s, i, j, c)
end
'''
        },
    )

    roots = _roots(result)
    assert "unchecked-backward-codeunit-read-precedes-lower-bound-proof" in roots
    assert "byte-span-count-fixed-before-character-boundary-alignment" in roots


def test_julia_string_boundary_and_count_contracts_are_clean_when_aligned(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        {
            "base/strings/string.jl": '''
function thisind(s::String, i::Int)
    i == 0 && return 0
    n = ncodeunits(s)
    @boundscheck between(i, 1, n) || throw(BoundsError(s, i))
    @inbounds b = codeunit(s, i)
    b & 0xc0 == 0x80 || return i
    i > 1 || return i
    @inbounds b = codeunit(s, i-1)
    return between(b, 0xc0, 0xf7) ? i-1 : i
end

function length(s::String, i::Int, j::Int)
    j < i && return 0
    @inbounds i, k = thisind(s, i), i
    c = j - i + (i == k)
    _length(s, i, j, c)
end
'''
        },
    )

    assert result["finding_count"] == 0


def test_optional_ktls_acceleration_cannot_fail_valid_handshake(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        {
            "src/openssl/ssl/context.cr": '''
protected def initialize(method)
  add_options(OpenSSL::SSL::Options.flags(ALL))
  remove_options(OpenSSL::SSL::Options::ENABLE_KTLS)
end
''',
            "src/openssl/ssl/socket.cr": '''
private def ktls_safe_handshake(&)
  io = bio.io
  if @context.options.includes?(OpenSSL::SSL::Options::ENABLE_KTLS)
    unless io.@in_buffer_rem.empty?
      raise Error.new("TLS handshake with KTLS enabled requires the read buffer to be empty")
    end
  end
  yield
end
''',
            "src/openssl/bio.cr": '''
def self.ctrl(b, cmd, num, ptr)
  case cmd
  when LibCrypto::CTRL_SET_KTLS
    socket = bio.socket
    is_tx = num != 0
    KTLS.enable(socket)
    if KTLS.start(socket, ptr, is_tx)
      1
    else
      0
    end
  end
end
''',
        },
    )

    assert "optional-transport-acceleration-failure-escalated-to-handshake-error" in _roots(result)


def test_optional_ktls_acceleration_is_clean_when_it_falls_back(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        {
            "src/openssl/ssl/context.cr": '''
protected def initialize(method)
  add_options(OpenSSL::SSL::Options.flags(ALL))
end
''',
            "src/openssl/ssl/socket.cr": '''
private def ktls_safe_handshake(&)
  io = bio.io
  if @context.options.includes?(OpenSSL::SSL::Options::ENABLE_KTLS)
    io.read_buffering = false if io.read_buffering?
  end
  yield
end
''',
            "src/openssl/bio.cr": '''
def self.ctrl(b, cmd, num, ptr)
  case cmd
  when LibCrypto::CTRL_SET_KTLS
    socket = bio.socket
    is_tx = num != 0
    if is_tx || !socket.read_buffering? || socket.@in_buffer_rem.empty?
      KTLS.enable(socket)
      KTLS.start(socket, ptr, is_tx) ? 1 : 0
    else
      0
    end
  end
end
''',
        },
    )

    assert result["finding_count"] == 0
