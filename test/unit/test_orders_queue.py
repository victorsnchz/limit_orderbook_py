import unittest
from unittest.mock import MagicMock
import sys

sys.path.append("src")
from lob.orderbook.orders_queue import OrdersQueue
from lob.orders.order import Order, OrderSpec, OrderID
from lob.bookkeeping.custom_types import Side, ExecutionRule, OrderType, LevelState
from lob.bookkeeping.exceptions import (
    DuplicateOrderError,
    EmptyQueueError,
    OrderNotFoundError,
)


class OrdersQueueTestBase(unittest.TestCase):
    def setUp(self):
        self.orders_queue = OrdersQueue()

    def make_order(
        self,
        order_id: int = 1,
        user_id: int = 1,
        initial_quantity: int = 100,
        remaining_quantity: int = 0,
    ):
        order = MagicMock()
        order.order_id = order_id
        order.user_id = user_id
        order.remaining_quantity = remaining_quantity
        order.initial_quantity = initial_quantity
        return order


class TestOrdersQueueInvariants(OrdersQueueTestBase):
    def test_empty_len_zero(self):
        self.assertEqual(len(self.orders_queue), 0)

    def test_len_tracks_posted_order(self):
        resting = self.make_order(1)
        self.orders_queue.add_order(resting)
        self.assertEqual(len(self.orders_queue), 1)

    def test_len_tracks_revmoved_order(self):
        resting = self.make_order(1)
        self.orders_queue.add_order(resting)
        self.orders_queue.remove_order(resting.order_id)
        self.assertEqual(len(self.orders_queue), 0)

    def test_is_empty_true_on_init(self):
        self.assertTrue(self.orders_queue.is_empty)

    def test_is_empty_false_after_add(self):
        resting = self.make_order()
        self.orders_queue.add_order(resting)
        self.assertFalse(self.orders_queue.is_empty)

    def test_is_empty_true_after_add_then_remove(self):
        resting = self.make_order()
        self.orders_queue.add_order(resting)
        self.orders_queue.remove_order(resting.order_id)
        self.assertTrue(self.orders_queue.is_empty)

    def test_contains_false_on_empty(self):
        self.assertNotIn(1, self.orders_queue)

    def test_contains_true_after_add(self):
        resting = self.make_order()
        self.orders_queue.add_order(resting)
        self.assertIn(resting.order_id, self.orders_queue)

    def test_contains_false_unknown_id(self):
        resting = self.make_order(1)
        self.orders_queue.add_order(resting)
        self.assertNotIn(3, self.orders_queue)

    def test_contains_false_after_remove(self):
        resting = self.make_order(1)
        self.orders_queue.add_order(resting)
        self.orders_queue.remove_order(resting.order_id)
        self.assertNotIn(resting.order_id, self.orders_queue)


class TestOrdersQueueCRUD(OrdersQueueTestBase):
    def test_add_single_order(self):
        resting = self.make_order()
        self.orders_queue.add_order(resting)
        self.assertIn(resting.order_id, self.orders_queue)
        self.assertIs(self.orders_queue.get_order(resting.order_id), resting)

    def test_add_duplicate_id_raises(self):
        # adding two orders with same order_id should raise RuntimeError
        resting1 = self.make_order(1)
        resting2 = self.make_order(1)
        self.orders_queue.add_order(resting1)
        with self.assertRaises(DuplicateOrderError):
            self.orders_queue.add_order(resting2)

    def test_add_multiple_orders_all_present(self):
        resting1 = self.make_order(1)
        resting2 = self.make_order(2)
        self.orders_queue.add_order(resting1)
        self.orders_queue.add_order(resting2)
        self.assertIn(resting1.order_id, self.orders_queue)
        self.assertIn(resting2.order_id, self.orders_queue)
        self.assertIs(self.orders_queue.get_order(1), resting1)
        self.assertEqual(self.orders_queue.get_order(2), resting2)

    def test_remove_returns_the_order(self):
        resting = self.make_order()
        self.orders_queue.add_order(resting)
        self.assertEqual(self.orders_queue.remove_order(resting.order_id), resting)

    def test_remove_last_order_queue_empty(self):
        resting = self.make_order()
        self.orders_queue.add_order(resting)
        self.orders_queue.remove_order(resting.order_id)
        self.assertTrue(self.orders_queue.is_empty)

    def test_remove_non_existent_raises(self):
        resting = self.make_order()
        self.orders_queue.add_order(resting)
        with self.assertRaises(AssertionError):
            self.orders_queue.remove_order(2)

    def test_remove_empty_raises(self):
        with self.assertRaises(AssertionError):
            self.orders_queue.remove_order(2)

    def test_next_on_empty_raises(self):
        with self.assertRaises(EmptyQueueError):
            self.orders_queue.next_order_to_execute

    def test_next_returns_only_inserted(self):
        resting = self.make_order()
        self.orders_queue.add_order(resting)
        self.assertIs(self.orders_queue.next_order_to_execute, resting)

    def test_tail_returns_only_inserted(self):
        resting = self.make_order()
        self.orders_queue.add_order(resting)
        self.assertIs(self.orders_queue.tail, resting)

    def test_tail_on_empty_raises(self):

        with self.assertRaises(EmptyQueueError):
            self.orders_queue.tail

    def test_get_order_not_found_raises(self):
        resting = self.make_order(order_id=1)
        self.orders_queue.add_order(resting)
        with self.assertRaises(OrderNotFoundError):
            self.orders_queue.get_order(3)

    def test_get_order_empty_raises(self):
        with self.assertRaises(OrderNotFoundError):
            self.orders_queue.get_order(3)


class TestOrdersQueueFIFO(OrdersQueueTestBase):
    def test_next_returns_first_inserted(self):
        resting1 = self.make_order(1)
        resting2 = self.make_order(2)
        self.orders_queue.add_order(resting1)
        self.orders_queue.add_order(resting2)
        self.assertIs(self.orders_queue.next_order_to_execute, resting1)

    def test_next_does_not_modify(self):
        resting1 = self.make_order(1)
        resting2 = self.make_order(2)
        self.orders_queue.add_order(resting1)
        self.orders_queue.add_order(resting2)

        _ = self.orders_queue.next_order_to_execute
        _ = self.orders_queue.next_order_to_execute

        self.assertIs(self.orders_queue.next_order_to_execute, resting1)
        self.assertIn(1, self.orders_queue)
        self.assertIn(2, self.orders_queue)
        self.assertEqual(len(self.orders_queue), 2)

    def test_tail_returns_last_inserted(self):
        resting1 = self.make_order(1)
        resting2 = self.make_order(2)
        self.orders_queue.add_order(resting1)
        self.orders_queue.add_order(resting2)
        self.assertIs(self.orders_queue.tail, resting2)

    def test_tail_does_not_modify(self):
        resting1 = self.make_order(1)
        resting2 = self.make_order(2)
        self.orders_queue.add_order(resting1)
        self.orders_queue.add_order(resting2)

        _ = self.orders_queue.tail
        _ = self.orders_queue.tail

        self.assertIs(self.orders_queue.tail, resting2)
        self.assertIn(1, self.orders_queue)
        self.assertIn(2, self.orders_queue)
        self.assertEqual(len(self.orders_queue), 2)

    def test_fifo_three_orders_full_drain(self):
        expected = [self.make_order(i) for i in (1, 2, 3)]
        for order_to_post in expected:
            self.orders_queue.add_order(order_to_post)

        for order in expected:
            self.assertIs(self.orders_queue.next_order_to_execute, order)
            self.orders_queue.remove_order(order.order_id)

    def test_fifo_not_affected_by_order_id_value(self):
        resting1 = self.make_order(1)
        resting3 = self.make_order(3)
        self.orders_queue.add_order(resting3)
        self.orders_queue.add_order(resting1)
        self.assertIs(self.orders_queue.next_order_to_execute, resting3)
        self.assertIs(self.orders_queue.tail, resting1)

    def test_remove_leaves_others_intact(self):
        resting1 = self.make_order(1)
        resting2 = self.make_order(2)
        self.orders_queue.add_order(resting1)
        self.orders_queue.add_order(resting2)
        self.orders_queue.remove_order(resting1.order_id)
        self.assertFalse(self.orders_queue.is_empty)
        self.assertIn(resting2.order_id, self.orders_queue)
        self.assertDictEqual(
            {resting2.order_id: resting2},
            self.orders_queue._queue,
        )


class TestOrdersQueueSnapshot(OrdersQueueTestBase):
    def test_get_state_empty_raises(self):
        with self.assertRaises(AssertionError):
            self.orders_queue.get_state()

    def test_get_state_returns_level_state(self):
        resting = self.make_order()
        self.orders_queue.add_order(resting)
        self.assertIsInstance(self.orders_queue.get_state(), LevelState)

    def test_get_state_single_order(self):
        resting = self.make_order(order_id=1, user_id=1, remaining_quantity=100)
        self.orders_queue.add_order(resting)
        state = self.orders_queue.get_state()
        self.assertEqual(state.order_count, 1)
        self.assertEqual(state.participant_count, 1)
        self.assertEqual(state.total_volume, 100)

    def test_get_state_multiple_orders_same_participant(self):
        resting1 = self.make_order(order_id=1, user_id=1, remaining_quantity=100)
        resting2 = self.make_order(order_id=2, user_id=1, remaining_quantity=50)
        self.orders_queue.add_order(resting1)
        self.orders_queue.add_order(resting2)
        state = self.orders_queue.get_state()
        self.assertEqual(state.order_count, 2)
        self.assertEqual(state.participant_count, 1)
        self.assertEqual(state.total_volume, 150)

    def test_get_state_deduplicated_users(self):
        resting1 = self.make_order(order_id=1, user_id=1, remaining_quantity=100)
        resting2 = self.make_order(order_id=2, user_id=2, remaining_quantity=100)
        resting3 = self.make_order(order_id=3, user_id=1, remaining_quantity=100)
        self.orders_queue.add_order(resting1)
        self.orders_queue.add_order(resting2)
        self.orders_queue.add_order(resting3)
        state = self.orders_queue.get_state()
        self.assertEqual(state.order_count, 3)
        self.assertEqual(state.participant_count, 2)
        self.assertEqual(state.total_volume, 300)

    def test_get_state_uses_remaining_not_initial_quantity(self):
        resting = self.make_order(
            order_id=1, user_id=1, remaining_quantity=50, initial_quantity=100
        )
        self.orders_queue.add_order(resting)
        self.assertEqual(self.orders_queue.get_state().total_volume, 50)

    def test_get_state_tracks_removal(self):
        resting1 = self.make_order(order_id=1, user_id=1, remaining_quantity=100)
        resting2 = self.make_order(order_id=2, user_id=2, remaining_quantity=200)
        self.orders_queue.add_order(resting1)
        self.orders_queue.add_order(resting2)
        self.orders_queue.remove_order(2)
        state = self.orders_queue.get_state()
        self.assertEqual(state.order_count, 1)
        self.assertEqual(state.participant_count, 1)
        self.assertEqual(state.total_volume, 100)

    def test_get_volume_empty_returns_zero(self):
        self.assertEqual(self.orders_queue.get_volume(), 0)

    def test_get_volume_single_order(self):
        resting = self.make_order(remaining_quantity=100)
        self.orders_queue.add_order(resting)
        self.assertEqual(self.orders_queue.get_volume(), 100)

    def test_get_volume_multiple_orders(self):
        resting1 = self.make_order(order_id=1, user_id=1, remaining_quantity=100)
        resting2 = self.make_order(order_id=2, user_id=2, remaining_quantity=200)
        self.orders_queue.add_order(resting1)
        self.orders_queue.add_order(resting2)
        self.assertEqual(self.orders_queue.get_volume(), 300)

    def test_get_volume_tracks_removal(self):
        resting1 = self.make_order(order_id=1, user_id=1, remaining_quantity=100)
        resting2 = self.make_order(order_id=2, user_id=2, remaining_quantity=200)
        self.orders_queue.add_order(resting1)
        self.orders_queue.add_order(resting2)
        self.orders_queue.remove_order(2)
        self.assertEqual(self.orders_queue.get_volume(), 100)

    def test_get_volume_uses_remaining_quantity(self):
        resting = self.make_order(
            order_id=1, user_id=1, remaining_quantity=50, initial_quantity=100
        )
        self.orders_queue.add_order(resting)
        self.assertEqual(self.orders_queue.get_volume(), 50)


if __name__ == "__main__":
    unittest.main()
