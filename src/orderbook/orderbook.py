from src.bookkeeping.custom_types import Side
from src.orderbook.book_side import BidSide, AskSide, BookSide
from src.bookkeeping.custom_types import FilledOrder, Side, OrderType
from src.bookkeeping.exceptions import DuplicateOrderError, InvalidOrderError
from src.orders.order import Order


class OrderBook:
    """
    Order book data structure: stores and returns orders.
    Orders stores in bids and asks structures.
    """

    def __init__(self):

        self.bid_side = BidSide()
        self.ask_side = AskSide()
        self._order_index: dict[int, tuple[Side, int]] = {}

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

    def post_order(self, order: Order) -> None:

        if order.order_type is not OrderType.LIMIT:
            raise InvalidOrderError(
                f"cannot post to book an order of type {order.order_type}"
            )

        if order.order_id in self._order_index:
            raise DuplicateOrderError(f"order {order.order_id} already exists in book")

        if order.is_filled:
            raise InvalidOrderError(
                f"order {order.order_id} is filled, cannot post to book"
            )

        opposite_side = self.get_opposite_book_side(order.side)
        if not opposite_side.is_empty:
            if (
                order.side == Side.BID and order.limit_price >= opposite_side.best_price
            ) or (
                order.side == Side.ASK and order.limit_price <= opposite_side.best_price
            ):
                raise InvalidOrderError("post expects non-crossing orders only")

        self.get_book_side(order.side).post_order(order)

        self._order_index[order.order_id] = (order.side, order.limit_price)

    def cancel_order(self, order_id: int) -> None: ...

    def fill_top(self, order: Order) -> list[FilledOrder]:

        filled_orders = []
        aggressor = order

        opposite_book_side = self.get_opposite_book_side(aggressor.side)
        queue = opposite_book_side.top_level

        while not (aggressor.is_filled or queue.is_empty):
            resting = queue.next_order_to_execute
            snapshot_resting = resting.snapshot()
            snapshot_aggressor = aggressor.snapshot()

            filled_qty = resting.fill(aggressor.remaining_quantity)
            aggressor.fill(filled_qty)

            filled_order = FilledOrder(snapshot_resting, snapshot_aggressor, filled_qty)
            filled_orders.append(filled_order)

            if resting.is_filled:
                queue.remove_order(resting)

        if queue.is_empty:
            opposite_book_side.delete_level(opposite_book_side.best_price)

        return filled_orders

    def get_order(self, order_id: int) -> Order:

        if order_id not in self._order_index:
            raise InvalidOrderError(f"order {order_id} not in book")

        side, price = self._order_index[order_id]
        bookside = self.get_book_side(side)
        order_queue = bookside.levels[price]
        return order_queue.queue[order_id]
