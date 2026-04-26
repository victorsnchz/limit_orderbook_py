from src.orders.order import Order
from src.orderbook.orderbook import OrderBook
from src.orderbook.book_side import BookSide
from src.bookkeeping.custom_types import (
    OrderType,
    FilledPayload,
    Event,
    ExecutionResult,
    FillStatus,
    PostedPayload,
    AcceptedPayload,
    EventKind,
    ExecutionReport,
)

from abc import ABC, abstractmethod


class OrderExecution(ABC):
    """
    Parent class for order execution.
    """

    def __init__(self, order: Order, orderbook: OrderBook):
        self.order: Order = order
        self.orderbook: OrderBook = orderbook
        self._filled_payloads = [FilledPayload]
        self._events: list[Event]
        self._posted: bool = False

    @abstractmethod
    def execute(self) -> ExecutionResult:
        pass

    def _get_side(self) -> BookSide:
        return self.orderbook.get_book_side(self.order.side)

    def _get_opposite_side(self) -> BookSide:
        return self.orderbook.get_opposite_book_side(self.order.side)

    def _can_match_order(self) -> bool:
        # if opposite side empty will pass a None price to order.can_cross()
        # may have to review this logic, not obvious at first read
        opposite_side = self.orderbook.get_opposite_book_side(self.order.side)
        best_price = None if opposite_side.is_empty else opposite_side.best_price
        return self.order.can_cross(best_price)

    def _match(self) -> list[Event]:
        filled_payloads = []
        while not self.order.is_filled and self._can_match_order():
            filled_payloads += self.orderbook.fill_top(self.order)

        return [Event(EventKind.FILLED, payload) for payload in filled_payloads]

    def _record_accepted(self) -> None:
        payload = AcceptedPayload(self.order.snapshot())
        kind = EventKind.ACCEPTED
        self._events.append(Event(kind=kind, payload=payload))

    def _record_posted(self) -> None:
        payload = PostedPayload(self.order.snapshot())
        kind = EventKind.POSTED
        self._events.append(Event(kind=kind, payload=payload))
        self._posted = True

    def _compute_status(self) -> FillStatus:
        if self.order.is_filled:
            return FillStatus.FILLED
        if self.order.initial_quantity == self.order.remaining_quantity:
            return FillStatus.UNFILLED
        return FillStatus.PARTIALLY_FILLED

    def _build_result(self) -> None:
        report = ExecutionReport(
            aggresssor=self.order.snapshot(),
            fills=self._filled_payloads,
            posted=self._posted,
            status=self._compute_status(),
        )

        return ExecutionResult(report=report, events=self._events)


class LimitOrderExecution(OrderExecution):
    """
    Execute limit orders in order book.
    If possible will match order against opposite side orders.. Remaining will be posted in book.
    """

    def __init__(self, order: Order, orderbook):
        super().__init__(order, orderbook)

    def execute(self) -> ExecutionResult:

        self._match()
        if not self.order.is_filled:
            self.orderbook.post_order(self.order)


class MarketOrderExecution(OrderExecution):
    """
    Execute market orders in order book.
    If possible will match order against opposite side.
    """

    def __init__(self, order: Order, orderbook):
        super().__init__(order, orderbook)

    def execute(self) -> ExecutionResult:
        self._match()


map_order_type_to_execution = {
    OrderType.LIMIT: LimitOrderExecution,
    OrderType.MARKET: MarketOrderExecution,
}


def execute_order(order: Order, orderbook: OrderBook) -> None:
    executor = map_order_type_to_execution[order.order_type](order, orderbook)
    executor.execute()
