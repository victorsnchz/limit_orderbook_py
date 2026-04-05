import unittest

from src.orders.factory import (
    OrderFactory,
    LimitOrderFactory,
    MarketOrderFactory,
    map_type_to_factory,
)
from src.orders.order import Order
from src.bookkeeping.custom_types import ExecutionRule, Side, OrderType
from src.orders.order_id_generator import OrderIdGenerator


class TestLimitOrderFactory(unittest.TestCase):
    def setUp(self):
        self.generator = OrderIdGenerator()
        self.factory = LimitOrderFactory(self.generator)

    def test_creates_order_with_correct_side(self):
        order = self.factory.create_order(
            side=Side.BID,
            quantity=100,
            user_id=1,
            limit_price=99,
            execution_rule=ExecutionRule.GTC,
        )
        self.assertEqual(order.side, Side.BID)

    def test_creates_order_with_correct_quantity(self):
        order = self.factory.create_order(
            side=Side.BID,
            quantity=100,
            user_id=1,
            limit_price=99,
            execution_rule=ExecutionRule.GTC,
        )
        self.assertEqual(order.initial_quantity, 100)

    def test_creates_order_with_correct_limit_price(self):
        order = self.factory.create_order(
            side=Side.BID,
            quantity=100,
            user_id=1,
            limit_price=99,
            execution_rule=ExecutionRule.GTC,
        )
        self.assertEqual(order.limit_price, 99)

    def test_creates_order_with_correct_execution_rule(self):
        order = self.factory.create_order(
            side=Side.BID,
            quantity=100,
            user_id=1,
            limit_price=99,
            execution_rule=ExecutionRule.GTC,
        )
        self.assertEqual(order.execution_rule, ExecutionRule.GTC)

    def test_order_id_assigned_from_generator(self):
        order = self.factory.create_order(
            side=Side.BID,
            quantity=100,
            user_id=1,
            limit_price=99,
            execution_rule=ExecutionRule.GTC,
        )
        self.assertEqual(order.order_id, 1)


class TestMarketOrderFactory(unittest.TestCase):
    def setUp(self):
        generator = OrderIdGenerator()
        self.factory = MarketOrderFactory(generator)

    def test_creates_order_with_correct_side(self):
        order = self.factory.create_order(
            side=Side.BID,
            quantity=100,
            user_id=1,
        )
        self.assertEqual(order.side, Side.BID)

    def test_creates_order_with_correct_quantity(self):
        order = self.factory.create_order(
            side=Side.BID,
            quantity=100,
            user_id=1,
        )
        self.assertEqual(order.initial_quantity, 100)

    def test_market_order_has_no_limit_price(self):
        order = self.factory.create_order(
            side=Side.BID,
            quantity=100,
            user_id=1,
        )
        self.assertIsNone(order.limit_price)

    def test_market_order_has_no_execution_rule(self):
        order = self.factory.create_order(
            side=Side.BID,
            quantity=100,
            user_id=1,
        )
        self.assertIsNone(order.execution_rule)

    def test_order_id_assigned_from_generator(self):
        order = self.factory.create_order(
            side=Side.BID,
            quantity=100,
            user_id=1,
        )
        self.assertEqual(order.order_id, 1)


class TestFactoriesShareGenerator(unittest.TestCase):
    def setUp(self):
        self.generator = OrderIdGenerator()
        self.limit_factory = LimitOrderFactory(self.generator)
        self.market_factory = MarketOrderFactory(self.generator)

    def test_limit_and_market_ids_do_not_collide(self):
        limit_order = self.limit_factory.create_order(
            Side.BID, 100, 1, 99, ExecutionRule.GTC
        )
        market_order = self.market_factory.create_order(Side.BID, 100, 1)
        self.assertNotEqual(limit_order.order_id, market_order.order_id)


class TestFactoryMap(unittest.TestCase):
    def setUp(self):
        self.generator = OrderIdGenerator()

    def test_limit_key_returns_limit_factory(self):
        factory = map_type_to_factory[OrderType.LIMIT](self.generator)
        self.assertIsInstance(factory, LimitOrderFactory)

    def test_marekt_key_returns_market_factory(self):
        factory = map_type_to_factory[OrderType.MARKET](self.generator)
        self.assertIsInstance(factory, MarketOrderFactory)
