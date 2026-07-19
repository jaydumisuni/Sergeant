from __future__ import annotations

from pathlib import Path

from main_review.static_transfer_12_review import run_static_transfer_12_review


AUTH_ROOT = "http-debug-dump-logs-authorization-without-redaction"
BODY_ROOT = "http-debug-dump-consumes-live-request-body"
PROCESS_ROOT = "external-process-wait-without-timeout-or-cancellation"
TX_ROOT = "multi-resource-financial-operation-spans-separate-transactions"


def _roots(result: dict) -> set[str]:
    return {str(item.get("root_cause")) for item in result.get("findings", [])}


def test_live_go_request_dump_exposes_auth_and_consumes_body(tmp_path: Path) -> None:
    source = tmp_path / "client.go"
    source.write_text(
        '''
package api

func (dt *debugTransport) RoundTrip(req *http.Request) (*http.Response, error) {
    dump, _ := httputil.DumpRequestOut(req, true)
    fmt.Fprintf(os.Stderr, "DEBUG REQUEST: %s", dump)
    return dt.transport.RoundTrip(req)
}
        ''',
        encoding="utf-8",
    )

    result = run_static_transfer_12_review(tmp_path, ["client.go"])
    roots = _roots(result)

    assert AUTH_ROOT in roots
    assert BODY_ROOT in roots


def test_redacted_header_only_clone_preserves_live_request(tmp_path: Path) -> None:
    source = tmp_path / "client.go"
    source.write_text(
        '''
package api

func (dt *debugTransport) RoundTrip(req *http.Request) (*http.Response, error) {
    safeReq := req.Clone(req.Context())
    if safeReq.Header.Get("Authorization") != "" {
        safeReq.Header.Set("Authorization", "Bearer [REDACTED]")
    }
    safeReq.Body = http.NoBody
    dump, _ := httputil.DumpRequestOut(safeReq, false)
    fmt.Fprintf(os.Stderr, "DEBUG REQUEST: %s", dump)
    return dt.transport.RoundTrip(req)
}
        ''',
        encoding="utf-8",
    )

    result = run_static_transfer_12_review(tmp_path, ["client.go"])
    roots = _roots(result)

    assert AUTH_ROOT not in roots
    assert BODY_ROOT not in roots


def test_non_logging_request_serialization_is_not_misclassified(tmp_path: Path) -> None:
    source = tmp_path / "proxy.go"
    source.write_text(
        '''
package proxy

func encode(req *http.Request) ([]byte, error) {
    return httputil.DumpRequestOut(req, false)
}
        ''',
        encoding="utf-8",
    )

    result = run_static_transfer_12_review(tmp_path, ["proxy.go"])

    assert AUTH_ROOT not in _roots(result)
    assert BODY_ROOT not in _roots(result)


def test_swift_process_wait_without_timeout_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "Enumerator.swift"
    source.write_text(
        '''
import Foundation

func enumerate() -> [String] {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/sfltool")
    let pipe = Pipe()
    process.standardOutput = pipe
    try? process.run()
    let data = pipe.fileHandleForReading.readDataToEndOfFile()
    process.waitUntilExit()
    return [String(data: data, encoding: .utf8) ?? ""]
}
        ''',
        encoding="utf-8",
    )

    result = run_static_transfer_12_review(tmp_path, ["Enumerator.swift"])

    assert PROCESS_ROOT in _roots(result)


def test_bounded_swift_process_runner_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "Enumerator.swift"
    source.write_text(
        '''
import Foundation

func enumerate() async -> [String] {
    guard let result = try? await ProcessRunner.run(
        executable: "/usr/bin/sfltool",
        arguments: ["dumpbtm"],
        timeout: 10
    ), result.didSucceed else { return [] }
    return [result.output]
}
        ''',
        encoding="utf-8",
    )

    result = run_static_transfer_12_review(tmp_path, ["Enumerator.swift"])

    assert PROCESS_ROOT not in _roots(result)


def test_fire_and_forget_swift_process_is_not_wait_lifecycle_finding(tmp_path: Path) -> None:
    source = tmp_path / "Launcher.swift"
    source.write_text(
        '''
import Foundation

func launch() throws {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/open")
    try process.run()
}
        ''',
        encoding="utf-8",
    )

    result = run_static_transfer_12_review(tmp_path, ["Launcher.swift"])

    assert PROCESS_ROOT not in _roots(result)


def test_money_and_aggregate_writes_in_separate_transactions_are_reported(tmp_path: Path) -> None:
    route = tmp_path / "route.ts"
    route.write_text(
        '''
export async function POST(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const { rows } = await db.query(`SELECT * FROM boz_markets WHERE id=$1`, [id]);
  const pools = { ...rows[0].pools };
  await moveVault({ wallet, delta: -micro, kind: 'STAKE' });
  pools[outcome] = (pools[outcome] ?? 0) + micro;
  await db.query(`UPDATE boz_markets SET pools=$1 WHERE id=$2`, [JSON.stringify(pools), id]);
  await db.query(`INSERT INTO boz_predictions (id, market_id) VALUES ($1,$2)`, [randomUUID(), id]);
}
        ''',
        encoding="utf-8",
    )
    vault = tmp_path / "vault.ts"
    vault.write_text(
        '''
export async function moveVault(opts: MoveVaultOpts): Promise<number> {
  const client = await db.connect();
  try {
    await client.query('BEGIN');
    await client.query(`UPDATE boz_vault SET balance_micro=$2 WHERE wallet_address=$1`, [opts.wallet, opts.delta]);
    await client.query('COMMIT');
    return opts.delta;
  } finally {
    client.release();
  }
}
        ''',
        encoding="utf-8",
    )

    result = run_static_transfer_12_review(tmp_path, ["route.ts", "vault.ts"])

    assert TX_ROOT in _roots(result)


def test_single_transaction_and_row_lock_are_clean(tmp_path: Path) -> None:
    route = tmp_path / "route.ts"
    route.write_text(
        '''
export async function POST(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const client = await db.connect();
  try {
    await client.query('BEGIN');
    const { rows } = await client.query(`SELECT * FROM boz_markets WHERE id=$1 FOR UPDATE`, [id]);
    const pools = { ...rows[0].pools };
    await moveVaultTx(client, { wallet, delta: -micro, kind: 'STAKE' });
    pools[outcome] = (pools[outcome] ?? 0) + micro;
    await client.query(`UPDATE boz_markets SET pools=$1 WHERE id=$2`, [JSON.stringify(pools), id]);
    await client.query(`INSERT INTO boz_predictions (id, market_id) VALUES ($1,$2)`, [randomUUID(), id]);
    await client.query('COMMIT');
  } finally {
    client.release();
  }
}
        ''',
        encoding="utf-8",
    )
    vault = tmp_path / "vault.ts"
    vault.write_text(
        '''
export async function moveVaultTx(client: PoolClient, opts: MoveVaultOpts): Promise<number> {
  await client.query(`UPDATE boz_vault SET balance_micro=$2 WHERE wallet_address=$1`, [opts.wallet, opts.delta]);
  return opts.delta;
}
        ''',
        encoding="utf-8",
    )

    result = run_static_transfer_12_review(tmp_path, ["route.ts", "vault.ts"])

    assert TX_ROOT not in _roots(result)
