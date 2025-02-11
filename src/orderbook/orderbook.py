from bookkeeping.custom_types import Side
from orderbook.price_levels import Bids, Asks, PriceLevels

class OrderBook:
    """
    Order book data structure: stores and returns orders.
    Orders stores in bids and asks structures.
    """

    def __init__(self):     
        
        self.bids = Bids()
        self.asks = Asks()

    def get_levels(self, side: Side) -> PriceLevels:
        """
        Return price levels for specified side.
        """
        
        if side == Side.BID:
            return self.bids
        if side == Side.ASK:
            return self.asks
        
        raise TypeError(f'invalid type {type(side)}, must be of type Side')
    
    def get_opposite_side_levels(self, side: Side) -> PriceLevels:
        """
        Return opposite price level to specified side.
        """

        if side == Side.BID:
            return self.asks
        if side == Side.ASK:
            return self.bids
        
        raise TypeError(f'invalid type {type(side)}, must be of type Side')
    
    def get_bid_ask_mid(self) -> tuple[float, float, float]:
        """
        Return current market best-bid, best-ask, mid.
        """

        if not self.bids.is_empty() and not self.asks.is_empty():
            top_bid = self.bids.get_best_price()
            top_ask = self.asks.get_best_price()
        else:
            raise RuntimeError('Must have orders in orderbook in order to plot prices')
        
        mid = .5 * (top_bid + top_ask)

        return top_bid, top_ask, mid
    
    def get_orderbook_state(self) -> tuple[dict, dict]:
        """
        Return state for all levels on both sides: {price: (volume, #participants)}
        """

        bids_state = self.bids.get_price_levels_state()
        asks_state = self.asks.get_price_levels_state()

        return bids_state, asks_state
    
    def get_top_of_book_state(self) -> tuple[dict, dict]:
        """
        Return state for top-of-book ONLY on both sides: {price: (total_volume, #participants)}
        """

        bids_top_state = self.bids.get_top_of_book_state()
        asks_top_state = self.asks.get_top_of_book_state()

        return bids_top_state, asks_top_state
    
    def get_volumes(self) -> tuple[dict[float, int], dict[float, int]]:
        """
        Return volumes for all levels on both sides: {price: total_volume}
        """

        bid_volumes, ask_volumes = self.bids.get_volumes(), self.asks.get_volumes()

        return bid_volumes, ask_volumes