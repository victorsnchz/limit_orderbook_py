"""Core value types for the order book: enums, immutable snapshots, and the
event/result taxonomy emitted by matching and execution."""

import enum
from dataclasses import dataclass
from typing import Optional


class Side(enum.Enum):
    """Book side. The integer values double as the price-ordering sign."""

    BID = 1
    ASK = -1


class OrderType(enum.Enum):
    """Order pricing type: market (no limit) or limit."""

    MARKET = enum.auto()
    LIMIT = enum.auto()


class ExecutionRule(enum.Enum):
    """Time-in-force rule: good-for-day, good-till-cancelled, immediate-or-cancel."""

    GFD = enum.auto()
    GTC = enum.auto()
    IOC = enum.auto()


@dataclass(frozen=True)
class OrderSnapshot:
    """Immutable copy of an order's state at the moment an event is emitted."""

    side: Side
    order_type: OrderType
    initial_quantity: int
    remaining_quantity: int
    order_id: int
    user_id: int
    limit_price: Optional[int] = None
    execution_rule: Optional[ExecutionRule] = None


@dataclass(frozen=True)
class LevelState:
    """Aggregate state of a single price level."""

    total_volume: int
    order_count: int
    participant_count: int


class FillStatus(enum.Enum):
    """Degree to which an order's quantity was filled."""

    FILLED = enum.auto()
    PARTIALLY_FILLED = enum.auto()
    UNFILLED = enum.auto()


class EventKind(enum.Enum):
    """Tag identifying which payload an Event carries."""

    ACCEPTED = enum.auto()
    REJECTED = enum.auto()
    FILLED = enum.auto()
    POSTED = enum.auto()
    CANCELLED = enum.auto()
    MODIFIED = enum.auto()


# Book-transition payloads: one atomic change to book state, each paired with an
# EventKind via PAYLOAD_KIND and surfaced only wrapped in an Event.


@dataclass(frozen=True)
class FilledPayload:
    """A resting order had `filled_quantity` taken by an aggressor."""

    resting: OrderSnapshot
    filled_quantity: int


@dataclass(frozen=True)
class PostedPayload:
    """An order rested on the book."""

    aggressor: OrderSnapshot


@dataclass(frozen=True)
class CancelledPayload:
    """An order was removed from the book."""

    aggressor: OrderSnapshot


@dataclass(frozen=True)
class ModifiedPayload:
    """An order was replaced in place, carrying both states."""

    original_order: OrderSnapshot
    modified_order: OrderSnapshot


# Policy-lifecycle payloads: an execution policy's verdict on an incoming order.
# These are never pushed into the book.


@dataclass(frozen=True)
class AcceptedPayload:
    """An execution policy admitted an incoming order for matching."""

    aggressor: OrderSnapshot


@dataclass(frozen=True)
class RejectedPayload:
    """An execution policy refused an incoming order, with the reason."""

    aggressor: OrderSnapshot
    rejected_reason: str


@dataclass(frozen=True)
class ExecutionReport:
    """A policy's terminal summary of how an aggressor resolved."""

    aggressor: OrderSnapshot
    posted: bool
    status: FillStatus


Payload = (
    AcceptedPayload
    | RejectedPayload
    | FilledPayload
    | PostedPayload
    | CancelledPayload
    | ModifiedPayload
)


# Single source of truth for the kind <-> payload pairing; Event.of relies on it.
PAYLOAD_KIND: dict[type, EventKind] = {
    AcceptedPayload: EventKind.ACCEPTED,
    RejectedPayload: EventKind.REJECTED,
    FilledPayload: EventKind.FILLED,
    PostedPayload: EventKind.POSTED,
    CancelledPayload: EventKind.CANCELLED,
    ModifiedPayload: EventKind.MODIFIED,
}


@dataclass(frozen=True)
class Event:
    """A payload tagged with its kind; the unit of the execution event log."""

    kind: EventKind
    payload: Payload
    # TODO: for logging
    # timestamp: str
    # sequence: int

    @classmethod
    def of(cls, payload: Payload) -> "Event":
        """Wrap `payload` in an Event tagged with its matching kind."""
        return cls(kind=PAYLOAD_KIND[type(payload)], payload=payload)


@dataclass(frozen=True)
class ExecutionResult:
    """A policy's outcome: a terminal report plus the ordered events that produced it."""

    report: ExecutionReport
    events: list[Event]

    @property
    def is_rejected(self) -> bool:
        """Whether any recorded event is a rejection."""
        for event in self.events:
            if event.kind == EventKind.REJECTED:
                return True

        return False
