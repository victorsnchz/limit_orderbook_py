import random
from order import LimitOrder, OrderParameters, OrderID, ExecutionRules
from custom_types import Side

def generate():

    bids = []
    asks = []

    for i in range(20):
        bid_price = random.randint(95, 105)
        ask_price = random.randint(106, 115)
        bids.append(LimitOrder(OrderParameters(Side.BID, random.randint(1, 50)), OrderID(i), limit_price=bid_price, execution_rules=ExecutionRules.GTC))
        asks.append(LimitOrder(OrderParameters(Side.ASK, random.randint(1, 50)), OrderID(i+20), limit_price=ask_price, execution_rules=ExecutionRules.GTC))
        
        

    return bids, asks