"""
Two-sided limit order book with id-indexed O(1) order lookup.
Owns book state and single-level matching; multi-level routing is the caller's job.
"""

from lob.bookkeeping.custom_types import Side
from lob.orderbook.book_side import BidSide, AskSide, BookSide
from lob.bookkeeping.custom_types import (
    FilledPayload,
    OrderType,
    PostedPayload,
    CancelledPayload,
    ModifiedPayload,
)
from lob.bookkeeping.exceptions import (
    DuplicateOrderError,
    InvalidOrderError,
    OrderBookError,
    OrderNotFoundError,
    PriceLevelNotFoundError,
)
from lob.orders.order import Order


class OrderBook:
    """
    Composes `BidSide` and `AskSide` with an id-keyed index for O(1) order lookup.
    """

    def __init__(self):

        self.bid_side = BidSide()
        self.ask_side = AskSide()

        self._order_index: dict[int, tuple[Side, int]] = {}

    # --- getters ----------------------------------------------------------------------

    def get_book_side(self, side: Side) -> BookSide:
        """
        Return the matching book side.
        """

        if side == Side.BID:
            return self.bid_side
        if side == Side.ASK:
            return self.ask_side

        raise TypeError(f"invalid type {type(side)}, must be of type Side")

    def get_opposite_book_side(self, side: Side) -> BookSide:
        """
        Return the opposite book side.
        """

        if side == Side.BID:
            return self.ask_side
        if side == Side.ASK:
            return self.bid_side

        raise TypeError(f"invalid type {type(side)}, must be of type Side")

    def get_bid_ask_mid(self) -> tuple[int, int, float]:
        """
        Return `(best_bid, best_ask, mid)`. Raises if either side is empty.
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
        Return `(bid_state, ask_state)` as `{price: (volume, n_participants)}`.
        """

        bids_state = self.bid_side.get_states()
        asks_state = self.ask_side.get_states()

        return bids_state, asks_state

    def get_top_state(self) -> tuple[dict, dict]:
        """
        Return top-of-book state per side as `{price: (volume, n_participants)}`.
        """

        bids_top_state = self.bid_side.get_top_state()
        asks_top_state = self.ask_side.get_top_state()

        return bids_top_state, asks_top_state

    def get_volumes(self) -> tuple[dict[float, int], dict[float, int]]:
        """
        Return `(bid_volumes, ask_volumes)` as `{price: total_volume}`.
        """

        bid_volumes, ask_volumes = (
            self.bid_side.get_volumes(),
            self.ask_side.get_volumes(),
        )

        return bid_volumes, ask_volumes

    def get_order(self, order_id: int) -> Order:
        """
        Return the resting order with `order_id`. Raises `OrderNotFoundError` if absent.
        """

        if order_id not in self._order_index:
            raise OrderNotFoundError(f"order {order_id} not in book")

        side, price = self._order_index[order_id]

        try:
            return self.get_book_side(side).get_order(price, order_id)
        except (OrderNotFoundError, PriceLevelNotFoundError) as exc:
            raise OrderBookError(
                f"index/book inconsistency: order {order_id} indexed at "
                f"{side}/{price} but absent from book."
            ) from exc

    def __contains__(self, order_id: int) -> bool:
        return order_id in self._order_index

    def _validate_postable(self, order: Order) -> None:
        """
        Enforce post preconditions. Raises `InvalidOrderError` on non-LIMIT type,
        filled order, non-positive quantity, missing/non-positive price, or a
        crossing price; `DuplicateOrderError` on a duplicate id.
        """

        if order.order_type is not OrderType.LIMIT:
            raise InvalidOrderError(
                f"cannot post to book an order of type {order.order_type}"
            )

        if order.order_id in self:
            raise DuplicateOrderError(
                f"order {order.order_id} already exists in book"
            )

        if order.is_filled:
            raise InvalidOrderError(
                f"order {order.order_id} is filled, cannot post to book"
            )

        if order.remaining_quantity <= 0:
            raise InvalidOrderError(
                f"order {order.order_id} has <= 0 quantity, cannot post to book"
            )

        if order.limit_price is None:
            raise InvalidOrderError(
                f"order {order.order_id} has no price, cannot post to book"
            )

        if order.limit_price <= 0:
            raise InvalidOrderError(
                f"order {order.order_id} has non-positive price, cannot post to book"
            )

        opposite_side = self.get_opposite_book_side(order.side)
        if not opposite_side.is_empty:
            crosses = (
                order.side == Side.BID and order.limit_price >= opposite_side.best_price
            ) or (
                order.side == Side.ASK and order.limit_price <= opposite_side.best_price
            )
            if crosses:
                raise InvalidOrderError("post expects non-crossing orders only")

    def post_order(self, order: Order) -> PostedPayload:
        """
        Admit a non-crossing LIMIT `order` to its side and index it by id.
        Raises on non-LIMIT type, duplicate id, filled order, or a price that
        would cross the opposite top.
        """

        self._validate_postable(order)

        snapshot = order.snapshot()

        self.get_book_side(order.side).post_order(order)

        self._order_index[order.order_id] = (order.side, order.limit_price)

        return PostedPayload(snapshot)

    def cancel_order(self, order_id: int) -> CancelledPayload:
        """
        Remove the order with `order_id` from its side and index. Raises
        `OrderNotFoundError` if absent.
        """

        if order_id not in self:
            raise OrderNotFoundError(f"order {order_id} not found in orderbook")

        snapshot = self.get_order(order_id).snapshot()
        side, price = self._order_index[order_id]
        book_side = self.get_book_side(side)
        book_side.delete_order(order_id, price)
        del self._order_index[order_id]
        return CancelledPayload(snapshot)

    def fill_top(self, order: Order) -> list[FilledPayload]:
        """
        Match `order` against the opposite top level under price-time priority.
        Stops when the aggressor fills or the level exhausts. Returns one
        `FilledPayload` per touched resting order.
        """

        filled_payloads = []
        aggressor = order

        opposite_book_side = self.get_opposite_book_side(aggressor.side)
        if opposite_book_side.is_empty:
            return []
        # TODO: handle matching against an empty book more deliberately,
        # clarify responsibilities, and add unit and integration tests.
        queue = opposite_book_side.top_level

        while not (aggressor.is_filled or queue.is_empty):
            resting = queue.next_order_to_execute
            snapshot_resting = resting.snapshot()

            filled_quantity = resting.fill(aggressor.remaining_quantity)
            aggressor.fill(filled_quantity)

            filled_payload = FilledPayload(
                resting=snapshot_resting,
                filled_quantity=filled_quantity,
            )
            filled_payloads.append(filled_payload)

            if resting.is_filled:
                queue.remove_order(resting.order_id)
                del self._order_index[resting.order_id]

        if queue.is_empty:
            opposite_book_side.delete_level(opposite_book_side.best_price)

        return filled_payloads

    def modify_order(self, order_id: int, quantity: int) -> ModifiedPayload:
        """
        Reduce the resting order with `order_id` to `quantity` in place. Raises
        `OrderNotFoundError` if absent.
        """

        if order_id not in self:
            raise OrderNotFoundError(f"order {order_id} not found in orderbook")

        order = self.get_order(order_id)
        initial_snapshot = order.snapshot()
        order.reduce(quantity)
        new_snapshot = order.snapshot()
        return ModifiedPayload(initial_snapshot, new_snapshot)
