import enum
from typing import Self
        
class Side(enum.Enum):
    BID = 1
    ASK = -1

class OrderType(enum.Enum):
    MARKET = enum.auto()
    LIMIT = enum.auto() 

class ExecutionRules(enum.Enum):
    GFD = enum.auto()
    GTC = enum.auto()
    IOC = enum.auto()