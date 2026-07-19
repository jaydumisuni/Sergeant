from __future__ import annotations

from pathlib import Path

from main_review.static_external_integrity_review import run_static_external_integrity_review
from main_review.static_status_review import run_static_status_review


GIT_ROOT = "untrusted-git-submodule-exec-without-protocol-hardening"
QUEUE_ROOT = "persistent-queue-read-modify-write-without-serialization"
DEAD_ROOT = "retry-exhaustion-removes-item-without-durable-dead-letter"
ACK_ROOT = "webhook-side-effect-failure-acknowledged-successfully"
CREDIT_ROOT = "payment-credit-read-modify-write-without-atomic-idempotency"


def _roots(result: dict) -> set[str]:
    return {str(item.get("root_cause")) for item in result.get("findings", [])}


def test_untrusted_worktree_submodule_init_without_hardening_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "internal" / "worktree" / "submodule.go"
    source.parent.mkdir(parents=True)
    source.write_text(
        """
package worktree

import (
    "context"
    "os/exec"
)

func (m *Manager) initSubmodules(ctx context.Context, dir string) {
    cmd := exec.CommandContext(ctx, "git", "submodule", "update", "--init", "--recursive")
    cmd.Dir = dir
    _ = cmd.Run()
}
        """,
        encoding="utf-8",
    )

    result = run_static_external_integrity_review(tmp_path, ["internal/worktree/submodule.go"])

    assert GIT_ROOT in _roots(result)


def test_hardened_noninteractive_submodule_helper_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "internal" / "worktree" / "submodule.go"
    source.parent.mkdir(parents=True)
    source.write_text(
        """
package worktree

import "context"

var hardenedSubmoduleConfig = []string{
    "protocol.allow=never",
    "protocol.https.allow=always",
    "protocol.ssh.allow=always",
    "protocol.ext.allow=never",
    "core.hooksPath=/dev/null",
}

func (m *Manager) newSubmoduleUpdateCmd(ctx context.Context, dir string) *Cmd {
    args := []string{}
    for _, value := range hardenedSubmoduleConfig {
        args = append(args, "-c", value)
    }
    args = append(args, "submodule", "update", "--init", "--recursive")
    return m.newNonInteractiveGitCmd(ctx, dir, args...)
}

func (m *Manager) initSubmodules(ctx context.Context, dir string) {
    cmd := m.newSubmoduleUpdateCmd(ctx, dir)
    _ = cmd.Run()
}
        """,
        encoding="utf-8",
    )

    result = run_static_external_integrity_review(tmp_path, ["internal/worktree/submodule.go"])

    assert GIT_ROOT not in _roots(result)


def test_trusted_vendor_submodule_command_without_review_context_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "tools" / "vendor.go"
    source.parent.mkdir(parents=True)
    source.write_text(
        """
package tools

import (
    "context"
    "os/exec"
)

func updateBundledDependencies(ctx context.Context, dir string) {
    cmd := exec.CommandContext(ctx, "git", "submodule", "update", "--init", "--recursive")
    cmd.Dir = dir
    _ = cmd.Run()
}
        """,
        encoding="utf-8",
    )

    result = run_static_external_integrity_review(tmp_path, ["tools/vendor.go"])

    assert GIT_ROOT not in _roots(result)


def test_persisted_queue_rmw_and_retry_erasure_are_reported(tmp_path: Path) -> None:
    source = tmp_path / "queue.ts"
    source.write_text(
        """
import { KEY_QUEUE, MAX_ATTEMPTS } from "./constants";

class UploadQueue {
  constructor(private store: KeyValueStore) {}

  private async load(): Promise<QueuedItem[]> {
    return (await this.store.get<QueuedItem[]>(KEY_QUEUE)) ?? [];
  }

  private async save(items: QueuedItem[]): Promise<void> {
    await this.store.set(KEY_QUEUE, items);
  }

  async enqueue(capture: CaptureUpload) {
    const items = await this.load();
    items.push({ capture, attempts: 0 });
    await this.save(items);
  }

  async flush(upload: Uploader) {
    const items = await this.load();
    const remaining: QueuedItem[] = [];
    for (const item of items) {
      const outcome = await upload(item.capture);
      if (outcome === "retry") {
        const attempts = item.attempts + 1;
        if (attempts >= MAX_ATTEMPTS) {
          result.dropped++;
        } else {
          remaining.push({ ...item, attempts });
        }
      }
    }
    await this.save(remaining);
  }
}
        """,
        encoding="utf-8",
    )

    result = run_static_external_integrity_review(tmp_path, ["queue.ts"])
    roots = _roots(result)

    assert QUEUE_ROOT in roots
    assert DEAD_ROOT in roots


def test_serialized_queue_with_durable_dead_letter_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "queue.ts"
    source.write_text(
        """
import { KEY_DEADLETTER, KEY_QUEUE, MAX_ATTEMPTS } from "./constants";

class UploadQueue {
  private mutationTail: Promise<void> = Promise.resolve();

  constructor(private store: KeyValueStore) {}

  private mutate<T>(operation: () => Promise<T>): Promise<T> {
    const next = this.mutationTail.then(operation, operation);
    this.mutationTail = next.then(() => undefined, () => undefined);
    return next;
  }

  private async load(): Promise<QueuedItem[]> {
    return (await this.store.get<QueuedItem[]>(KEY_QUEUE)) ?? [];
  }

  private async save(items: QueuedItem[]): Promise<void> {
    await this.store.set(KEY_QUEUE, items);
  }

  private async moveToDeadLetter(item: QueuedItem): Promise<void> {
    const deadLetter = (await this.store.get<QueuedItem[]>(KEY_DEADLETTER)) ?? [];
    deadLetter.push(item);
    await this.store.set(KEY_DEADLETTER, deadLetter);
  }

  async enqueue(capture: CaptureUpload) {
    return this.mutate(async () => {
      const items = await this.load();
      items.push({ capture, attempts: 0 });
      await this.save(items);
    });
  }

  async flush(upload: Uploader) {
    return this.mutate(async () => {
      const items = await this.load();
      const remaining: QueuedItem[] = [];
      for (const item of items) {
        const outcome = await upload(item.capture);
        if (outcome === "retry") {
          const attempts = item.attempts + 1;
          if (attempts >= MAX_ATTEMPTS) {
            await this.moveToDeadLetter({ ...item, attempts });
          } else {
            remaining.push({ ...item, attempts });
          }
        }
      }
      await this.save(remaining);
    });
  }
}
        """,
        encoding="utf-8",
    )

    result = run_static_external_integrity_review(tmp_path, ["queue.ts"])
    roots = _roots(result)

    assert QUEUE_ROOT not in roots
    assert DEAD_ROOT not in roots


def test_payment_webhook_success_ack_and_non_atomic_credit_are_reported(tmp_path: Path) -> None:
    source = tmp_path / "stripe" / "webhook" / "route.ts"
    source.parent.mkdir(parents=True)
    source.write_text(
        """
async function creditCoinPack(clerkId: string, coinAmount: number, sessionId: string) {
  const sb = getAdminSupabase();
  try {
    const { data: wallet } = await sb
      .from("wallets")
      .select("balance")
      .eq("user_id", clerkId)
      .single();
    const currentBalance = wallet?.balance || 0;
    const newBalance = currentBalance + coinAmount;
    await sb.from("wallets").update({ balance: newBalance }).eq("user_id", clerkId);
    await sb.from("transactions").insert({
      type: "purchase",
      amount: coinAmount,
      metadata: { stripe_session_id: sessionId },
    });
  } catch (error) {
    console.error(error);
  }
}

export async function POST(req: NextRequest) {
  const event = await stripe.webhooks.constructEvent(await req.text());
  try {
    if (event.type === "checkout.session.completed") {
      await creditCoinPack("user", 100, event.data.object.id);
    }
  } catch (error) {
    console.error(error);
  }
  return NextResponse.json({ received: true });
}
        """,
        encoding="utf-8",
    )

    result = run_static_external_integrity_review(tmp_path, ["stripe/webhook/route.ts"])
    roots = _roots(result)

    assert ACK_ROOT in roots
    assert CREDIT_ROOT in roots


def test_retryable_webhook_ack_with_atomic_credit_rpc_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "stripe" / "webhook" / "route.ts"
    source.parent.mkdir(parents=True)
    source.write_text(
        """
async function creditCoinPack(userId: string, coinAmount: number, sessionId: string) {
  const sb = getAdminSupabase();
  const { error } = await sb.rpc("credit_coin_pack", {
    p_user_id: userId,
    p_coin_amount: coinAmount,
    p_stripe_session_id: sessionId,
  });
  if (error) throw error;
}

export async function POST(req: NextRequest) {
  const event = await stripe.webhooks.constructEvent(await req.text());
  try {
    if (event.type === "checkout.session.completed") {
      await creditCoinPack("user", 100, event.data.object.id);
    }
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
  return NextResponse.json({ received: true });
}
        """,
        encoding="utf-8",
    )

    result = run_static_external_integrity_review(tmp_path, ["stripe/webhook/route.ts"])
    roots = _roots(result)

    assert ACK_ROOT not in roots
    assert CREDIT_ROOT not in roots


def test_non_payment_best_effort_webhook_ack_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "analytics" / "webhook" / "route.ts"
    source.parent.mkdir(parents=True)
    source.write_text(
        """
export async function POST(req: NextRequest) {
  try {
    await analytics.record(await req.json());
  } catch (error) {
    console.error(error);
  }
  return NextResponse.json({ received: true });
}
        """,
        encoding="utf-8",
    )

    result = run_static_external_integrity_review(tmp_path, ["analytics/webhook/route.ts"])

    assert not _roots(result)


def test_status_bundle_exposes_all_external_integrity_roots(tmp_path: Path) -> None:
    git_source = tmp_path / "internal" / "worktree" / "submodule.go"
    git_source.parent.mkdir(parents=True)
    git_source.write_text(
        """
package worktree
import ("context"; "os/exec")
func initSubmodules(ctx context.Context, dir string) {
    cmd := exec.CommandContext(ctx, "git", "submodule", "update", "--init", "--recursive")
    cmd.Dir = dir
}
        """,
        encoding="utf-8",
    )
    queue_source = tmp_path / "queue.ts"
    queue_source.write_text(
        """
class UploadQueue {
  async load() { return (await this.store.get(KEY_QUEUE)) ?? []; }
  async save(items) { await this.store.set(KEY_QUEUE, items); }
  async enqueue(item) { const items = await this.load(); items.push(item); await this.save(items); }
  async flush(upload) {
    const items = await this.load();
    const remaining = [];
    for (const item of items) {
      const attempts = item.attempts + 1;
      if (attempts >= MAX_ATTEMPTS) { result.dropped++; }
      else { remaining.push(item); }
    }
    await this.save(remaining);
  }
}
        """,
        encoding="utf-8",
    )
    webhook_source = tmp_path / "stripe" / "webhook" / "route.ts"
    webhook_source.parent.mkdir(parents=True)
    webhook_source.write_text(
        """
async function credit(sessionId, amount) {
  const { data: wallet } = await sb.from("wallets").select("balance").single();
  const newBalance = wallet.balance + amount;
  await sb.from("wallets").update({ balance: newBalance });
  await sb.from("transactions").insert({ metadata: { stripe_session_id: sessionId } });
}
export async function POST() {
  try { await credit("evt", 1); }
  catch (error) { console.error(error); }
  return NextResponse.json({ received: true });
}
        """,
        encoding="utf-8",
    )

    result = run_static_status_review(
        tmp_path,
        [
            "internal/worktree/submodule.go",
            "queue.ts",
            "stripe/webhook/route.ts",
        ],
    )
    roots = _roots(result)

    assert GIT_ROOT in roots
    assert QUEUE_ROOT in roots
    assert DEAD_ROOT in roots
    assert ACK_ROOT in roots
    assert CREDIT_ROOT in roots
