import enum
from dataclasses import dataclass


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
class LevelState:
    total_volume: int
    order_count: int
    participant_count: int
