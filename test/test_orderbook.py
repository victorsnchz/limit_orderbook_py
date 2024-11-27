import unittest
from orderbook import OrderBook
from order import Order
from custom_types import OrderType, OrderExecutionRules, BookSide

# blend of unit-testing and integration testing

class TestOrderbook(unittest.TestCase):

    def test_case_match_no_order(self):

        orderbook = OrderBook()
        new_order = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=100.0, price = 100.0)
        
        
        self.assertEqual(orderbook.can_match_order(new_order), False)

    def test_case_post_order(self):
        orderbook = OrderBook()
        new_order = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=100.0, price = 100.0)
        
        orderbook.post_order(new_order)

        self.assertEqual(orderbook.bids.levels[new_order.price].queue[new_order.id], new_order)


    def test_case_can_match_order(self):

        orderbook = OrderBook()
        order_to_post = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=100.0, price = 100.0)
        order_to_match = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.ASK, initial_quantity=100.0, price = 100.0)
        orderbook.post_order(order_to_post)

        self.assertEqual(orderbook.can_match_order(order_to_match), True)


    def test_case_post_and_match_order(self):

        orderbook = OrderBook()
        order_to_post = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=100.0, price = 100.0)
        
        order_to_match = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.ASK, initial_quantity=100.0, price = 100.0)
        
        orderbook.post_order(order_to_post)
        filled_orders, posted_order_to_match = orderbook.post_order(order_to_match)

        self.assertEqual(filled_orders[0], order_to_post)
        self.assertEqual(posted_order_to_match.is_filled(), True)

    def test_case_post_and_match_order_multi_levels(self):

        orderbook = OrderBook()
        order1 = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=10, price = 100.0)
        
        order2 = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=20, price = 99.0)
        
        order3 = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=75, price = 98.0)
        
        order_to_match = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.ASK, initial_quantity=100.0, price = 98.0)
        

        orderbook.post_order(order1)
        orderbook.post_order(order2)
        orderbook.post_order(order3)

        filled_orders, posted_order_to_match = orderbook.post_order(order_to_match)

        self.assertEqual(filled_orders[0], order1)
        self.assertEqual(filled_orders[1], order2)
        self.assertEqual(orderbook.bids.get_top_of_book().queue[order3.id].id, order3.id)
        self.assertEqual(posted_order_to_match.is_filled(), True)

    def test_case_post_and_match_and_post_order_multi_levels(self):

        orderbook = OrderBook()
        order1 = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=10, price = 100.0)
        
        order2 = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=20, price = 99.0)
        
        order3 = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=60, price = 98.0)
        
        order4 = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.BID, initial_quantity=60, price = 97.0)
        
        order_to_match = Order(type = OrderType.LIMIT, execution_rules = OrderExecutionRules.GOOD_TILL_CANCELLED,
                          side = BookSide.ASK, initial_quantity=100.0, price = 98.0)
        

        orderbook.post_order(order1)
        orderbook.post_order(order2)
        orderbook.post_order(order3)
        orderbook.post_order(order4)

        filled_orders, posted_order_to_match = orderbook.post_order(order_to_match)

        self.assertEqual(filled_orders[2], order3)
        self.assertEqual(orderbook.bids.get_top_of_book().queue[order4.id].id, order4.id)
        self.assertEqual(posted_order_to_match.is_filled(), False)
        self.assertEqual(orderbook.asks.get_top_of_book().queue[posted_order_to_match.id].id, 
                         posted_order_to_match.id)