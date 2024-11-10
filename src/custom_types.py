import enum

class BookSide(enum.Enum):
    BID = 1
    ASK = -1

    
class TradeSide(enum.Enum):
    BUY = 1
    SELL = -1

class OrderType(enum.Enum):
    MARKET = enum.auto()
    LIMIT = enum.auto()

class OrderExecutionRules(enum.Enum):
    FILL_OR_KILL = enum.auto()
    GOOD_TILL_CANCELLED = enum.auto()

