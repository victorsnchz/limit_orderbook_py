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


@dataclass(frozen=True)
class FilledOrder:
    resting: OrderSnapshot
    aggressor: OrderSnapshot
    filled_qty: int


class ExecutionStatus(enum.Enum):
    FILLED = enum.auto()
    PARTIALLY_FILELD = enum.auto()
    UNFILLED = enum.auto()
    RESTED = enum.auto()
