import pytest

from main_review.state_failure_reasoning import (
    FailureEvent, FailureEventKind, FailureSpaceError, StateFailureTrace,
)


def ev(seq, kind, op='op-1'):
    return FailureEvent(sequence=seq, operation=op, kind=kind)


def test_retry_after_ack_loss_is_terminalized_once():
    trace = StateFailureTrace.create(events=[
        ev(1, FailureEventKind.BEGIN),
        ev(2, FailureEventKind.COMMIT),
        ev(3, FailureEventKind.ACK_LOSS),
        ev(4, FailureEventKind.RETRY),
        ev(5, FailureEventKind.DUPLICATE),
        ev(6, FailureEventKind.ACK),
    ])
    result = trace.analyze()
    assert result.terminalized_operations == ('op-1',)
    assert result.duplicate_effects == ()
    assert result.recovery_required == ()


def test_partial_commit_requires_recovery_before_terminalization():
    trace = StateFailureTrace.create(events=[
        ev(1, FailureEventKind.BEGIN),
        ev(2, FailureEventKind.PARTIAL_COMMIT),
        ev(3, FailureEventKind.RESTART),
        ev(4, FailureEventKind.RECOVER),
        ev(5, FailureEventKind.COMMIT),
        ev(6, FailureEventKind.ACK),
    ])
    result = trace.analyze()
    assert result.terminalized_operations == ('op-1',)
    assert result.recovered_operations == ('op-1',)


def test_partial_commit_without_recovery_fails_closed():
    trace = StateFailureTrace.create(events=[
        ev(1, FailureEventKind.BEGIN),
        ev(2, FailureEventKind.PARTIAL_COMMIT),
        ev(3, FailureEventKind.ACK),
    ])
    with pytest.raises(FailureSpaceError, match='recovery'):
        trace.analyze()


def test_reordered_or_duplicate_sequence_fails_closed():
    with pytest.raises(FailureSpaceError, match='sequence'):
        StateFailureTrace.create(events=[ev(2, FailureEventKind.BEGIN), ev(1, FailureEventKind.COMMIT)])
    with pytest.raises(FailureSpaceError, match='sequence'):
        StateFailureTrace.create(events=[ev(1, FailureEventKind.BEGIN), ev(1, FailureEventKind.COMMIT)])


def test_duplicate_commit_effect_is_rejected():
    trace = StateFailureTrace.create(events=[
        ev(1, FailureEventKind.BEGIN), ev(2, FailureEventKind.COMMIT),
        ev(3, FailureEventKind.RETRY), ev(4, FailureEventKind.COMMIT),
    ])
    with pytest.raises(FailureSpaceError, match='duplicate effect'):
        trace.analyze()


def test_concurrent_operations_remain_isolated_and_deterministic():
    trace = StateFailureTrace.create(events=[
        ev(1, FailureEventKind.BEGIN, 'a'), ev(2, FailureEventKind.BEGIN, 'b'),
        ev(3, FailureEventKind.COMMIT, 'b'), ev(4, FailureEventKind.ACK, 'b'),
        ev(5, FailureEventKind.COMMIT, 'a'), ev(6, FailureEventKind.ACK, 'a'),
    ])
    result = trace.analyze()
    assert result.terminalized_operations == ('a', 'b')


def test_restart_of_uncommitted_operation_requires_explicit_recovery():
    trace = StateFailureTrace.create(events=[
        ev(1, FailureEventKind.BEGIN), ev(2, FailureEventKind.RESTART),
        ev(3, FailureEventKind.COMMIT), ev(4, FailureEventKind.ACK),
    ])
    with pytest.raises(FailureSpaceError, match='recovery'):
        trace.analyze()


def test_unknown_or_noncanonical_event_data_is_rejected():
    with pytest.raises(FailureSpaceError):
        FailureEvent(sequence=1, operation=' op-1', kind=FailureEventKind.BEGIN)
    with pytest.raises(FailureSpaceError):
        FailureEvent(sequence=0, operation='op-1', kind=FailureEventKind.BEGIN)
