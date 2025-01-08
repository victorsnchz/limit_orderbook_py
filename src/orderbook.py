from order import Order, LimitOrder, MarketOrder
from custom_types import OrderType, Side, ExecutionRules
from price_levels import Bids, Asks
import execution_schedules

class OrderBook:

    def __init__(self):
        
       #todo 
        self.bids = Bids()
        self.asks = Asks()

    def get_levels(self, side: Side):
        
        if side == Side.BID:
            return self.bids
        if side == Side.ASK:
            return self.asks
        
        raise TypeError(f'invalid type {type(side)}, must be of type Side')
    
    def get_opposite_side_levels(self, side: Side):

        if side == Side.BID:
            return self.asks
        if side == Side.ASK:
            return self.bids
        
        raise TypeError(f'invalid type {type(side)}, must be of type Side')

    