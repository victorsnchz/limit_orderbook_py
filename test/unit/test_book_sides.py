import unittest
from unittest.mock import MagicMock, patch

from src.orderbook.book_side import BookSide, BidSide, AskSide
from src.orders.order import OrderID, Order, OrderSpec
from src.bookkeeping.custom_types import OrderType, ExecutionRule, Side
from src.orderbook.orders_queue import OrdersQueue
from src.bookkeeping.exceptions import EmptyBookSideError, PriceLevelNotFoundError


# ======================================================================================
# Base classes
# ======================================================================================
class BookSideTestBase(unittest.TestCase):
    """
    Tests for shared BookSide behaviour.
    Subclassed by TestBidSide and TestAskSide where behaviour diverges.
    """

    def get_book_side(self) -> BookSide:
        raise NotImplementedError("subclass must return a BookSide instance")

    def setUp(self):
        patcher = patch("src.orderbook.book_side.OrdersQueue")
        self.MockQueueCls = patcher.start()
        self.addCleanup(patcher.stop)

        self._queues_created = []

        def _factory():
            q = MagicMock(spec=OrdersQueue)
            self._queues_created.append(q)
            return q

        self.MockQueueCls.side_effect = _factory
        self.side = self.get_book_side()

    def make_order(
        self,
        order_id=1,
        limit_price=99,
        user_id=1,
        remaining_quantity=100,
        initial_quantity: int = 100,
    ):
        order = MagicMock()
        order.order_id = order_id
        order.limit_price = limit_price
        order.user_id = user_id
        order.remaining_quantity = remaining_quantity
        order.initial_quantity = initial_quantity
        return order

    def queue_at(self, price: int) -> MagicMock:
        return self.side.get_level(price)


class BookSideInvariants:
    side: BookSide

    def test_is_empty_on_init(self):
        self.assertTrue(self.side.is_empty)

    def test_is_empty_false_after_post(self):
        self.side.post_order(self.make_order())
        self.assertFalse(self.side.is_empty)

    def test_prices_empty_on_init(self):
        self.assertEqual(list(self.side.prices), [])

    def test_prices_reflect_posted_levels(self):
        self.side.post_order(self.make_order(order_id=1, limit_price=99))
        self.side.post_order(self.make_order(order_id=2, limit_price=100))
        self.assertEqual(set(self.side.prices), {99, 100})


class BookSideCRUD:
    side: BookSide

    def test_post_order_creates_queue_for_new_price(self):
        order = self.make_order(limit_price=99)
        self.side.post_order(order)

        self.MockQueueCls.assert_called_once()
        self.queue_at(99).add_order.assert_called_once_with(order)

    def test_post_order_reuses_queue_for_existing_price(self):
        order1 = self.make_order(order_id=1, limit_price=99)
        order2 = self.make_order(order_id=2, limit_price=99)

        self.side.post_order(order1)
        self.side.post_order(order2)

        # Only one queue was constructed despite two posts at the same price.
        self.assertEqual(self.MockQueueCls.call_count, 1)

        queue = self.queue_at(99)
        self.assertEqual(queue.add_order.call_count, 2)
        queue.add_order.assert_any_call(order1)
        queue.add_order.assert_any_call(order2)

    def test_post_order_at_distinct_prices_creates_distinct_queues(self):
        self.side.post_order(self.make_order(order_id=1, limit_price=99))
        self.side.post_order(self.make_order(order_id=2, limit_price=100))

        self.assertEqual(self.MockQueueCls.call_count, 2)
        self.assertIsNot(self.queue_at(99), self.queue_at(100))

    def test_delete_level_removes_it(self):
        self.side.post_order(self.make_order(limit_price=99))
        self.side.delete_level(99)
        self.assertTrue(self.side.is_empty)
        self.assertNotIn(99, self.side.prices)

    def test_get_level_returns_queue_at_price(self):
        order = self.make_order(limit_price=99)
        self.side.post_order(order)

        # The queue returned must be the same instance add_order was called on.
        returned = self.side.get_level(99)
        returned.add_order.assert_called_once_with(order)

    def test_get_order_delegates_to_level(self):
        order = self.make_order(order_id=42, limit_price=99)
        self.side.post_order(order)

        queue = self.queue_at(99)
        queue.get_order.return_value = order

        self.assertIs(self.side.get_order(99, 42), order)
        queue.get_order.assert_called_once_with(42)

    def test_is_level_empty_delegates_to_queue(self):
        self.side.post_order(self.make_order(limit_price=99))
        self.queue_at(99).is_empty = True
        self.assertTrue(self.side.is_level_empty(99))


class BookSideSnapshot:
    side: BookSide

    def test_get_states_keys_each_queue_by_its_price(self):
        self.side.post_order(self.make_order(order_id=1, limit_price=99))
        self.side.post_order(self.make_order(order_id=2, limit_price=100))

        self.queue_at(99).get_state.return_value = "STATE_99"
        self.queue_at(100).get_state.return_value = "STATE_100"

        self.assertEqual(
            self.side.get_states(),
            {99: "STATE_99", 100: "STATE_100"},
        )

    def test_get_states_delegates_once_per_level(self):
        self.side.post_order(self.make_order(order_id=1, limit_price=99))
        self.side.post_order(self.make_order(order_id=2, limit_price=100))

        _ = self.side.get_states()

        self.queue_at(99).get_state.assert_called_once()
        self.queue_at(100).get_state.assert_called_once()

    def test_get_volumes_keys_each_queue_by_its_price(self):
        self.side.post_order(self.make_order(order_id=1, limit_price=99))
        self.side.post_order(self.make_order(order_id=2, limit_price=100))

        self.queue_at(99).get_volume.return_value = 100
        self.queue_at(100).get_volume.return_value = 250

        volumes = self.side.get_volumes()
        self.assertEqual(volumes[99], 100)
        self.assertEqual(volumes[100], 250)


class BookSideEdgeCases:
    side: BookSide

    def test_best_price_raises_on_empty(self):
        with self.assertRaises(EmptyBookSideError):
            _ = self.side.best_price

    def test_top_level_raises_on_empty(self):
        with self.assertRaises(EmptyBookSideError):
            _ = self.side.top_level

    def test_get_top_state_returns_empty_dict_on_empty(self):
        self.assertEqual(self.side.get_top_state(), {})

    def test_get_states_returns_empty_on_empty(self):
        self.assertEqual(self.side.get_states(), {})

    def test_get_volumes_returns_empty_on_empty(self):
        self.assertEqual(self.side.get_volumes(), {})

    def test_delete_nonexistent_level_raises(self):
        with self.assertRaises(PriceLevelNotFoundError):
            self.side.delete_level(99)

    def test_get_level_nonexistent_raises(self):
        with self.assertRaises(PriceLevelNotFoundError):
            self.side.get_level(99)


class TestBookSideAbstract(unittest.TestCase):
    def test_book_side_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            BookSide()


class BidSideTestBase(BookSideTestBase):
    def get_book_side(self):
        return BidSide()


class TestBidSideInvariants(BookSideInvariants, BidSideTestBase):
    pass


class TestBidSideCRUD(BookSideCRUD, BidSideTestBase):
    pass


class TestBidSideSnapshot(BookSideSnapshot, BidSideTestBase):
    pass


class TestBidSideEdgeCases(BookSideEdgeCases, BidSideTestBase):
    pass


class TestBidSideOrdering(BidSideTestBase):
    def get_book_side(self):
        return BidSide()

    def setUp(self):
        super().setUp()
        for order_id, price in [(1, 97), (2, 98), (3, 99)]:
            self.side.post_order(self.make_order(order_id=order_id, limit_price=price))

    def test_best_price_is_highest(self):
        self.assertEqual(self.side.best_price, 99)

    def test_top_level_is_queue_at_highest_price(self):
        self.assertIs(self.side.top_level, self.queue_at(99))

    def test_get_top_state_returns_only_highest_price(self):
        self.queue_at(99).get_state.return_value = "TOP_STATE"
        self.assertEqual(self.side.get_top_state(), {99: "TOP_STATE"})

    def test_get_volumes_is_descending(self):
        self.queue_at(99).get_volume.return_value = 100
        self.queue_at(98).get_volume.return_value = 100
        self.queue_at(97).get_volume.return_value = 100

        prices = list(self.side.get_volumes().keys())
        self.assertEqual(prices, [99, 98, 97])


class AskSideTestBase(BookSideTestBase):
    def get_book_side(self) -> BookSide:
        return AskSide()


class TestAskSideInvariants(BookSideInvariants, AskSideTestBase):
    pass


class TestAskSideCRUD(BookSideCRUD, AskSideTestBase):
    pass


class TestAskSideSnapshot(BookSideSnapshot, AskSideTestBase):
    pass


class TestAskSideEdgeCases(BookSideEdgeCases, AskSideTestBase):
    pass


class TestAskSideOrdering(AskSideTestBase):
    """
    Ask-specific behaviour: best price is lowest.
    """

    def setUp(self):
        super().setUp()
        for order_id, price in [(1, 101), (2, 102), (3, 103)]:
            self.side.post_order(self.make_order(order_id=order_id, limit_price=price))

    def test_best_price_is_lowest(self):
        self.assertEqual(self.side.best_price, 101)

    def test_top_level_is_queue_at_lowest_price(self):
        self.assertIs(self.side.top_level, self.queue_at(101))

    def test_get_top_state_returns_only_lowest_price(self):
        self.queue_at(101).get_state.return_value = "TOP_STATE"
        self.assertEqual(self.side.get_top_state(), {101: "TOP_STATE"})

    def test_get_volumes_is_ascending(self):
        self.queue_at(101).get_volume.return_value = 100
        self.queue_at(102).get_volume.return_value = 100
        self.queue_at(103).get_volume.return_value = 100

        prices = list(self.side.get_volumes().keys())
        self.assertEqual(prices, [101, 102, 103])


if __name__ == "__main__":
    unittest.main()
