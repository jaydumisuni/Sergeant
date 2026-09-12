"""SAE-130C bounded state / failure-space reasoning."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence


class FailureSpaceError(ValueError):
    """Raised when a trace cannot be admitted into the bounded failure model."""


class FailureEventKind(str, Enum):
    BEGIN = "BEGIN"
    COMMIT = "COMMIT"
    PARTIAL_COMMIT = "PARTIAL_COMMIT"
    ACK = "ACK"
    ACK_LOSS = "ACK_LOSS"
    RETRY = "RETRY"
    DUPLICATE = "DUPLICATE"
    RESTART = "RESTART"
    RECOVER = "RECOVER"


@dataclass(frozen=True)
class FailureEvent:
    sequence: int
    operation: str
    kind: FailureEventKind

    def __post_init__(self) -> None:
        if not isinstance(self.sequence, int) or isinstance(self.sequence, bool) or self.sequence <= 0:
            raise FailureSpaceError("sequence must be a positive integer")
        if (
            not isinstance(self.operation, str)
            or not self.operation
            or self.operation != self.operation.strip()
        ):
            raise FailureSpaceError("operation must be canonical")
        if not isinstance(self.kind, FailureEventKind):
            raise FailureSpaceError("event kind must be canonical")


@dataclass(frozen=True)
class StateFailureResult:
    terminalized_operations: tuple[str, ...]
    recovered_operations: tuple[str, ...]
    recovery_required: tuple[str, ...]
    duplicate_effects: tuple[str, ...]


@dataclass
class _OperationState:
    begun: bool = False
    committed: bool = False
    terminalized: bool = False
    needs_recovery: bool = False
    recovered: bool = False
    ack_lost: bool = False
    retry_seen: bool = False


@dataclass(frozen=True)
class StateFailureTrace:
    events: tuple[FailureEvent, ...]

    @classmethod
    def create(cls, *, events: Sequence[FailureEvent]) -> "StateFailureTrace":
        values = tuple(events)
        if not values:
            raise FailureSpaceError("trace must contain at least one event")
        if any(not isinstance(event, FailureEvent) for event in values):
            raise FailureSpaceError("trace contains a noncanonical event")
        sequences = tuple(event.sequence for event in values)
        if any(current <= previous for previous, current in zip(sequences, sequences[1:])):
            raise FailureSpaceError("sequence must be strictly increasing")
        return cls(values)

    def analyze(self) -> StateFailureResult:
        states: dict[str, _OperationState] = {}
        recovered: set[str] = set()
        duplicate_effects: set[str] = set()

        for event in self.events:
            state = states.setdefault(event.operation, _OperationState())
            kind = event.kind

            if state.terminalized and kind not in {FailureEventKind.DUPLICATE}:
                raise FailureSpaceError(
                    f"operation {event.operation} received event after terminalization"
                )

            if kind is FailureEventKind.BEGIN:
                if state.begun:
                    raise FailureSpaceError(f"operation {event.operation} has duplicate begin")
                state.begun = True
                continue

            if not state.begun:
                raise FailureSpaceError(
                    f"operation {event.operation} event occurs before begin"
                )

            if kind is FailureEventKind.PARTIAL_COMMIT:
                if state.committed:
                    duplicate_effects.add(event.operation)
                    raise FailureSpaceError(
                        f"duplicate effect for operation {event.operation}"
                    )
                state.needs_recovery = True
                continue

            if kind is FailureEventKind.RESTART:
                if not state.committed:
                    state.needs_recovery = True
                continue

            if kind is FailureEventKind.RECOVER:
                if not state.needs_recovery:
                    raise FailureSpaceError(
                        f"recovery for operation {event.operation} has no failed state"
                    )
                state.needs_recovery = False
                state.recovered = True
                recovered.add(event.operation)
                continue

            if kind is FailureEventKind.COMMIT:
                if state.needs_recovery:
                    raise FailureSpaceError(
                        f"operation {event.operation} requires recovery before commit"
                    )
                if state.committed:
                    duplicate_effects.add(event.operation)
                    raise FailureSpaceError(
                        f"duplicate effect for operation {event.operation}"
                    )
                state.committed = True
                continue

            if kind is FailureEventKind.ACK_LOSS:
                if not state.committed:
                    raise FailureSpaceError(
                        f"ack loss for operation {event.operation} precedes commit"
                    )
                state.ack_lost = True
                continue

            if kind is FailureEventKind.RETRY:
                if not (state.committed or state.ack_lost or state.needs_recovery):
                    raise FailureSpaceError(
                        f"retry for operation {event.operation} has no failure basis"
                    )
                state.retry_seen = True
                continue

            if kind is FailureEventKind.DUPLICATE:
                if not state.committed:
                    raise FailureSpaceError(
                        f"duplicate delivery for operation {event.operation} precedes commit"
                    )
                # A duplicate-delivery observation is safe only after a retry/failure
                # boundary; it represents deduplication, not a second effect.
                if not (state.retry_seen or state.ack_lost):
                    raise FailureSpaceError(
                        f"duplicate delivery for operation {event.operation} has no retry basis"
                    )
                continue

            if kind is FailureEventKind.ACK:
                if state.needs_recovery:
                    raise FailureSpaceError(
                        f"operation {event.operation} requires recovery before ack"
                    )
                if not state.committed:
                    raise FailureSpaceError(
                        f"ack for operation {event.operation} precedes commit"
                    )
                state.terminalized = True
                continue

            raise FailureSpaceError(f"unsupported event kind {kind!r}")

        terminalized = tuple(
            sorted(operation for operation, state in states.items() if state.terminalized)
        )
        recovery_required = tuple(
            sorted(operation for operation, state in states.items() if state.needs_recovery)
        )
        return StateFailureResult(
            terminalized_operations=terminalized,
            recovered_operations=tuple(sorted(recovered)),
            recovery_required=recovery_required,
            duplicate_effects=tuple(sorted(duplicate_effects)),
         )
