from __future__ import annotations

from pathlib import Path

from main_review.static_transfer_10_replacement_review import (
    run_static_transfer_10_replacement_review,
)


EVENT_ROOT = "persisted-event-graph-never-links-causal-edges"
CHECKOUT_ROOT = "retryable-checkout-creation-without-stable-provider-idempotency-key"
VARIANT_ROOT = "variant-gated-schema-cell-persists-on-incompatible-row-kind"


def _roots(result: dict) -> set[str]:
    return {str(item.get("root_cause")) for item in result.get("findings", [])}


def test_persisted_episode_events_without_links_are_reported(tmp_path: Path) -> None:
    source = tmp_path / "extract_episode.py"
    source.write_text(
        '''
def events(rows):
    out = []
    for i, row in enumerate(rows, 1):
        out.append({"id": f"e{i:03d}", "content": row, "caused_by": [], "leads_to": []})
        out.append({"id": f"e{i+1:03d}", "content": row, "caused_by": [], "leads_to": []})
    episode = {"events": out}
    Path("episode.json").write_text(json.dumps(episode))
''',
        encoding="utf-8",
    )
    assert EVENT_ROOT in _roots(
        run_static_transfer_10_replacement_review(tmp_path, ["extract_episode.py"])
    )


def test_final_event_linking_pass_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "extract_episode.py"
    source.write_text(
        '''
def link_events(events):
    for index, event in enumerate(events):
        event["caused_by"] = [events[index - 1]["id"]] if index else []
        event["leads_to"] = [events[index + 1]["id"]] if index + 1 < len(events) else []

def build(rows):
    events = []
    for i, row in enumerate(rows, 1):
        events.append({"id": f"e{i:03d}", "content": row, "caused_by": [], "leads_to": []})
        events.append({"id": f"e{i+1:03d}", "content": row, "caused_by": [], "leads_to": []})
    link_events(events)
    episode = {"events": events}
    Path("episode.json").write_text(json.dumps(episode))
''',
        encoding="utf-8",
    )
    assert EVENT_ROOT not in _roots(
        run_static_transfer_10_replacement_review(tmp_path, ["extract_episode.py"])
    )


def test_retryable_checkout_without_provider_key_is_reported(tmp_path: Path) -> None:
    service = tmp_path / "billing.service.ts"
    provider = tmp_path / "stripe.provider.ts"
    interface = tmp_path / "billing-provider.interface.ts"
    service.write_text(
        '''
async createCheckoutSession(userId: string) {
  try {
    return await provider.createCheckout({ userId, productId: "pro" });
  } catch (error) {
    await db.subscription.update({ data: { checkoutPendingAt: null } });
    throw error;
  }
}
''',
        encoding="utf-8",
    )
    provider.write_text(
        '''
async createCheckout(params: CheckoutParams) {
  return this.client().checkout.sessions.create({
    customer: params.customerId,
    line_items: [{ price: params.productId, quantity: 1 }],
  });
}
''',
        encoding="utf-8",
    )
    interface.write_text(
        '''
interface Provider {
  createCheckout(params: { userId: string; productId: string }): Promise<Result>;
}
''',
        encoding="utf-8",
    )
    assert CHECKOUT_ROOT in _roots(
        run_static_transfer_10_replacement_review(
            tmp_path,
            ["billing.service.ts", "stripe.provider.ts", "billing-provider.interface.ts"],
        )
    )


def test_persisted_attempt_and_provider_idempotency_key_are_clean(tmp_path: Path) -> None:
    service = tmp_path / "billing.service.ts"
    provider = tmp_path / "stripe.provider.ts"
    interface = tmp_path / "billing-provider.interface.ts"
    service.write_text(
        '''
async createCheckoutSession(userId: string) {
  const attempt = await persistCheckoutAttempt(userId);
  try {
    return await provider.createCheckout({ userId, productId: "pro", attempt });
  } catch (error) {
    await db.subscription.update({ data: { checkoutPendingAt: null } });
    throw error;
  }
}
''',
        encoding="utf-8",
    )
    provider.write_text(
        '''
async createCheckout(params: CheckoutParams) {
  return this.client().checkout.sessions.create(
    { customer: params.customerId, line_items: [{ price: params.productId, quantity: 1 }] },
    { idempotencyKey: params.attempt.key },
  );
}
''',
        encoding="utf-8",
    )
    interface.write_text(
        '''
interface CheckoutAttempt { key: string; startedAt: Date }
interface Provider {
  createCheckout(params: { userId: string; productId: string; attempt: CheckoutAttempt }): Promise<Result>;
}
''',
        encoding="utf-8",
    )
    assert CHECKOUT_ROOT not in _roots(
        run_static_transfer_10_replacement_review(
            tmp_path,
            ["billing.service.ts", "stripe.provider.ts", "billing-provider.interface.ts"],
        )
    )


def test_variant_only_field_without_save_pruning_is_reported(tmp_path: Path) -> None:
    normalize = tmp_path / "normalize.php"
    resolver = tmp_path / "content_block.php"
    normalize.write_text(
        '''<?php
function normalize( array &$node ): bool {
  if ( ef_prune_default_content_block_cells( $node['content-block-row'] ) ) return true;
  return false;
}
function ef_prune_default_content_block_cells( array &$rows ): bool {
  $records = Contract::records_for( 'row', 'content-block-row' );
  foreach ( $rows['value'] as &$row ) { /* default-only pruning */ }
  return false;
}
''',
        encoding="utf-8",
    )
    resolver.write_text(
        '''<?php
switch ( $kind ) {
  case 'tag': return $this->tag_context( $row );
  case 'media':
    $position = Media_Position::desktop_position( $row['position'] ?? '' );
    return [ 'kind' => 'media', 'position' => $position ];
}
''',
        encoding="utf-8",
    )
    assert VARIANT_ROOT in _roots(
        run_static_transfer_10_replacement_review(tmp_path, ["normalize.php"])
    )


def test_kind_aware_variant_pruning_is_clean(tmp_path: Path) -> None:
    normalize = tmp_path / "normalize.php"
    resolver = tmp_path / "content_block.php"
    normalize.write_text(
        '''<?php
function normalize( array &$node ): bool {
  ef_prune_default_content_block_cells( $node['content-block-row'] );
  ef_prune_media_only_position( $node['content-block-row'] );
  return true;
}
function ef_prune_media_only_position( array &$rows ): bool {
  foreach ( $rows['value'] as &$row ) {
    $kind = $row['value']['kind']['value'] ?? null;
    if ( is_string( $kind ) && 'media' !== $kind ) unset( $row['value']['position'] );
  }
  return true;
}
''',
        encoding="utf-8",
    )
    resolver.write_text(
        '''<?php
switch ( $kind ) {
  case 'media':
    $position = Media_Position::desktop_position( $row['position'] ?? '' );
    return [ 'kind' => 'media', 'position' => $position ];
}
''',
        encoding="utf-8",
    )
    assert VARIANT_ROOT not in _roots(
        run_static_transfer_10_replacement_review(tmp_path, ["normalize.php"])
    )


def test_variant_rule_requires_repository_ownership_evidence(tmp_path: Path) -> None:
    normalize = tmp_path / "normalize.php"
    normalize.write_text(
        '''<?php
function normalize( array &$node ): bool {
  return ef_prune_default_content_block_cells( $node['content-block-row'] );
}
function ef_prune_default_content_block_cells( array &$rows ): bool {
  $records = Contract::records_for( 'row', 'content-block-row' );
  return false;
}
''',
        encoding="utf-8",
    )
    assert VARIANT_ROOT not in _roots(
        run_static_transfer_10_replacement_review(tmp_path, ["normalize.php"])
    )
