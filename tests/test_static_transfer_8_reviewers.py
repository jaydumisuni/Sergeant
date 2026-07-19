from __future__ import annotations

from pathlib import Path

from main_review.static_persistent_queue_review import run_static_persistent_queue_review
from main_review.static_untrusted_git_review import run_static_untrusted_git_review
from main_review.static_webhook_delivery_review import run_static_webhook_delivery_review


GIT_ROOT = "untrusted-git-submodule-init-without-transport-hardening"
QUEUE_ROOT = "persistent-collection-read-modify-write-without-serialization"
DEADLETTER_ROOT = "exhausted-retry-is-erased-without-durable-dead-letter"
ACK_ROOT = "webhook-side-effect-failure-acknowledged-as-success"
MONEY_ROOT = "webhook-money-credit-is-nonatomic-and-nonidempotent"


def _roots(result: dict) -> set[str]:
    return {str(item.get("root_cause")) for item in result.get("findings", [])}


def test_untrusted_worktree_submodule_init_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "submodule.go"
    source.write_text(
        '''
package worktree
// A review worktree contains the pull request HEAD and its .gitmodules.
func (m *Manager) initSubmodules(ctx context.Context, dir string) {
    cmd := exec.CommandContext(ctx, "git", "submodule", "update", "--init", "--recursive")
    cmd.Dir = dir
}
''',
        encoding="utf-8",
    )
    assert GIT_ROOT in _roots(run_static_untrusted_git_review(tmp_path, ["submodule.go"]))


def test_hardened_submodule_sink_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "submodule.go"
    source.write_text(
        '''
package worktree
var hardened = []string{
  "protocol.allow=never",
  "protocol.https.allow=always",
  "protocol.ssh.allow=always",
  "protocol.ext.allow=never",
  "core.hooksPath=/dev/null",
}
func (m *Manager) initSubmodules(ctx context.Context, dir string) {
    // review worktree / .gitmodules boundary
    cmd := m.newNonInteractiveGitCmd(ctx, dir, "-c", hardened[0], "submodule", "update", "--init", "--recursive")
    cmd.Env = append(cmd.Env, "GIT_TERMINAL_PROMPT=0")
}
''',
        encoding="utf-8",
    )
    assert GIT_ROOT not in _roots(run_static_untrusted_git_review(tmp_path, ["submodule.go"]))


def test_persistent_queue_whole_array_replacement_and_erasure_are_reported(tmp_path: Path) -> None:
    source = tmp_path / "queue.ts"
    source.write_text(
        '''
export class UploadQueue {
  constructor(private store: KeyValueStore) {}
  private async load(): Promise<Item[]> { return (await this.store.get<Item[]>(KEY_QUEUE)) ?? []; }
  private async save(items: Item[]): Promise<void> { await this.store.set(KEY_QUEUE, items); }
  async enqueue(item: Item) {
    const items = await this.load();
    items.push(item);
    await this.save(items);
  }
  async flush(upload: Uploader) {
    const items = await this.load();
    const remaining: Item[] = [];
    for (const item of items) {
      const attempts = item.attempts + 1;
      if (attempts >= MAX_ATTEMPTS) {
        res.dropped++;
      } else {
        remaining.push({ ...item, attempts });
      }
    }
    await this.save(remaining);
  }
}
''',
        encoding="utf-8",
    )
    roots = _roots(run_static_persistent_queue_review(tmp_path, ["queue.ts"]))
    assert QUEUE_ROOT in roots
    assert DEADLETTER_ROOT in roots


def test_serialized_queue_with_durable_deadletter_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "queue.ts"
    source.write_text(
        '''
export class UploadQueue {
  private chain = Promise.resolve();
  constructor(private store: KeyValueStore) {}
  private async load(): Promise<Item[]> { return (await this.store.get<Item[]>(KEY_QUEUE)) ?? []; }
  private async save(items: Item[]): Promise<void> { await this.store.set(KEY_QUEUE, items); }
  async enqueue(item: Item) {
    return this.chain = this.chain.then(async () => {
      const items = await this.load(); items.push(item); await this.save(items);
    });
  }
  async flush(upload: Uploader) {
    return this.chain = this.chain.then(async () => {
      const items = await this.load(); const remaining: Item[] = [];
      for (const item of items) {
        const attempts = item.attempts + 1;
        if (attempts >= MAX_ATTEMPTS) {
          const deadLetter = (await this.store.get<Item[]>(KEY_DEADLETTER)) ?? [];
          deadLetter.push({ ...item, failureReason: "max_attempts_exhausted" });
          await this.store.set(KEY_DEADLETTER, deadLetter);
        } else { remaining.push(item); }
      }
      await this.save(remaining);
    });
  }
}
''',
        encoding="utf-8",
    )
    roots = _roots(run_static_persistent_queue_review(tmp_path, ["queue.ts"]))
    assert QUEUE_ROOT not in roots
    assert DEADLETTER_ROOT not in roots


def test_webhook_swallowed_side_effect_and_nonatomic_credit_are_reported(tmp_path: Path) -> None:
    source = tmp_path / "webhook.ts"
    source.write_text(
        '''
async function creditCoinPack(coinAmount: number, sessionId: string) {
  try {
    const { data: wallet } = await sb.from("wallets").select("balance").single();
    const currentBalance = wallet?.balance || 0;
    const newBalance = currentBalance + coinAmount;
    await sb.from("wallets").update({ balance: newBalance });
    await sb.from("transactions").insert({ type: "purchase", metadata: { stripe_session_id: sessionId } });
  } catch (err) {
    console.error("credit failed", err);
  }
}
export async function POST(req: NextRequest) {
  try {
    const event = verifyWebhook(await req.text());
    await creditCoinPack(10, event.id);
  } catch (err) {
    console.error("webhook processing failed", err);
  }
  return NextResponse.json({ received: true });
}
''',
        encoding="utf-8",
    )
    roots = _roots(run_static_webhook_delivery_review(tmp_path, ["webhook.ts"]))
    assert ACK_ROOT in roots
    assert MONEY_ROOT in roots


def test_safe_signature_catch_does_not_hide_later_swallowed_processing_catch(tmp_path: Path) -> None:
    source = tmp_path / "webhook.ts"
    source.write_text(
        '''
export async function POST(req: NextRequest) {
  let event;
  try { event = verifyWebhook(await req.text()); }
  catch (err) { return NextResponse.json({ error: "bad signature" }, { status: 400 }); }
  try { await sb.from("subscriptions").upsert({ id: event.id }); }
  catch (err) { console.error("processing failed", err); }
  return NextResponse.json({ received: true });
}
''',
        encoding="utf-8",
    )
    assert ACK_ROOT in _roots(run_static_webhook_delivery_review(tmp_path, ["webhook.ts"]))


def test_webhook_non_success_and_atomic_idempotent_credit_are_clean(tmp_path: Path) -> None:
    source = tmp_path / "webhook.ts"
    source.write_text(
        '''
async function creditCoinPack(userId: string, amount: number, sessionId: string) {
  const { error } = await sb.rpc("credit_coin_pack", {
    p_user_id: userId, p_coin_amount: amount, p_stripe_session_id: sessionId,
  });
  if (error) throw error;
}
export async function POST(req: NextRequest) {
  try {
    const event = verifyWebhook(await req.text());
    await creditCoinPack(event.userId, event.amount, event.id); // idempotent unique provider event
    return NextResponse.json({ received: true });
  } catch (err) {
    return NextResponse.json({ error: "retry" }, { status: 500 });
  }
}
''',
        encoding="utf-8",
    )
    roots = _roots(run_static_webhook_delivery_review(tmp_path, ["webhook.ts"]))
    assert ACK_ROOT not in roots
    assert MONEY_ROOT not in roots


def test_non_webhook_wallet_update_is_out_of_scope(tmp_path: Path) -> None:
    source = tmp_path / "wallet.ts"
    source.write_text(
        '''
export async function renameWallet(id: string, label: string) {
  await sb.from("wallets").update({ label }).eq("id", id);
}
''',
        encoding="utf-8",
    )
    assert run_static_webhook_delivery_review(tmp_path, ["wallet.ts"])["finding_count"] == 0
