from __future__ import annotations

from pathlib import Path

from main_review.static_preawait_durability_review import (
    run_static_preawait_durability_review,
)
from main_review.static_selector_continuity_review import (
    run_static_selector_continuity_review,
)
from main_review.static_status_review import run_static_status_review


SELECTOR_ROOT = "resolved-display-default-not-propagated-to-operation-create"
DURABILITY_ROOT = "routing-state-not-persisted-before-slow-await"


def _roots(result: dict) -> set[str]:
    return {str(item.get("root_cause")) for item in result.get("findings", [])}


def test_displayed_model_lost_before_bridge_create_is_reported(tmp_path: Path) -> None:
    presentation = tmp_path / "tui_app.go"
    presentation.write_text(
        '''
package main

func selectBackend(ctx context.Context, root string, sup *Supervisor) Backend {
    bridge := tuibridge.New(sup)
    return Backend{
        sup: bridge,
        meta: OverviewMeta{Model: resolveOverviewModel(ctx, root)},
    }
}
        ''',
        encoding="utf-8",
    )
    bridge = tmp_path / "bridge.go"
    bridge.write_text(
        '''
package tuibridge

type Adapter struct { sup *supervisor.Supervisor }
func New(sup *supervisor.Supervisor) Adapter { return Adapter{sup: sup} }
func (a Adapter) Create(ctx context.Context, prompt string, opts tui.CreateOptions) error {
    return a.sup.Create(ctx, prompt, supervisor.CreateOptions{Model: opts.Model})
}
        ''',
        encoding="utf-8",
    )

    result = run_static_selector_continuity_review(
        tmp_path,
        ["tui_app.go", "bridge.go"],
    )

    assert SELECTOR_ROOT in _roots(result)


def test_bridge_receiving_and_applying_resolved_model_is_clean(tmp_path: Path) -> None:
    presentation = tmp_path / "tui_app.go"
    presentation.write_text(
        '''
package main

func selectBackend(ctx context.Context, root string, sup *Supervisor) Backend {
    model := resolveOverviewModel(ctx, root)
    bridge := tuibridge.New(sup, model)
    return Backend{sup: bridge, meta: OverviewMeta{Model: model}}
}
        ''',
        encoding="utf-8",
    )
    bridge = tmp_path / "bridge.go"
    bridge.write_text(
        '''
package tuibridge

type Adapter struct { sup *supervisor.Supervisor; defaultModel string }
func New(sup *supervisor.Supervisor, model string) Adapter {
    return Adapter{sup: sup, defaultModel: model}
}
func (a Adapter) Create(ctx context.Context, prompt string, opts tui.CreateOptions) error {
    if opts.Model == "" { opts.Model = a.defaultModel }
    return a.sup.Create(ctx, prompt, supervisor.CreateOptions{Model: opts.Model})
}
        ''',
        encoding="utf-8",
    )

    result = run_static_selector_continuity_review(
        tmp_path,
        ["tui_app.go", "bridge.go"],
    )

    assert SELECTOR_ROOT not in _roots(result)


def test_unrelated_display_metadata_without_bridge_create_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "overview.go"
    source.write_text(
        '''
package overview

func meta(ctx context.Context, root string) OverviewMeta {
    return OverviewMeta{Model: resolveOverviewModel(ctx, root)}
}
        ''',
        encoding="utf-8",
    )

    result = run_static_selector_continuity_review(tmp_path, ["overview.go"])

    assert not result["findings"]


def test_routing_state_saved_only_after_slow_await_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "engine.py"
    source.write_text(
        '''
class Engine:
    async def process(self, chat_id, state, photo):
        if state["kind"] == "print":
            state["state"] = "ELECTRICAL_PRINT"
            reply = await self._grounded_print_reply(photo)
            state["context"]["reply"] = reply
            self._save_state(chat_id, state)
            return reply
        ''',
        encoding="utf-8",
    )

    result = run_static_preawait_durability_review(tmp_path, ["engine.py"])

    assert DURABILITY_ROOT in _roots(result)


def test_routing_state_saved_before_slow_await_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "engine.py"
    source.write_text(
        '''
class Engine:
    async def process(self, chat_id, state, photo):
        if state["kind"] == "print":
            state["state"] = "ELECTRICAL_PRINT"
            self._save_state(chat_id, state)
            reply = await self._grounded_print_reply(photo)
            return reply
        ''',
        encoding="utf-8",
    )

    result = run_static_preawait_durability_review(tmp_path, ["engine.py"])

    assert DURABILITY_ROOT not in _roots(result)


def test_transient_state_with_no_later_durable_save_is_not_misclassified(tmp_path: Path) -> None:
    source = tmp_path / "engine.py"
    source.write_text(
        '''
class Engine:
    async def preview(self, state, photo):
        state["state"] = "PREVIEW_ONLY"
        return await self._generate_preview(photo)
        ''',
        encoding="utf-8",
    )

    result = run_static_preawait_durability_review(tmp_path, ["engine.py"])

    assert DURABILITY_ROOT not in _roots(result)


def test_status_bundle_exposes_both_companion_roots(tmp_path: Path) -> None:
    presentation = tmp_path / "tui_app.go"
    presentation.write_text(
        '''
package main
func build(ctx context.Context, root string, sup *Supervisor) Backend {
    b := tuibridge.New(sup)
    return Backend{sup: b, meta: OverviewMeta{Model: resolveOverviewModel(ctx, root)}}
}
        ''',
        encoding="utf-8",
    )
    bridge = tmp_path / "bridge.go"
    bridge.write_text(
        '''
package tuibridge
type Adapter struct { sup *Supervisor }
func New(sup *Supervisor) Adapter { return Adapter{sup: sup} }
func (a Adapter) Create(ctx context.Context, prompt string, opts CreateOptions) error {
    return a.sup.Create(ctx, prompt, RuntimeCreateOptions{Model: opts.Model})
}
        ''',
        encoding="utf-8",
    )
    engine = tmp_path / "engine.py"
    engine.write_text(
        '''
class Engine:
    async def process(self, chat_id, state, photo):
        if state["kind"] == "print":
            state["state"] = "PRINT"
            reply = await self._interpret_print(photo)
            self._save_state(chat_id, state)
            return reply
        ''',
        encoding="utf-8",
    )

    result = run_static_status_review(
        tmp_path,
        ["tui_app.go", "bridge.go", "engine.py"],
    )

    assert {SELECTOR_ROOT, DURABILITY_ROOT}.issubset(_roots(result))
    assert result["static_selector_continuity_review"]["finding_count"] == 1
    assert result["static_preawait_durability_review"]["finding_count"] == 1
