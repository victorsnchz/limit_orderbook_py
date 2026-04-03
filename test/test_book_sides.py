import unittest
import sys

sys.path.append('src')

from abc import abstractmethod
from orderbook.orderbook import OrderBook
from orderbook.book_side import BookSide, BidSide, AskSide
from orders.order import OrderId, Order, OrderSpec
from bookkeeping.custom_types import OrderType, ExecutionRules, Side

class TestBookSideBase(unittest.TestCase):
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
        specs = OrderSpec(side.)        
        self.assertFalse(side.is_empty)

    def test_post_order_creates_level(self): ...
    def test_post_order_appends_to_existing_level(self):...
    def test_delete_level(self):...
    def test_is_level_empty(self): ...
    def test_get_price_levels_state_volume_aggregation(self):...
    def test_get_price_levels_state_participant_deduplication(self): ...
    def test_get_volumes(self): ...

class TestBidSide(TestBookSideBase):
    """
    Bids-specific behaviour: best price highest, volumes reversed.
    """

    def get_book_side(self) -> BookSide:
        return BidSide()

    def test_is_empty_on_init(self):

        bid_side = BidSide()
        super().test_is_empty_on_init(bid_side)

    def test_best_price_is_highest(self): ...
    def test_top_of_book_is_highest_queue(self):...
    def test_get_volumes_is_descending(self): ...
    def test_get_top_of_book_state(self): ...

class TestAskSide(TestBookSideBase):
    """
    Ask-specific behaviour: best price is lowest.
    """
    def get_book_side(self) -> BookSide:
        return AskSide()

    def test_is_empty_on_init(self, side):
        ask_side = AskSide()
        super().test_is_empty_on_init(ask_side)

    def test_best_price_is_lowest(self): ...
    def test_top_of_book_is_lowest_queue(self): ...
    def test_get_top_of_book_state(self): ...

class TestBookSideEdgeCases(unittest.TestCase):
    """
    Boundary and error conditions.
    """
    


    def test_get_best_price_raises_on_empty(self): ...
    def test_get_top_of_book_raises_on_empty(self): ...
    def test_delete_nonexistent_level_raises(self): ...
    def test_post_multiple_orders_same_price_same_participant(self): ...



if __name__ == '__main__':
    unittest.main()