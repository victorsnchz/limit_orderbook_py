import unittest


from src.orderbook.book_side import BookSide, BidSide, AskSide
from src.orders.order import OrderID, Order, OrderSpec
from src.bookkeeping.custom_types import OrderType, ExecutionRule, Side


class TestBookSideBase:
    """
    Tests for shared BookSide behaviour.
    Subclassed by TestBidSide and TestAskSide where behaviour diverges.
    """

    def get_book_side(self) -> BookSide:
        raise NotImplementedError("subclasses must return a BookSide instance")

    # define ? will this auto run or should it be called in child class?
    def test_is_empty_on_init(self):
        side = self.get_book_side()
        self.assertTrue(side.is_empty)

    def test_is_empty_false_after_post(self):
        side = self.get_book_side()
        order = _make_order(1, 99, side)
        side.post_order(order)
        self.assertFalse(side.is_empty)

    def test_post_order_creates_level(self):
        side = self.get_book_side()
        order = _make_order(1, 99, side)

        side.post_order(order)
        self.assertIn(99, side.levels)

    def test_post_order_appends_to_existing_level(self):
        side = self.get_book_side()
        order1 = _make_order(1, 99, side)
        order2 = _make_order(2, 99, side)
        side.post_order(order1)
        side.post_order(order2)
        self.assertEqual(len(side.levels[99].queue), 2)

    def test_delete_level_removes_it(self):
        side = self.get_book_side()
        order = _make_order(1, 99, side)
        side.post_order(order)
        side.delete_level(order.limit_price)
        self.assertTrue(side.is_empty)

    def test_is_level_empty_after_all_removed(self):
        side = self.get_book_side()
        order = _make_order(1, 99, side)
        side.post_order(order)
        side.levels[99].remove_order(order)
        self.assertTrue(side.is_level_empty(99))

    def test_get_states_volume_aggregation(self):
        side = self.get_book_side()
        order1 = _make_order(1, 99, side)
        order2 = _make_order(2, 99, side)
        side.post_order(order1)
        side.post_order(order2)
        state = side.get_states()[99]
        self.assertEqual(state.total_volume, 200)

    def test_get_states_participant_deduplication(self):
        side = self.get_book_side()
        order1 = _make_order(1, 99, side)
        order2 = _make_order(2, 99, side)
        side.post_order(order1)
        side.post_order(order2)
        state = side.get_states()[99]
        self.assertEqual(state.participant_count, 1)

    def test_get_states_order_count(self):
        side = self.get_book_side()
        order1 = _make_order(1, 99, side, user_id=0)
        order2 = _make_order(2, 99, side, user_id=2)
        side.post_order(order1)
        side.post_order(order2)
        state = side.get_states()[99]
        self.assertEqual(state.order_count, 2)

    def test_get_states_multiple_levels(self):
        side = self.get_book_side()
        order1 = _make_order(1, 99, side)
        order2 = _make_order(2, 98, side)
        side.post_order(order1)
        side.post_order(order2)
        states = side.get_states()
        self.assertEqual(len(states), 2)
        self.assertEqual(states[99].total_volume, 100)
        self.assertEqual(states[98].total_volume, 100)

    def test_get_volumes(self):
        side = self.get_book_side()
        order1 = _make_order(1, 99, side)
        order2 = _make_order(2, 98, side)
        side.post_order(order1)
        side.post_order(order2)
        volumes = side.get_volumes()
        self.assertEqual(volumes[99], 100)
        self.assertEqual(volumes[98], 100)


class TestBidSide(TestBookSideBase, unittest.TestCase):
    """
    Bids-specific behaviour: best price highest, volumes reversed.
    """

    def get_book_side(self) -> BookSide:
        return BidSide()

    def setUp(self):
        self.side = self.get_book_side()
        order1 = _make_order(1, 99, self.side)
        order2 = _make_order(1, 100, self.side)
        order3 = _make_order(1, 101, self.side)
        self.side.post_order(order1)
        self.side.post_order(order2)
        self.side.post_order(order3)

    def test_best_price_is_highest(self):
        self.assertTrue(self.side.best_price == 101)

    def test_top_level_is_highest_queue(self):
        self.assertEqual(self.side.top_level, self.side.levels[101])

    def test_top_level_state(self):
        top_state = self.side.get_top_state()
        self.assertEqual(len(top_state), 1)
        self.assertIn(101, top_state)
        self.assertEqual(top_state[101].total_volume, 100)

    def test_get_volumes_is_descending(self):

        prices = list(self.side.get_volumes().keys())
        self.assertEqual(prices, [101, 100, 99])


class TestAskSide(TestBookSideBase, unittest.TestCase):
    """
    Ask-specific behaviour: best price is lowest.
    """

    def get_book_side(self) -> BookSide:
        return AskSide()

    def setUp(self):
        self.side = self.get_book_side()
        order1 = _make_order(1, 99, self.side)
        order2 = _make_order(1, 100, self.side)
        order3 = _make_order(1, 101, self.side)
        self.side.post_order(order1)
        self.side.post_order(order2)
        self.side.post_order(order3)

    def test_best_price_is_lowest(self):

        self.assertTrue(self.side.best_price == 99)

    def test_top_level_is_lowest_queue(self):
        self.assertEqual(self.side.top_level, self.side.levels[99])

    def test_top_level_state(self):
        top_state = self.side.get_top_state()
        self.assertEqual(len(top_state), 1)
        self.assertIn(99, top_state)
        self.assertEqual(top_state[99].total_volume, 100)

    def test_get_volumes_is_ascending(self):

        prices = list(self.side.get_volumes().keys())
        self.assertEqual(prices, [99, 100, 101])


class TestBookSideEdgeCases:
    """
    Boundary and error conditions.
    """

    def get_book_side(self) -> BookSide:
        raise NotImplementedError("subclasses must return a BookSide instance")

    def test_book_side_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            BookSide()

    def test_get_best_price_raises_on_empty(self):
        side = self.get_book_side()
        with self.assertRaises(IndexError):
            _ = side.best_price

    def test_get_top_level_raises_on_empty(self):
        side = self.get_book_side()
        with self.assertRaises(IndexError):
            _ = side.top_level

    def test_get_top_state_raises_on_empty(self):
        side = self.get_book_side()
        with self.assertRaises(IndexError):
            _ = side.get_top_state()

    def test_get_states_returns_empty_on_empty(self):

        side = self.get_book_side()
        self.assertEqual(side.get_states(), {})

    def test_delete_nonexistent_level_raises(self):
        side = self.get_book_side()
        with self.assertRaises(KeyError):
            _ = side.delete_level(99)

    def test_get_volumes_returns_empty_on_empty(self):

        side = self.get_book_side()
        self.assertEqual(side.get_volumes(), {})

    def test_post_multiple_orders_same_price_same_participant(self):
        side = self.get_book_side()
        order1 = _make_order(order_id=1, price=99, side=side)
        order2 = _make_order(order_id=2, price=99, side=side)
        side.post_order(order1)
        side.post_order(order2)
        self.assertEqual(len(side.levels[99].queue), 2)


class TestBidSideEdgeCases(TestBookSideEdgeCases, unittest.TestCase):
    def get_book_side(self) -> BookSide:
        return BidSide()


class TestAskSideEdgeCases(TestBookSideEdgeCases, unittest.TestCase):
    def get_book_side(self) -> BookSide:
        return AskSide()


def _make_order(
    order_id: int, price: int, side: Side, quantity: int = 100, user_id: int = 0
) -> Order:
    spec = OrderSpec(side, OrderType.LIMIT, quantity, price, ExecutionRule.GTC)
    return Order(spec, OrderID(order_id, user_id))


if __name__ == "__main__":
    unittest.main()
