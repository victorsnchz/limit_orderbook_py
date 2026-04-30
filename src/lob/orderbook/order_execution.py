from lob.orders.order import Order
from lob.orderbook.orderbook import OrderBook
from lob.orderbook.book_side import BookSide
from lob.bookkeeping.custom_types import (
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
    Validate, match, and report on a single aggressor order against the book.
    Subclasses define order-type-specific validation and post-match disposition.
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
        """
        Run shared sanity checks then defer to `_validate_type_specific`.
        """

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
        """
        Validate, then either record the rejection or run `_do_execute`. Always
        produces an `ExecutionResult`, also cached for `get_execution_result`.
        """

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
        """
        Whether the aggressor would cross the opposite top.
        Passes `None` to `Order.can_cross` when the opposite side is empty.
        """
        best_price = (
            None
            if self._opposite_book_side.is_empty
            else self._opposite_book_side.best_price
        )
        return self.order.can_cross(best_price)

    def _match(self) -> None:
        """
        Drive `fill_top` across price levels until the aggressor fills or the
        opposite side stops crossing, recording one FILLED event per touched resting.
        """

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
        """
        Snapshot the aggressor and freeze the recorded events into `_execution_result`.
        """
        report = ExecutionReport(
            aggressor=self.order.snapshot(),
            posted=self._posted,
            status=self._compute_status(),
        )

        self._execution_result = ExecutionResult(
            report=report, events=list(self._events)
        )

    def get_execution_result(self) -> ExecutionResult:
        """
        Return the cached result. Raises `RuntimeError` if `execute` has not run.
        """
        if self._execution_result is None:
            raise RuntimeError(
                "must first call 'execute()' prior to get_execution_result"
            )
        return self._execution_result


class LimitOrderExecution(OrderExecution):
    """
    Match against the opposite side, then post any residual to the book.
    """

    def _do_execute(self) -> None:

        self._match()
        if not self.order.is_filled:
            self.orderbook.post_order(self.order)

            self._record_posted()

    def _validate_type_specific(self) -> AcceptedPayload | RejectedPayload:
        """
        Reject if the limit price is missing or non-positive.
        """
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
    Match against the opposite side; never posts residual.
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
    """
    Run `order` through the executor matching its `order_type` and return the result.
    """
    executor = map_order_type_to_execution[order.order_type](order, orderbook)
    return executor.execute()
