import unittest
from orderbook import OrderBook
from order import Order, LimitOrder, OrderID, OrderParameters
from custom_types import OrderType, Side, ExecutionRules

# blend of unit-testing and integration testing

class TestOrderbook(unittest.TestCase):

    def test_case_match_no_order(self):

        orderbook = OrderBook()
        order = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        
        
        self.assertEqual(orderbook.can_match_order(order), False)

    def test_case_post_order(self):
        orderbook = OrderBook()
        order = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        
        orderbook.post_order(order)

        self.assertEqual(orderbook.bids.levels[order.limit_price].queue[order.id], order)


    def test_case_can_match_order(self):

        orderbook = OrderBook()
        order = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        order_to_match = LimitOrder(OrderParameters(Side.ASK, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        orderbook.post_order(order)

        self.assertEqual(orderbook.can_match_order(order_to_match), True)


    def test_case_post_and_match_order(self):

        orderbook = OrderBook()
        order = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        
        order_to_match = LimitOrder(OrderParameters(Side.ASK, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        
        orderbook.post_order(order)
        filled_orders, posted_order_to_match = orderbook.post_order(order_to_match)

        self.assertEqual(filled_orders[0], order)
        self.assertEqual(posted_order_to_match.is_filled(), True)

    def test_case_post_and_match_order_multi_levels(self):

        orderbook = OrderBook()
        order1 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        
        order2 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=99, execution_rules = ExecutionRules.GTC)
        
        order3 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                               limit_price=98, execution_rules = ExecutionRules.GTC)
        
        order_to_match = LimitOrder(OrderParameters(Side.ASK, 100), OrderID(0),
                               limit_price=98, execution_rules = ExecutionRules.GTC)
        

        orderbook.post_order(order1)
        orderbook.post_order(order2)
        orderbook.post_order(order3)

        filled_orders, posted_order_to_match = orderbook.post_order(order_to_match)

        self.assertEqual(filled_orders[0], order1)
        self.assertEqual(filled_orders[1], order2)
        self.assertEqual(orderbook.bids.get_top_of_book().queue[order3.id].id, order3.id)
        self.assertEqual(posted_order_to_match.is_filled(), True)

    def test_case_post_and_match_order_multi_levels(self):

        orderbook = OrderBook()
        order1 = LimitOrder(OrderParameters(Side.BID, 90), OrderID(0),
                               limit_price=100, execution_rules = ExecutionRules.GTC)
        
        order2 = LimitOrder(OrderParameters(Side.BID, 10), OrderID(1),
                               limit_price=99, execution_rules = ExecutionRules.GTC)
        
        order3 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(2),
                               limit_price=98, execution_rules = ExecutionRules.GTC)
        
        order_to_match = LimitOrder(OrderParameters(Side.ASK, 110), OrderID(3),
                               limit_price=99, execution_rules = ExecutionRules.GTC)
    
        

        orderbook.post_order(order1)
        orderbook.post_order(order2)
        orderbook.post_order(order3)

        filled_orders, posted_order_to_match = orderbook.post_order(order_to_match)

        self.assertEqual(filled_orders[1], order2)
        self.assertEqual(orderbook.bids.get_top_of_book().queue[order3.id].id, order3.id)
        self.assertEqual(posted_order_to_match.is_filled(), False)
        self.assertEqual(orderbook.asks.get_top_of_book().queue[posted_order_to_match.id].id, 
                         posted_order_to_match.id)