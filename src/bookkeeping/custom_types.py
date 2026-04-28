import enum
from dataclasses import dataclass
from typing import Optional


class Side(enum.Enum):
    BID = 1
    ASK = -1


class OrderType(enum.Enum):
    MARKET = enum.auto()
    LIMIT = enum.auto()


class ExecutionRule(enum.Enum):
    GFD = enum.auto()
    GTC = enum.auto()
    IOC = enum.auto()


@dataclass(frozen=True)
class OrderSnapshot:
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
    total_volume: int
    order_count: int
    participant_count: int


class FillStatus(enum.Enum):
    FILLED = enum.auto()
    PARTIALLY_FILLED = enum.auto()
    UNFILLED = enum.auto()


class EventKind(enum.Enum):
    ACCEPTED = enum.auto()
    FILLED = enum.auto()
    POSTED = enum.auto()
    # backlog: REJECTED, CANCELLED, MODIFIED


@dataclass(frozen=True)
class AcceptedPayload:
    aggressor: OrderSnapshot


@dataclass(frozen=True)
class FilledPayload:
    resting: OrderSnapshot
    filled_qty: int


@dataclass(frozen=True)
class PostedPayload:
    aggressor: OrderSnapshot


Payload = AcceptedPayload | FilledPayload | PostedPayload


@dataclass(frozen=True)
class Event:
    kind: EventKind
    payload: Payload
    # TODO: for logging
    # timestamp: str
    # sequence: int


@dataclass(frozen=True)
class ExecutionReport:
    aggresssor: OrderSnapshot
    posted: bool
    status: FillStatus


@dataclass(frozen=True)
class ExecutionResult:
    report: ExecutionReport
    events: list[Event]
