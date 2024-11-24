import unittest
unittest.TestLoader.sortTestMethodsUsing = None

from price_levels import PriceLevels
from order import Order
from custom_types import OrderType,OrderExecutionRules, BookSide



class TestPriceLevels(unittest.TestCase):
    
    price_levels = PriceLevels(BookSide.ASK)
    order = Order(type =  OrderType.LIMIT, execution_rules= OrderExecutionRules.GOOD_TILL_CANCELLED, 
                      side = BookSide.ASK, initial_quantity=100, price = 100)
    
    def test_case_empty(self):
        self.assertEqual(self.price_levels.is_empty(), True)

    def test_case_add_order(self):
        
        self.price_levels.post_order(self.order)

        self.assertEqual(self.order.id in self.price_levels.levels[self.order.price].queue, True)


    def test_case_add_order(self):
        order = Order(type =  OrderType.LIMIT, execution_rules= OrderExecutionRules.GOOD_TILL_CANCELLED, 
                      side = BookSide.ASK, initial_quantity=100, price = 100)
        
        self.price_levels.post_order(order)

        self.assertEqual(order.id in self.price_levels.levels[order.price].queue, True)

    def test_case_top_of_book(self):
        order2 = Order(type =  OrderType.LIMIT, execution_rules= OrderExecutionRules.GOOD_TILL_CANCELLED, 
                      side = BookSide.ASK, initial_quantity=99, price = 100)
        
        self.price_levels.post_order(order2)

        self.assertEqual(self.price_levels.top_of_book(), order2.price)

    def test_case_cancel_order(self):

        order3 = Order(type =  OrderType.LIMIT, execution_rules= OrderExecutionRules.GOOD_TILL_CANCELLED, 
                      side = BookSide.ASK, initial_quantity=99, price = 98)
        
        self.price_levels.post_order(order3)
        self.assertEqual(order3.id in self.price_levels.levels[order3.price].queue, True)
        self.price_levels.cancel_order(order3)
        self.assertEqual(order3.id in self.price_levels.levels_ordered, False)
        self.assertEqual(order3.id in self.price_levels.levels, False)