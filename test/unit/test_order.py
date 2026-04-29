import unittest
import sys

# TODO
# fix import system accross package
# seems like test_order called first, appends src to path then subsequent test modules can test src
# individual test module will fail import otherwise
sys.path.append("src")

from src.orders.order import Order, OrderSpec, OrderID
from src.bookkeeping.custom_types import OrderType, Side, ExecutionRule


class TestOrderConstruction(unittest.TestCase):
    """Initial state and field accessors after `Order(spec, id)`."""

    def test_remaining_equals_initial_on_init(self):
        specs = OrderSpec(
            side=Side.BID,
            order_type=OrderType.LIMIT,
            quantity=100,
            execution_rule=ExecutionRule.GTC,
            limit_price=100,
        )
        id = OrderID(0, 0)
        order = Order(specs, id)
        self.assertEqual(order.remaining_quantity, order.initial_quantity)

    def test_is_filled_false_on_init(self):
        specs = OrderSpec(
            side=Side.BID,
            order_type=OrderType.LIMIT,
            quantity=100,
            execution_rule=ExecutionRule.GTC,
            limit_price=100,
        )
        id = OrderID(0, 0)
        order = Order(specs, id)
        self.assertFalse(order.is_filled)

    def test_limit_price_accessible(self):
        specs = OrderSpec(
            side=Side.BID,
            order_type=OrderType.LIMIT,
            quantity=100,
            execution_rule=ExecutionRule.GTC,
            limit_price=100,
        )
        id = OrderID(0, 0)
        order = Order(specs, id)
        self.assertEqual(order.limit_price, 100)

    def test_side_accessible(self):
        specs = OrderSpec(
            side=Side.BID,
            order_type=OrderType.LIMIT,
            quantity=100,
            execution_rule=ExecutionRule.GTC,
            limit_price=100,
        )
        id = OrderID(0, 0)
        order = Order(specs, id)
        self.assertEqual(order.side, Side.BID)

    def test_order_type_accessible(self):
        specs = OrderSpec(
            side=Side.BID,
            order_type=OrderType.LIMIT,
            quantity=100,
            execution_rule=ExecutionRule.GTC,
            limit_price=100,
        )
        id = OrderID(0, 0)
        order = Order(specs, id)
        self.assertEqual(order.order_type, OrderType.LIMIT)

    def test_execution_rule_accessible(self):
        specs = OrderSpec(
            side=Side.BID,
            order_type=OrderType.LIMIT,
            quantity=100,
            execution_rule=ExecutionRule.GTC,
            limit_price=100,
        )
        id = OrderID(0, 0)
        order = Order(specs, id)
        self.assertEqual(order.execution_rule, ExecutionRule.GTC)

    def test_market_order_has_no_limit_price(self):
        specs = OrderSpec(side=Side.BID, order_type=OrderType.MARKET, quantity=100)
        id = OrderID(0, 0)
        order = Order(specs, id)
        self.assertIsNone(order.limit_price)

    def test_market_order_has_no_execution_rule(self):
        specs = OrderSpec(side=Side.BID, order_type=OrderType.MARKET, quantity=100)
        id = OrderID(0, 0)
        order = Order(specs, id)
        self.assertIsNone(order.execution_rule)


class TestOrderFill(unittest.TestCase):
    """`fill(qty)`: clamps to remaining, returns filled amount, flips `is_filled`."""

    def setUp(self):
        specs = OrderSpec(
            side=Side.BID,
            order_type=OrderType.LIMIT,
            quantity=100,
            execution_rule=ExecutionRule.GTC,
            limit_price=100,
        )
        id = OrderID(0, 0)
        self.order = Order(specs, id)

    def test_partial_fill_reduces_remaining(self):
        self.order.fill(50)
        self.assertLess(self.order.remaining_quantity, self.order.initial_quantity)

    def test_partial_fill_is_not_filled(self):
        self.order.fill(50)
        self.assertFalse(self.order.is_filled)

    def test_partial_fill_returns_filled_quantity(self):
        self.assertEqual(self.order.fill(50), 50)

    def test_full_fill_sets_remaining_to_zero(self):
        self.order.fill(100)
        self.assertEqual(self.order.remaining_quantity, 0)

    def test_full_fill_is_filled_true(self):
        self.order.fill(100)
        self.assertTrue(self.order.is_filled)

    def test_overfill_clamps_to_zero(self):
        self.order.fill(1000)
        self.assertEqual(self.order.remaining_quantity, 0)

    def test_overfill_is_filled_true(self):
        self.order.fill(1000)
        self.assertTrue(self.order.is_filled)

    def test_fill_zero_has_no_effect(self):
        self.order.fill(0)
        self.assertEqual(self.order.initial_quantity, self.order.remaining_quantity)

    def test_fill_zero_returns_zero(self):
        self.assertEqual(self.order.fill(0), 0)


class TestOrderReduce(unittest.TestCase):
    """`reduce(qty)`: must strictly shrink remaining, else raises."""

    def setUp(self):
        specs = OrderSpec(
            side=Side.BID,
            order_type=OrderType.LIMIT,
            quantity=100,
            execution_rule=ExecutionRule.GTC,
            limit_price=100,
        )
        id = OrderID(0, 0)
        self.order = Order(specs, id)

    def test_reduce_updates_remaining(self):
        self.order.reduce(50)
        self.assertEqual(self.order.remaining_quantity, 50)

    def test_reduce_to_larger_value_raises(self):
        with self.assertRaises(ValueError):
            self.order.reduce(1000)

    def test_reduce_to_equal_value_raises(self):
        with self.assertRaises(ValueError):
            self.order.reduce(100)


class TestOrderSpec(unittest.TestCase):
    """`OrderSpec` construction-time validation."""

    def test_limit_order_no_limit_price_raises(self):
        with self.assertRaises(ValueError):
            OrderSpec(
                Side.BID,
                OrderType.LIMIT,
                quantity=100,
                limit_price=None,
                execution_rule=ExecutionRule.GTC,
            )


class TestSnapshot(unittest.TestCase):
    """`Order.snapshot()`: immutable point-in-time copy, no aliasing."""

    def setUp(self):

        self.spec = OrderSpec(
            Side.BID,
            OrderType.LIMIT,
            quantity=100,
            limit_price=100,
            execution_rule=ExecutionRule.GTC,
        )

        self.order = Order(self.spec, OrderID(0, 0))

    def test_snapshot_reflects_initial_state(self):
        snap = self.order.snapshot()
        self.assertEqual(snap.side, self.order.side)
        self.assertEqual(snap.order_type, self.order.order_type)
        self.assertEqual(snap.initial_quantity, self.order.initial_quantity)
        self.assertEqual(snap.remaining_quantity, self.order.remaining_quantity)
        self.assertEqual(snap.order_id, self.order.order_id)
        self.assertEqual(snap.user_id, self.order.user_id)
        self.assertEqual(snap.limit_price, self.order.limit_price)
        self.assertEqual(snap.execution_rule, self.order.execution_rule)

    def test_snapshot_reflects_state_after_fill(self):
        self.order.fill(40)
        snap = self.order.snapshot()
        self.assertEqual(snap.remaining_quantity, self.order.remaining_quantity)
        self.assertEqual(snap.initial_quantity, self.order.initial_quantity)

    def test_snapshot_is_immutable(self):
        snap = self.order.snapshot()
        with self.assertRaises(Exception):
            snap.remaining_quantity = 0

    def test_snapshot_does_not_alias_order(self):
        snap = self.order.snapshot()
        self.order.fill(40)
        self.assertEqual(snap.remaining_quantity, self.order.remaining_quantity + 40)


if __name__ == "__main__":
    unittest.main()
