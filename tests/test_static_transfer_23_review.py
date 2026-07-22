from __future__ import annotations

from pathlib import Path

from main_review.static_status_review import run_static_status_review
from main_review.static_transfer_23_review import run_static_transfer_23_review


AUTH_ROOT = "nested-operation-bypasses-canonical-authorization-helper"
QUERY_ROOT = "query-only-decision-parses-unrelated-full-request-url"
BOOL_ROOT = "protobuf-bool-wrapper-presence-assigned-as-value"


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _roots(result: dict) -> set[str]:
    return {str(item.get("root_cause")) for item in result.get("findings", [])}


def test_nested_put_must_use_canonical_side_effect_authorization(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "apply_auth.go",
        """
package server

func checkPutAuth(as AuthStore, ai *AuthInfo, lessor Lessor, r *PutRequest) error {
    if err := as.IsPutPermitted(ai, r.Key); err != nil { return err }
    if err := checkLeasePuts(as, ai, lessor, r.Lease); err != nil { return err }
    if r.PrevKv {
        if err := as.IsRangePermitted(ai, r.Key, nil); err != nil { return err }
    }
    return nil
}

func checkTxnReqsPermission(as AuthStore, ai *AuthInfo, reqs []*RequestOp) error {
    for _, req := range reqs {
        switch tv := req.Request.(type) {
        case *RequestOp_RequestPut:
            if tv.RequestPut == nil { continue }
            if err := as.IsPutPermitted(ai, tv.RequestPut.Key); err != nil { return err }
        case *RequestOp_RequestRange:
            if err := as.IsRangePermitted(ai, tv.RequestRange.Key, tv.RequestRange.RangeEnd); err != nil { return err }
        }
    }
    return nil
}
""",
    )

    result = run_static_transfer_23_review(tmp_path, ["apply_auth.go"])

    assert AUTH_ROOT in _roots(result)


def test_nested_put_delegating_to_canonical_authorization_is_clean(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "apply_auth.go",
        """
package server

func checkPutAuth(as AuthStore, ai *AuthInfo, lessor Lessor, r *PutRequest) error {
    if err := as.IsPutPermitted(ai, r.Key); err != nil { return err }
    if err := checkLeasePuts(as, ai, lessor, r.Lease); err != nil { return err }
    if r.PrevKv {
        if err := as.IsRangePermitted(ai, r.Key, nil); err != nil { return err }
    }
    return nil
}

func checkTxnReqsPermission(as AuthStore, ai *AuthInfo, lessor Lessor, reqs []*RequestOp) error {
    for _, req := range reqs {
        switch tv := req.Request.(type) {
        case *RequestOp_RequestPut:
            if tv.RequestPut == nil { continue }
            if err := checkPutAuth(as, ai, lessor, tv.RequestPut); err != nil { return err }
        }
    }
    return nil
}
""",
    )

    result = run_static_transfer_23_review(tmp_path, ["apply_auth.go"])

    assert AUTH_ROOT not in _roots(result)


def test_primary_permission_only_helper_does_not_create_false_parity_rule(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "apply_auth.go",
        """
package server

func checkPutAuth(as AuthStore, ai *AuthInfo, r *PutRequest) error {
    return as.IsPutPermitted(ai, r.Key)
}

func checkTxnReqsPermission(as AuthStore, ai *AuthInfo, reqs []*RequestOp) error {
    for _, req := range reqs {
        switch tv := req.Request.(type) {
        case *RequestOp_RequestPut:
            if err := as.IsPutPermitted(ai, tv.RequestPut.Key); err != nil { return err }
        }
    }
    return nil
}
""",
    )

    result = run_static_transfer_23_review(tmp_path, ["apply_auth.go"])

    assert AUTH_ROOT not in _roots(result)


def test_query_only_match_must_not_parse_full_request_url(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "RequestCache.java",
        """
class RequestCache {
    Request getMatchingRequest(Request request) {
        if (!StringUtils.hasText(request.getQueryString())
                || !UriComponentsBuilder.fromUriString(UrlUtils.buildRequestUrl(request))
                    .build()
                    .getQueryParams()
                    .containsKey(this.matchingRequestParameterName)) {
            return null;
        }
        return request;
    }
}
""",
    )

    result = run_static_transfer_23_review(tmp_path, ["RequestCache.java"])

    assert QUERY_ROOT in _roots(result)


def test_query_component_builder_is_clean(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "RequestCache.java",
        """
class RequestCache {
    Request getMatchingRequest(Request request) {
        if (!StringUtils.hasText(request.getQueryString())
                || !UriComponentsBuilder.newInstance()
                    .query(request.getQueryString())
                    .build()
                    .getQueryParams()
                    .containsKey(this.matchingRequestParameterName)) {
            return null;
        }
        return request;
    }
}
""",
    )

    result = run_static_transfer_23_review(tmp_path, ["RequestCache.java"])

    assert QUERY_ROOT not in _roots(result)


def test_full_url_parse_used_for_path_and_authority_is_clean(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "Redirect.java",
        """
class Redirect {
    boolean isSameOrigin(Request request) {
        UriComponents url = UriComponentsBuilder.fromUriString(UrlUtils.buildRequestUrl(request)).build();
        return url.getHost().equals(this.host) && url.getPath().startsWith(this.prefix);
    }
}
""",
    )

    result = run_static_transfer_23_review(tmp_path, ["Redirect.java"])

    assert QUERY_ROOT not in _roots(result)


def test_generated_bool_wrapper_must_be_unwrapped(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "parser.cc",
        """
#include "google/protobuf/wrappers.upb.h"

Rules ParseRules(const RulesProto* proto) {
  Rules config;
  config.disallow_all = package_v3_Rules_disallow_all(proto);
  config.disallow_is_error = package_v3_Rules_disallow_is_error(proto);
  return config;
}
""",
    )

    result = run_static_transfer_23_review(tmp_path, ["parser.cc"])

    assert BOOL_ROOT in _roots(result)


def test_generated_bool_wrapper_using_canonical_parser_is_clean(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "parser.cc",
        """
#include "google/protobuf/wrappers.upb.h"

Rules ParseRules(const RulesProto* proto) {
  Rules config;
  config.disallow_all = ParseBoolValue(package_v3_Rules_disallow_all(proto));
  config.disallow_is_error = ParseBoolValue(package_v3_Rules_disallow_is_error(proto));
  return config;
}
""",
    )

    result = run_static_transfer_23_review(tmp_path, ["parser.cc"])

    assert BOOL_ROOT not in _roots(result)


def test_ordinary_scalar_bool_accessor_without_wrapper_support_is_clean(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "parser.cc",
        """
Rules ParseRules(const RulesProto* proto) {
  Rules config;
  config.enabled = package_v3_Rules_enabled(proto);
  return config;
}
""",
    )

    result = run_static_transfer_23_review(tmp_path, ["parser.cc"])

    assert BOOL_ROOT not in _roots(result)


def test_normal_static_status_path_admits_transfer_23_root(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "RequestCache.java",
        """
class RequestCache {
    Request getMatchingRequest(Request request) {
        if (!StringUtils.hasText(request.getQueryString())
                || !UriComponentsBuilder.fromUriString(UrlUtils.buildRequestUrl(request))
                    .build().getQueryParams().containsKey(this.parameter)) {
            return null;
        }
        return request;
    }
}
""",
    )

    result = run_static_status_review(tmp_path, ["RequestCache.java"])

    assert QUERY_ROOT in _roots(result)
