from src.bookkeeping.custom_types import Side
from src.orderbook.book_side import BidSide, AskSide, BookSide


class OrderBook:
    """
    Order book data structure: stores and returns orders.
    Orders stores in bids and asks structures.
    """

    def __init__(self):

        self.bid_side = BidSide()
        self.ask_side = AskSide()

    def get_book_side(self, side: Side) -> BookSide:
        """
        Return specified book side.
        """

        if side == Side.BID:
            return self.bid_side
        if side == Side.ASK:
            return self.ask_side

        raise TypeError(f"invalid type {type(side)}, must be of type Side")

    def get_opposite_book_side(self, side: Side) -> BookSide:
        """
        Return opposite book side to the one specified.
        """

        if side == Side.BID:
            return self.ask_side
        if side == Side.ASK:
            return self.bid_side

        raise TypeError(f"invalid type {type(side)}, must be of type Side")

    def get_bid_ask_mid(self) -> tuple[int, int, float]:
        """
        Return current market best-bid, best-ask, mid.
        """

        if not self.bid_side.is_empty and not self.ask_side.is_empty:
            top_bid = self.bid_side.best_price
            top_ask = self.ask_side.best_price
        else:
            raise RuntimeError("Must have orders in orderbook in order to plot prices")

        mid = 0.5 * (top_bid + top_ask)

        return top_bid, top_ask, mid

    def get_states(self) -> tuple[dict, dict]:
        """
        Return state for all levels on both sides: {price: (volume, #participants)}
        """

        bids_state = self.bid_side.get_states()
        asks_state = self.ask_side.get_states()

        return bids_state, asks_state

    def get_top_state(self) -> tuple[dict, dict]:
        """
        Return state for top-of-book ONLY on both sides: {price: (total_volume, #participants)}
        """

        bids_top_state = self.bid_side.get_top_state()
        asks_top_state = self.ask_side.get_top_state()

        return bids_top_state, asks_top_state

    def get_volumes(self) -> tuple[dict[float, int], dict[float, int]]:
        """
        Return volumes for all levels on both sides: {price: total_volume}
        """

        bid_volumes, ask_volumes = (
            self.bid_side.get_volumes(),
            self.ask_side.get_volumes(),
        )

        return bid_volumes, ask_volumes
