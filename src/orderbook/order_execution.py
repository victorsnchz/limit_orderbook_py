from src.orders.order import Order
from src.orderbook.orderbook import OrderBook
from src.orderbook.book_side import BookSide
from src.bookkeeping.custom_types import (
    OrderType,
    Event,
    ExecutionResult,
    FillStatus,
    PostedPayload,
    AcceptedPayload,
    RejectedPayload,
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
        self._opposite_book_side: BookSide = self.orderbook.get_opposite_book_side(
            self.order.side
        )
        self._events: list[Event] = []
        self._posted: bool = False
        self._execution_result: None | ExecutionResult = None

    def _validate_order(self) -> AcceptedPayload | RejectedPayload:

        if self.order.order_id in self.orderbook:
            return RejectedPayload(self.order.snapshot(), "duplicate order id")
        if self.order.initial_quantity <= 0:
            return RejectedPayload(self.order.snapshot(), "non-positive quantity")
        if self.order.is_filled:
            return RejectedPayload(self.order.snapshot(), "order already filled")
        return self._validate_type_specific()

    @abstractmethod
    def _validate_type_specific(self) -> AcceptedPayload | RejectedPayload: ...

    def execute(self) -> ExecutionResult:

        validation_payload = self._validate_order()

        if isinstance(validation_payload, RejectedPayload):
            self._record_rejected(validation_payload)
            self._build_result()

        else:
            self._record_accepted(validation_payload)
            self._do_execute()
            self._build_result()
        return self._execution_result

    @abstractmethod
    def _do_execute(self): ...

    def _can_match_order(self) -> bool:
        # if opposite side empty will pass a None price to order.can_cross()
        # may have to review this logic, not obvious at first read
        best_price = (
            None
            if self._opposite_book_side.is_empty
            else self._opposite_book_side.best_price
        )
        return self.order.can_cross(best_price)

    def _match(self) -> None:

        while not self.order.is_filled and self._can_match_order():
            payloads = self.orderbook.fill_top(self.order)
            for payload in payloads:
                self._events.append(Event(kind=EventKind.FILLED, payload=payload))

    def _record_rejected(self, payload: RejectedPayload) -> None:
        kind = EventKind.REJECTED
        self._events.append(Event(kind=kind, payload=payload))

    def _record_accepted(self, payload: AcceptedPayload) -> None:
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
            aggressor=self.order.snapshot(),
            posted=self._posted,
            status=self._compute_status(),
        )

        self._execution_result = ExecutionResult(
            report=report, events=list(self._events)
        )

    def get_execution_result(self) -> ExecutionResult:
        if self._execution_result is None:
            raise RuntimeError(
                "must first call 'execute()' prior to get_execution_result"
            )
        return self._execution_result


class LimitOrderExecution(OrderExecution):
    """
    Execute limit orders in order book.
    If possible will match order against opposite side orders.. Remaining will be posted in book.
    """

    def _do_execute(self) -> None:

        self._match()
        if not self.order.is_filled:
            self.orderbook.post_order(self.order)

            self._record_posted()

    def _validate_type_specific(self) -> AcceptedPayload | RejectedPayload:
        if self.order.limit_price is None:
            return RejectedPayload(
                self.order.snapshot(), "limit order missing limit price"
            )
        if self.order.limit_price <= 0:
            return RejectedPayload(self.order.snapshot(), "non-positive limit price")
        # backlog - check type?
        return AcceptedPayload(self.order.snapshot())


class MarketOrderExecution(OrderExecution):
    """
    Execute market orders in order book.
    If possible will match order against opposite side.
    """

    def _do_execute(self) -> None:
        self._match()

    def _validate_type_specific(self) -> AcceptedPayload:
        return AcceptedPayload(self.order.snapshot())


map_order_type_to_execution = {
    OrderType.LIMIT: LimitOrderExecution,
    OrderType.MARKET: MarketOrderExecution,
}


def execute_order(order: Order, orderbook: OrderBook) -> ExecutionResult:
    executor = map_order_type_to_execution[order.order_type](order, orderbook)
    return executor.execute()
