from __future__ import annotations

from pathlib import Path

from main_review.static_transfer_28_review import run_static_transfer_28_review


def _run(tmp_path: Path, relative: str, source: str):
    target = tmp_path / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")
    return run_static_transfer_28_review(tmp_path, [relative])


def _roots(result: dict) -> set[str]:
    return {str(item["root_cause"]) for item in result["findings"]}


def test_keyword_diagnostic_anchored_to_enclosing_node_is_actionable(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        "lib/AstGen.zig",
        '''
fn comptimeExprAst(gz: *GenZir, node: Ast.Node.Index) !void {
    const astgen = gz.astgen;
    if (gz.is_comptime) {
        try astgen.appendErrorNode(node, "redundant comptime keyword in already comptime scope", .{});
    }
}
''',
    )

    assert "keyword-diagnostic-owned-by-enclosing-node-not-token" in _roots(result)


def test_token_anchored_keyword_diagnostic_is_clean(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        "lib/AstGen.zig",
        '''
fn comptimeExprAst(gz: *GenZir, node: Ast.Node.Index) !void {
    const astgen = gz.astgen;
    const tree = astgen.tree;
    if (gz.is_comptime) {
        try astgen.appendErrorTok(tree.nodeMainToken(node), "redundant comptime keyword in already comptime scope", .{});
    }
}
''',
    )

    assert result["finding_count"] == 0


def test_zero_expression_results_cannot_define_group_cardinality(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        "R/summarise.R",
        '''
summarise_cols <- function(data, dots, by, verb, error_call = caller_env()) {
  mask <- DataMask$new(data, by, verb)
  chunks <- list()
  results <- list()
  for (i in seq_along(dots)) {
    chunks <- append(chunks, list(dots[[i]]))
  }
  if (verb == "summarise") {
    sizes <- NULL
  } else {
    sizes <- .Call(
      `dplyr_reframe_recycle_horizontally_in_place`,
      chunks,
      results
    )
  }
  list(new = list(), sizes = sizes)
}

summarise_build <- function(by, cols) {
  out <- group_keys0(by$data)
  if (!is_null(cols$sizes)) {
    out <- vec_rep_each(out, cols$sizes)
  }
  out
}
''',
    )

    assert "empty-expression-results-used-as-authority-for-nonempty-group-cardinality" in _roots(result)


def test_independent_group_count_preserves_zero_expression_path(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        "R/summarise.R",
        '''
summarise_cols <- function(data, dots, by, verb, error_call = caller_env()) {
  mask <- DataMask$new(data, by, verb)
  n_groups <- mask$get_n_groups()
  chunks <- list()
  results <- list()
  for (i in seq_along(dots)) {
    chunks <- append(chunks, list(dots[[i]]))
  }
  if (verb == "summarise") {
    group_sizes <- NULL
  } else {
    group_sizes <- .Call(
      `dplyr_reframe_recycle_horizontally_in_place`,
      chunks,
      results,
      n_groups
    )
  }
  list(new = list(), group_sizes = group_sizes)
}

summarise_build <- function(by, cols) {
  out <- group_keys0(by$data)
  if (!is_null(cols$group_sizes)) {
    out <- vec_rep_each(out, cols$group_sizes)
  }
  out
}
''',
    )

    assert result["finding_count"] == 0


def test_nested_group_identity_cannot_be_discarded_before_skip_delegation(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        "lib/cth_surefire.erl",
        '''
pre_init_per_group(_Suite,Group,Config,State) ->
    {Config, init_tc(State#state{ curr_group = [Group|State#state.curr_group]}, Config)}.
post_end_per_group(_Suite,_Group,Config,Result,State) ->
    NewState = end_tc(end_per_group, Config, Result, State),
    {Result, NewState#state{ curr_group = tl(NewState#state.curr_group)}}.
on_tc_skip(Suite,{ConfigFunc,_GrName}, Res, State) ->
    on_tc_skip(Suite,ConfigFunc, Res, State);
on_tc_skip(_Suite,_Tc, _Res, State) ->
    State.
''',
    )

    assert "nested-group-callback-discards-group-identity-before-stack-transition" in _roots(result)


def test_nested_group_identity_is_clean_when_state_is_updated_symmetrically(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        "lib/cth_surefire.erl",
        '''
pre_init_per_group(_Suite,Group,Config,State) ->
    {Config, init_tc(State#state{ curr_group = [Group|State#state.curr_group]}, Config)}.
post_end_per_group(_Suite,_Group,Config,Result,State) ->
    NewState = end_tc(end_per_group, Config, Result, State),
    {Result, NewState#state{ curr_group = tl(NewState#state.curr_group)}}.
on_tc_skip(Suite,{init_per_group,GrName}, Res, State) ->
    on_tc_skip(Suite,init_per_group, Res,
               State#state{ curr_group = [GrName|State#state.curr_group]});
on_tc_skip(Suite,{end_per_group,_GrName}, Res, State) ->
    NewState = on_tc_skip(Suite,end_per_group, Res, State),
    NewState#state{ curr_group = tl(NewState#state.curr_group)};
on_tc_skip(_Suite,_Tc, _Res, State) ->
    State.
''',
    )

    assert result["finding_count"] == 0
