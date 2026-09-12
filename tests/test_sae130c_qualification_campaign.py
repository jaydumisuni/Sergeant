from __future__ import annotations

import pytest

from main_review.state_failure_reasoning import (
    FailureEvent,
    FailureEventKind,
    FailureSpaceError,
    StateFailureTrace,
)


def ev(seq: int, kind: FailureEventKind, op: str = "op-1") -> FailureEvent:
    return FailureEvent(sequence=seq, operation=op, kind=kind)


def test_qualification_retry_duplicate_and_ack_loss_terminalize_once():
    result = StateFailureTrace.create(events=(
        ev(1, FailureEventKind.BEGIN),
        ev(2, FailureEventKind.COMMIT),
        ev(3, FailureEventKind.ACK_LOSS),
        ev(4, FailureEventKind.RETRY),
        ev(5, FailureEventKind.DUPLICATE),
        ev(6, FailureEventKind.ACK),
    )).analyze()
    assert result.terminalized_operations == ("op-1",)
    assert result.duplicate_effects == ()


def test_qualification_restart_partial_commit_and_recovery_are_explicit():
    result = StateFailureTrace.create(events=(
        ev(1, FailureEventKind.BEGIN),
        ev(2, FailureEventKind.PARTIAL_COMMIT),
        ev(3, FailureEventKind.RESTART),
        ev(4, FailureEventKind.RECOVER),
        ev(5, FailureEventKind.COMMIT),
        ev(6, FailureEventKind.ACK),
    )).analyze()
    assert result.recovered_operations == ("op-1",)
    assert result.terminalized_operations == ("op-1",)


def test_qualification_rejects_unrecovered_partial_state_and_duplicate_effect():
    with pytest.raises(FailureSpaceError, match="recovery"):
        StateFailureTrace.create(events=(
            ev(1, FailureEventKind.BEGIN),
            ev(2, FailureEventKind.PARTIAL_COMMIT),
            ev(3, FailureEventKind.ACK),
        )).analyze()
    with pytest.raises(FailureSpaceError, match="duplicate effect"):
        StateFailureTrace.create(events=(
            ev(1, FailureEventKind.BEGIN),
            ev(2, FailureEventKind.COMMIT),
            ev(3, FailureEventKind.RETRY),
            ev(4, FailureEventKind.COMMIT),
        )).analyze()


def test_qualification_concurrency_isolation_and_ordering_fail_closed():
    result = StateFailureTrace.create(events=(
        ev(1, FailureEventKind.BEGIN, "a"),
        ev(2, FailureEventKind.BEGIN, "b"),
        ev(3, FailureEventKind.COMMIT, "b"),
        ev(4, FailureEventKind.ACK, "b"),
        ev(5, FailureEventKind.COMMIT, "a"),
        ev(6, FailureEventKind.ACK, "a"),
    )).analyze()
    assert result.terminalized_operations == ("a", "b")
    with pytest.raises(FailureSpaceError, match="sequence"):
        StateFailureTrace.create(events=(
            ev(2, FailureEventKind.BEGIN),
            ev(1, FailureEventKind.COMMIT),
        ))
