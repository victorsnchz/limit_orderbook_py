import pytest
from unittest.mock import MagicMock, patch
from lob.orderbook.modify_order import ModifyOrderExecution
from lob.orderbook.orderbook import OrderBook
from lob.orders.factory import OrderFactory
from lob.orders.order import Order, OrderSnapshot
from lob.bookkeeping.exceptions import InvalidModificationError, OrderNotFoundError
from lob.bookkeeping.custom_types import (
    Side,
    OrderType,
    ExecutionRule,
    FillStatus,
    EventKind,
    Event,
    ExecutionResult,
    ExecutionReport,
    ModifiedPayload,
    CancelledPayload,
    AcceptedPayload,
    PostedPayload,
    RejectedPayload,
)

# Patch the IMPORT SITE, not the definition module:
MAP = "lob.orderbook.modify_order.map_order_type_to_execution"


# --- fixtures -------------------------------------------------------------------------
# Mocked OrderBook + OrderFactory; make_modifier wires get_order to return a LIMIT
# order so __init__ passes.


@pytest.fixture
def orderbook():
    return MagicMock(spec=OrderBook)


@pytest.fixture
def factory():
    return MagicMock(spec=OrderFactory)


@pytest.fixture
def make_modifier(orderbook, factory):
    def _make(order=None):
        order = order or _make_limit_order()
        orderbook.get_order.return_value = order
        return ModifyOrderExecution(orderbook, order.order_id, factory)

    return _make


class TestModifyOrderExecutionInit:
    """__init__ resolves the order via get_order, stores refs, asserts LIMIT-only."""

    def test_resolves_and_stores_limit_order_from_orderbook(self, orderbook, factory):
        """get_order called once; _order/_orderbook/_factory stored."""
        order = _make_limit_order()
        orderbook.get_order.return_value = order

        ex = ModifyOrderExecution(orderbook, 1, factory)  # NOTE positional args

        orderbook.get_order.assert_called_once_with(1)
        assert ex._order is order
        assert ex._orderbook is orderbook
        assert ex._factory is factory

    def test_rejects_non_limit_order_with_assertion_error(self, orderbook, factory):
        """get_order returns a MARKET order -> AssertionError (modify is LIMIT-only)."""
        orderbook.get_order.return_value = _make_market_order()

        with pytest.raises(AssertionError):
            ModifyOrderExecution(orderbook, 1, factory)

    def test_propagates_order_not_found_from_get_order(self, orderbook, factory):
        """get_order raises OrderNotFoundError -> propagates before the LIMIT assert."""
        orderbook.get_order.side_effect = OrderNotFoundError("absent")

        with pytest.raises(OrderNotFoundError):
            ModifyOrderExecution(orderbook, 1, factory)

        orderbook.get_order.assert_called_once_with(1)


class TestModifyDispatch:
    """modify() guards both-None, validates, routes price-set -> _cancel_and_post,
    qty-only -> _modify_quantity."""

    def test_both_none_raises_before_any_collaborator(self, make_modifier):
        """modify(None, None) -> InvalidModificationError; no validate/clone/quantity calls."""
        ex = make_modifier()
        ex._validate_price = MagicMock()
        ex._validate_quantity = MagicMock()
        ex._clone_order = MagicMock()
        ex._modify_quantity = MagicMock()

        with pytest.raises(InvalidModificationError):
            ex.modify(None, None)

        ex._validate_price.assert_not_called()
        ex._validate_quantity.assert_not_called()
        ex._clone_order.assert_not_called()
        ex._modify_quantity.assert_not_called()

    def test_price_only_validates_price_skips_quantity(self, make_modifier):
        """modify(99, None) -> _validate_price(99); _validate_quantity NOT called."""
        ex = make_modifier()
        ex._validate_price = MagicMock()
        ex._validate_quantity = MagicMock()
        ex._clone_order = MagicMock()
        ex._cancel_and_post = MagicMock()

        ex.modify(99, None)

        ex._validate_price.assert_called_once_with(99)
        ex._validate_quantity.assert_not_called()

    def test_quantity_only_validates_quantity_skips_price(self, make_modifier):
        """modify(None, 60) -> _validate_quantity(60); _validate_price NOT called;
        routes _modify_quantity(60)."""
        ex = make_modifier()
        ex._validate_price = MagicMock()
        ex._validate_quantity = MagicMock()
        ex._modify_quantity = MagicMock()

        ex.modify(None, 60)

        ex._validate_quantity.assert_called_once_with(60)
        ex._validate_price.assert_not_called()
        ex._modify_quantity.assert_called_once_with(60)

    def test_both_set_validates_price_before_quantity_then_clones(self, make_modifier):
        """modify(99, 60) -> price then quantity (call_log order); routes _clone_order;
        _modify_quantity NOT called."""
        ex = make_modifier()
        call_log = []
        ex._validate_price = MagicMock(side_effect=lambda _p: call_log.append("price"))
        ex._validate_quantity = MagicMock(
            side_effect=lambda _q: call_log.append("quantity")
        )
        ex._clone_order = MagicMock()
        ex._cancel_and_post = MagicMock()
        ex._modify_quantity = MagicMock()

        ex.modify(99, 60)

        assert call_log == ["price", "quantity"]
        ex._clone_order.assert_called_once_with(new_price=99, new_quantity=60)
        ex._modify_quantity.assert_not_called()

    def test_price_branch_clones_then_returns_cancel_and_post_result(
        self, make_modifier
    ):
        """modify(99, None) -> _clone_order(new_price=99, new_quantity=None);
        returns _cancel_and_post(clone)."""
        ex = make_modifier()
        clone = object()
        sentinel = object()
        ex._clone_order = MagicMock(return_value=clone)
        ex._cancel_and_post = MagicMock(return_value=sentinel)

        result = ex.modify(99, None)

        ex._clone_order.assert_called_once_with(new_price=99, new_quantity=None)
        ex._cancel_and_post.assert_called_once_with(clone)
        assert result is sentinel

    def test_quantity_only_branch_returns_modify_quantity_result(self, make_modifier):
        """modify(None, 60) -> returns _modify_quantity(60);
        _clone_order/_cancel_and_post NOT called."""
        ex = make_modifier()
        sentinel = object()
        ex._modify_quantity = MagicMock(return_value=sentinel)
        ex._clone_order = MagicMock()
        ex._cancel_and_post = MagicMock()

        result = ex.modify(None, 60)

        assert result is sentinel
        ex._clone_order.assert_not_called()
        ex._cancel_and_post.assert_not_called()


class TestValidatePrice:
    """_validate_price rejects non-int and non-positive; accepts positive ints
    (bool leaks through)."""

    @pytest.mark.parametrize("value, type_name", [(99.0, "float"), ("99", "str")])
    def test_non_int_raises_with_type_name_in_message(
        self, make_modifier, value, type_name
    ):
        """_validate_price(99.0) -> 'new_price must be int, not float.' (trailing period)."""
        ex = make_modifier()

        with pytest.raises(
            InvalidModificationError,
            match=rf"new_price must be int, not {type_name}\.",
        ):
            ex._validate_price(value)

    @pytest.mark.parametrize("value", [0, -5])
    def test_zero_or_negative_raises_strictly_positive(self, make_modifier, value):
        """_validate_price(0) and (-5) -> 'new_price must be strictly positive.'"""
        ex = make_modifier()

        with pytest.raises(
            InvalidModificationError, match=r"new_price must be strictly positive\."
        ):
            ex._validate_price(value)

    def test_positive_int_passes_no_raise(self, make_modifier):
        """_validate_price(99) returns None."""
        assert make_modifier()._validate_price(99) is None

    def test_bool_true_leaks_through_int_guard(self, make_modifier):
        """_validate_price(True) raises nothing — documents the bool/int-subclass leak."""
        assert make_modifier()._validate_price(True) is None


class TestValidateQuantity:
    """_validate_quantity rejects non-int and non-positive; message has NO trailing
    period (asymmetry vs price)."""

    @pytest.mark.parametrize("value, type_name", [(60.0, "float"), ("60", "str")])
    def test_non_int_raises_message_without_trailing_period(
        self, make_modifier, value, type_name
    ):
        """_validate_quantity(60.0) -> 'new_quantity must be int, not float' (no period)."""
        ex = make_modifier()

        # `$` pins the end of the message: a trailing period would fail the match.
        with pytest.raises(
            InvalidModificationError,
            match=rf"new_quantity must be int, not {type_name}$",
        ):
            ex._validate_quantity(value)

    @pytest.mark.parametrize("value", [0, -3])
    def test_zero_or_negative_raises_strictly_positive(self, make_modifier, value):
        """_validate_quantity(0) and (-3) -> 'new_quantity must be strictly positive.'"""
        ex = make_modifier()

        with pytest.raises(
            InvalidModificationError, match=r"new_quantity must be strictly positive\."
        ):
            ex._validate_quantity(value)

    def test_positive_int_passes_no_raise(self, make_modifier):
        """_validate_quantity(60) returns None."""
        assert make_modifier()._validate_quantity(60) is None


class TestCloneOrder:
    """_clone_order builds via factory; price/quantity fall back to _order when the
    arg is None."""

    def test_both_none_raises_assertion_error(self, make_modifier, factory):
        """_clone_order() -> AssertionError; factory NOT called. Real regression barrier
        for the line-85 OR guard — do not drop."""
        ex = make_modifier()

        with pytest.raises(
            AssertionError, match="at least one of new_price/new_quantity must be set"
        ):
            ex._clone_order()

        factory.create_order.assert_not_called()

    def test_price_only_falls_back_to_order_remaining_quantity(
        self, make_modifier, factory
    ):
        """_clone_order(new_price=99) with remaining=50 -> create_order(quantity=50,
        limit_price=99, ...)."""
        order = _make_limit_order(limit_price=100, remaining_quantity=50)
        ex = make_modifier(order)

        ex._clone_order(new_price=99)

        factory.create_order.assert_called_once_with(
            side=order.side,
            quantity=50,
            user_id=order.user_id,
            limit_price=99,
            execution_rule=order.execution_rule,
        )

    def test_quantity_only_falls_back_to_order_limit_price(
        self, make_modifier, factory
    ):
        """_clone_order(new_quantity=80) with limit_price=100 -> create_order(quantity=80,
        limit_price=100, ...)."""
        order = _make_limit_order(limit_price=100, remaining_quantity=50)
        ex = make_modifier(order)

        ex._clone_order(new_quantity=80)

        factory.create_order.assert_called_once_with(
            side=order.side,
            quantity=80,
            user_id=order.user_id,
            limit_price=100,
            execution_rule=order.execution_rule,
        )

    def test_both_set_uses_args_no_fallback(self, make_modifier, factory):
        """_clone_order(new_price=99, new_quantity=70) -> create_order(quantity=70,
        limit_price=99); no _order fallback."""
        order = _make_limit_order(limit_price=100, remaining_quantity=50)
        ex = make_modifier(order)

        ex._clone_order(new_price=99, new_quantity=70)

        factory.create_order.assert_called_once_with(
            side=order.side,
            quantity=70,
            user_id=order.user_id,
            limit_price=99,
            execution_rule=order.execution_rule,
        )

    def test_passthrough_fields_sourced_from_order(self, make_modifier, factory):
        """create_order receives side / user_id / execution_rule from _order unchanged
        (id is the generator's job)."""
        order = _make_limit_order(
            side=Side.ASK, user_id=7, execution_rule=ExecutionRule.IOC
        )
        ex = make_modifier(order)

        ex._clone_order(new_price=99)

        _, kwargs = factory.create_order.call_args
        assert kwargs["side"] is Side.ASK
        assert kwargs["user_id"] == 7
        assert kwargs["execution_rule"] is ExecutionRule.IOC


class TestModifyQuantity:
    """_modify_quantity: equal -> raise; less -> _decrease_quantity; greater ->
    _increase_quantity."""

    def test_equal_remaining_raises_no_quantity_to_modify(self, make_modifier):
        """_modify_quantity(50) with remaining=50 -> InvalidModificationError; no
        decrease/increase."""
        ex = make_modifier(_make_limit_order(remaining_quantity=50))
        ex._decrease_quantity = MagicMock()
        ex._increase_quantity = MagicMock()

        with pytest.raises(InvalidModificationError, match="no quantity to modify"):
            ex._modify_quantity(50)

        ex._decrease_quantity.assert_not_called()
        ex._increase_quantity.assert_not_called()

    def test_less_than_remaining_routes_to_decrease(self, make_modifier):
        """_modify_quantity(40), remaining=50 -> _decrease_quantity(40);
        _increase_quantity NOT called."""
        ex = make_modifier(_make_limit_order(remaining_quantity=50))
        ex._decrease_quantity = MagicMock()
        ex._increase_quantity = MagicMock()

        ex._modify_quantity(40)

        ex._decrease_quantity.assert_called_once_with(40)
        ex._increase_quantity.assert_not_called()

    def test_greater_than_remaining_routes_to_increase(self, make_modifier):
        """_modify_quantity(80), remaining=50 -> _increase_quantity(80);
        _decrease_quantity NOT called."""
        ex = make_modifier(_make_limit_order(remaining_quantity=50))
        ex._decrease_quantity = MagicMock()
        ex._increase_quantity = MagicMock()

        ex._modify_quantity(80)

        ex._increase_quantity.assert_called_once_with(80)
        ex._decrease_quantity.assert_not_called()


class TestDecreaseQuantity:
    """_decrease_quantity: in-place orderbook.modify_order; posted/UNFILLED report;
    one MODIFIED event; no cancel."""

    def test_in_place_modify_builds_posted_unfilled_single_modified_event(
        self, make_modifier, orderbook
    ):
        """_decrease_quantity(40) -> modify_order(7, 40); report(modified_order,
        posted=True, UNFILLED); events == [Event.of(modified)] MODIFIED; no cancel."""
        ex = make_modifier(_make_limit_order(order_id=7))
        before = _make_snapshot(order_id=7, remaining_quantity=100)
        after = _make_snapshot(order_id=7, remaining_quantity=40)
        modified = ModifiedPayload(before, after)
        orderbook.modify_order.return_value = modified

        result = ex._decrease_quantity(40)

        orderbook.modify_order.assert_called_once_with(7, 40)
        assert result.report.aggressor is after
        assert result.report.posted is True
        assert result.report.status is FillStatus.UNFILLED
        assert len(result.events) == 1
        assert result.events[0].kind is EventKind.MODIFIED
        assert result.events[0].payload is modified
        orderbook.cancel_order.assert_not_called()


class TestIncreaseQuantity:
    """_increase_quantity clones at the new quantity (price defaults None inside clone)
    then defers to _cancel_and_post."""

    def test_clones_at_new_quantity_then_cancel_and_posts(self, make_modifier):
        """_increase_quantity(80) -> _clone_order(new_quantity=80);
        returns _cancel_and_post(clone)."""
        ex = make_modifier()
        clone = object()
        sentinel = object()
        ex._clone_order = MagicMock(return_value=clone)
        ex._cancel_and_post = MagicMock(return_value=sentinel)

        result = ex._increase_quantity(80)

        ex._clone_order.assert_called_once_with(new_quantity=80)
        ex._cancel_and_post.assert_called_once_with(clone)
        assert result is sentinel


class TestCancelAndPost:
    """_cancel_and_post: rejected -> return unchanged, no cancel; accepted -> cancel
    original LAST, prepend CANCELLED first. Inject a fake executor via
    patch.dict(MAP, {OrderType.LIMIT: <fake>})."""

    def test_rejected_result_returns_unchanged_without_cancelling(
        self, make_modifier, orderbook
    ):
        """is_rejected result -> returned verbatim; cancel_order NOT called; no CANCELLED
        prepended. (Closes the gap the integration rejected-test leaves open.)"""
        ex = make_modifier()
        rejected = ExecutionResult(
            report=_make_report(),
            events=[Event.of(RejectedPayload(_make_snapshot(), "dup"))],
        )
        fake_exec = MagicMock()
        fake_exec.execute.return_value = rejected

        with patch.dict(MAP, {OrderType.LIMIT: MagicMock(return_value=fake_exec)}):
            result = ex._cancel_and_post(_make_limit_order(order_id=2))

        assert result is rejected
        orderbook.cancel_order.assert_not_called()
        assert not any(e.kind is EventKind.CANCELLED for e in result.events)

    def test_accepted_cancels_after_execute_and_prepends_cancelled_event(
        self, make_modifier, orderbook
    ):
        """non-rejected -> execute() BEFORE cancel_order(order_id) (call_log);
        events == [CANCELLED] + replacement.events."""
        ex = make_modifier(_make_limit_order(order_id=1))
        replacement = ExecutionResult(
            report=_make_report(),
            events=[
                Event.of(AcceptedPayload(_make_snapshot())),
                Event.of(PostedPayload(_make_snapshot())),
            ],
        )
        cancelled = CancelledPayload(_make_snapshot())
        call_log = []

        def fake_execute():
            call_log.append("execute")
            return replacement

        def fake_cancel(_order_id):
            call_log.append("cancel")
            return cancelled

        fake_exec = MagicMock()
        fake_exec.execute.side_effect = fake_execute
        orderbook.cancel_order.side_effect = fake_cancel

        with patch.dict(MAP, {OrderType.LIMIT: MagicMock(return_value=fake_exec)}):
            result = ex._cancel_and_post(_make_limit_order(order_id=2))

        assert call_log == ["execute", "cancel"]
        orderbook.cancel_order.assert_called_once_with(1)
        assert result.events == [Event.of(cancelled)] + replacement.events

    def test_accepted_report_is_replacement_report_not_rebuilt(
        self, make_modifier, orderbook
    ):
        """accepted path -> returned result.report IS the replacement's report
        (passed through, not rebuilt)."""
        ex = make_modifier()
        report = _make_report()
        replacement = ExecutionResult(
            report=report, events=[Event.of(AcceptedPayload(_make_snapshot()))]
        )
        fake_exec = MagicMock()
        fake_exec.execute.return_value = replacement
        orderbook.cancel_order.return_value = CancelledPayload(_make_snapshot())

        with patch.dict(MAP, {OrderType.LIMIT: MagicMock(return_value=fake_exec)}):
            result = ex._cancel_and_post(_make_limit_order(order_id=2))

        assert result.report is report


# --- module-level helpers (extend the test_order_execution.py versions) ---------------
# _make_limit_order / _make_market_order ALSO set .user_id and .execution_rule
# (the _clone_order passthrough reads them). _make_snapshot reuses that module's version.


def _make_limit_order(
    order_id=1,
    side: Side = Side.BID,
    limit_price: int = 100,
    initial_quantity: int = 100,
    remaining_quantity: int = 100,
    is_filled: bool = False,
    user_id: int = 0,
    execution_rule: ExecutionRule = ExecutionRule.GTC,
):
    order = MagicMock(spec=Order)
    order.order_id = order_id
    order.side = side
    order.order_type = OrderType.LIMIT
    order.limit_price = limit_price
    order.initial_quantity = initial_quantity
    order.remaining_quantity = remaining_quantity
    order.is_filled = is_filled
    order.user_id = user_id
    order.execution_rule = execution_rule
    return order


def _make_market_order(
    order_id=1,
    side: Side = Side.BID,
    initial_quantity: int = 100,
    remaining_quantity: int = 100,
    is_filled: bool = False,
    user_id: int = 0,
    execution_rule: ExecutionRule | None = None,
):
    order = MagicMock(spec=Order)
    order.order_id = order_id
    order.side = side
    order.order_type = OrderType.MARKET
    order.initial_quantity = initial_quantity
    order.remaining_quantity = remaining_quantity
    order.is_filled = is_filled
    order.user_id = user_id
    order.execution_rule = execution_rule
    return order


def _make_snapshot(
    side: Side = Side.BID,
    order_type: OrderType = OrderType.LIMIT,
    initial_quantity: int = 100,
    remaining_quantity: int = 100,
    order_id: int = 1,
    user_id: int = 0,
    limit_price: int = 100,
):
    return OrderSnapshot(
        side=side,
        order_type=order_type,
        initial_quantity=initial_quantity,
        remaining_quantity=remaining_quantity,
        order_id=order_id,
        user_id=user_id,
        limit_price=limit_price,
    )


def _make_report(
    aggressor=None,
    posted: bool = True,
    status: FillStatus = FillStatus.UNFILLED,
):
    return ExecutionReport(
        aggressor=aggressor if aggressor is not None else _make_snapshot(),
        posted=posted,
        status=status,
    )
