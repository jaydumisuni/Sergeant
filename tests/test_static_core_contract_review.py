from __future__ import annotations

from pathlib import Path

from main_review.static_core_contract_review import run_static_core_contract_review


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _roots(result: dict) -> set[str]:
    return {str(item["root_cause"]) for item in result["findings"]}


def test_detects_sliced_rust_shutdown_without_durable_intent(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/macos.rs",
        """
use std::thread;
struct HookInner { thread: thread::JoinHandle<()>, run_loop: RunLoop }
fn thread_main() {
    loop {
        RunLoop::run_in_mode(Mode::Default, std::time::Duration::from_millis(500), false);
        refresh_permission();
    }
}
pub(crate) fn stop(inner: HookInner) {
    inner.run_loop.stop();
    inner.thread.join().unwrap();
}
""",
    )
    result = run_static_core_contract_review(tmp_path, ["src/macos.rs"])
    assert "sliced-loop-shutdown-without-durable-intent" in _roots(result)


def test_accepts_sliced_rust_shutdown_with_durable_flag(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "src/macos.rs",
        """
use std::sync::atomic::{AtomicBool, Ordering};
struct HookInner { stop: AtomicBool, thread: JoinHandle<()>, run_loop: RunLoop }
fn thread_main(stop: &AtomicBool) {
    loop {
        if stop.load(Ordering::Relaxed) { break; }
        RunLoop::run_in_mode(Mode::Default, std::time::Duration::from_millis(500), false);
    }
}
fn stop(inner: HookInner) {
    inner.stop.store(true, Ordering::Relaxed);
    inner.run_loop.stop();
    inner.thread.join().unwrap();
}
""",
    )
    result = run_static_core_contract_review(tmp_path, ["src/macos.rs"])
    assert "sliced-loop-shutdown-without-durable-intent" not in _roots(result)


def test_detects_privileged_state_missing_from_install_boundary(tmp_path: Path) -> None:
    _write(tmp_path, "deploy/install.sh", "#!/bin/sh\ninstall daemon /usr/local/bin/daemon\n")
    _write(
        tmp_path,
        "deploy/daemon.service",
        """
[Service]
User=daemon
AmbientCapabilities=CAP_NET_ADMIN
CapabilityBoundingSet=CAP_NET_ADMIN
ProtectSystem=strict
""",
    )
    _write(
        tmp_path,
        "src/router.rs",
        """
async fn enable_forwarding() -> Result<()> {
    const PATH: &str = "/proc/sys/net/ipv4/ip_forward";
    // The unprivileged service cannot write this root-owned proc file.
    if tokio::fs::write(PATH, "1").await.is_err() {
        run("sysctl", &["-w", "net.ipv4.ip_forward=1"]).await?;
    }
    Ok(())
}
""",
    )
    result = run_static_core_contract_review(
        tmp_path, ["deploy/install.sh", "deploy/daemon.service", "src/router.rs"]
    )
    assert "required-privileged-state-not-established" in _roots(result)


def test_accepts_privileged_state_established_by_installer(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "deploy/install.sh",
        "#!/bin/sh\nprintf 'net.ipv4.ip_forward = 1\\n' > /etc/sysctl.d/app.conf\nsysctl -w net.ipv4.ip_forward=1\n",
    )
    _write(tmp_path, "deploy/daemon.service", "[Service]\nUser=daemon\nProtectSystem=strict\n")
    _write(
        tmp_path,
        "src/router.rs",
        """
async fn enable_forwarding() {
    const PATH: &str = "/proc/sys/net/ipv4/ip_forward";
    // The unprivileged service cannot write this root-owned proc file.
    tokio::fs::write(PATH, "1").await.ok();
    run("sysctl", &["-w", "net.ipv4.ip_forward=1"]).await.ok();
}
""",
    )
    result = run_static_core_contract_review(
        tmp_path, ["deploy/install.sh", "deploy/daemon.service", "src/router.rs"]
    )
    assert "required-privileged-state-not-established" not in _roots(result)


def test_detects_specialized_parser_behind_closed_global_gate(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "BankParser.kt",
        """
abstract class BankParser {
    fun parse(message: String): Transaction? {
        if (!isTransactionMessage(message)) { return null }
        return Transaction(extractAmount(message))
    }
    protected open fun isTransactionMessage(message: String): Boolean {
        val transactionKeywords = listOf("debited", "credited", "paid")
        return transactionKeywords.any { message.lowercase().contains(it) }
    }
    protected open fun extractAmount(message: String): Amount? = null
}
""",
    )
    _write(
        tmp_path,
        "RegionalBankParser.kt",
        """
/** Sender patterns: XX-BANK-S (transactions). */
class RegionalBankParser : BaseIndianBankParser() {
    override fun extractAmount(message: String): Amount? = parseRegionalAmount(message)
    override fun extractTransactionType(message: String): Type? = regionalType(message)
}
""",
    )
    result = run_static_core_contract_review(
        tmp_path, ["BankParser.kt", "RegionalBankParser.kt"]
    )
    assert "specialized-parser-blocked-by-closed-global-gate" in _roots(result)


def test_accepts_specialized_parser_that_extends_recognition(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "BankParser.kt",
        """
abstract class BankParser {
    fun parse(message: String): Transaction? {
        if (!isTransactionMessage(message)) { return null }
        return Transaction(extractAmount(message))
    }
    protected open fun isTransactionMessage(message: String): Boolean {
        val transactionKeywords = listOf("debited", "credited", "paid")
        return transactionKeywords.any { message.lowercase().contains(it) }
    }
}
""",
    )
    _write(
        tmp_path,
        "RegionalBankParser.kt",
        """
/** Sender patterns: XX-BANK-S (transactions). */
class RegionalBankParser : BaseIndianBankParser() {
    override fun isTransactionMessage(message: String): Boolean =
        super.isTransactionMessage(message) || message.contains("bank-local-verb")
    override fun extractAmount(message: String): Amount? = parseRegionalAmount(message)
}
""",
    )
    result = run_static_core_contract_review(
        tmp_path, ["BankParser.kt", "RegionalBankParser.kt"]
    )
    assert "specialized-parser-blocked-by-closed-global-gate" not in _roots(result)
