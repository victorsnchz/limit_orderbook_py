from lob.orders.factory import OrderFactory
from lob.orders.order import Order
from lob.orderbook.order_execution import map_order_type_to_execution
from lob.orderbook.orderbook import OrderBook
from lob.bookkeeping.custom_types import (
    Event,
    ExecutionReport,
    ExecutionResult,
    FillStatus,
    OrderType,
)
from lob.bookkeeping.exceptions import InvalidModificationError


class ModifyOrderExecution:
    """
    Modify policy (D12): size-down keeps queue priority via an in-place book
    transition; any other change is cancel-and-repost. Every branch returns a
    single `ExecutionResult` (D10/D14), so a modify reads like any other
    execution and its transitions land in one event stream.
    """

    def __init__(self, orderbook: OrderBook, order_id: int, factory: OrderFactory):

        self._orderbook = orderbook
        self._order = self._orderbook.get_order(order_id)
        assert self._order.order_type is OrderType.LIMIT, (
            "modify is only defined for resting LIMIT orders"
        )
        self._factory = factory

    # ==================================================================================
    # Interface (public methods)
    # ==================================================================================

    def modify(
        self, new_price: int | None, new_quantity: int | None
    ) -> ExecutionResult:

        if new_price is None and new_quantity is None:
            raise InvalidModificationError(
                "nothing to modify: both new_price and new_quantity are None"
            )

        if new_price is not None:
            self._validate_price(new_price)

        if new_quantity is not None:
            self._validate_quantity(new_quantity)

        # Consider de-coupling the case new_price not None AND new_quantity not None
        # for readability and maintainability
        if new_price is not None:
            new_order = self._clone_order(
                new_price=new_price, new_quantity=new_quantity
            )
            return self._cancel_and_post(new_order)

        return self._modify_quantity(new_quantity)

    # ==================================================================================
    # Private methods
    # ==================================================================================

    def _validate_price(self, price: int):
        if not isinstance(price, int):
            raise InvalidModificationError(
                f"new_price must be int, not {type(price).__name__}."
            )
        if price <= 0:
            raise InvalidModificationError("new_price must be strictly positive.")

    def _validate_quantity(self, quantity: int):
        if not isinstance(quantity, int):
            raise InvalidModificationError(
                f"new_quantity must be int, not {type(quantity).__name__}"
            )
        if quantity <= 0:
            raise InvalidModificationError("new_quantity must be strictly positive.")

    def _clone_order(
        self, new_price: int | None = None, new_quantity: int | None = None
    ) -> Order:

        assert new_price is not None or new_quantity is not None, (
            "at least one of new_price/new_quantity must be set"
        )

        price_in = new_price if new_price is not None else self._order.limit_price
        quantity_in = (
            new_quantity if new_quantity is not None else self._order.remaining_quantity
        )

        new_order = self._factory.create_order(
            side=self._order.side,
            quantity=quantity_in,
            user_id=self._order.user_id,
            limit_price=price_in,
            execution_rule=self._order.execution_rule,
        )

        return new_order

    def _cancel_and_post(self, new_order: Order) -> ExecutionResult:
        order_exec = map_order_type_to_execution[new_order.order_type](
            new_order, self._orderbook
        )
        execution_result = order_exec.execute()

        if execution_result.is_rejected:
            # Replacement rejected: leave the original resting. The REJECTED
            # event is the whole story; nothing was cancelled.
            return execution_result

        # Cancel the original LAST so a rejected replacement never loses the
        # order, but narrate it FIRST: the old order leaves, then the new one
        # is accepted/matched/posted. The prepend reorders frozen payloads only.
        cancelled = self._orderbook.cancel_order(self._order.order_id)
        return ExecutionResult(
            report=execution_result.report,
            events=[Event.of(cancelled)] + execution_result.events,
        )

    def _modify_quantity(self, quantity: int) -> ExecutionResult:

        if quantity == self._order.remaining_quantity:
            raise InvalidModificationError("no quantity to modify")

        if quantity < self._order.remaining_quantity:
            return self._decrease_quantity(quantity)

        return self._increase_quantity(quantity)

    def _decrease_quantity(self, quantity: int) -> ExecutionResult:
        # Size-down keeps queue priority: an in-place book transition, no fill.
        modified = self._orderbook.modify_order(self._order.order_id, quantity)
        report = ExecutionReport(
            aggressor=modified.modified_order,
            posted=True,
            status=FillStatus.UNFILLED,
        )
        return ExecutionResult(report=report, events=[Event.of(modified)])

    def _increase_quantity(self, quantity: int) -> ExecutionResult:
        new_order = self._clone_order(new_quantity=quantity)
        return self._cancel_and_post(new_order)
