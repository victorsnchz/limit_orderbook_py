import unittest
import sys
import datetime
import csv

#sys.path.append('../')
sys.path.append('src')

from price_levels import Bids
from order import LimitOrder, OrderParameters, OrderID
from custom_types import Side, ExecutionRules
from order_execution import LimitOrderExecution
from analytics import Analytics
from orderbook import OrderBook
from saver import Saver

class TestSaverBookState(unittest.TestCase):
    
    def test_case_one_state(self):

        orderbook = OrderBook()

        bid1 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                                limit_price=100, execution_rules = ExecutionRules.GTC)
        bid2 = LimitOrder(OrderParameters(Side.BID, 200), OrderID(1),
                                limit_price=100, execution_rules = ExecutionRules.GTC)
        bid3 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                                limit_price=105, execution_rules = ExecutionRules.GTC)

        ask1 = LimitOrder(OrderParameters(Side.ASK, 100), OrderID(2),
                                limit_price=110, execution_rules = ExecutionRules.GTC)
        ask2 = LimitOrder(OrderParameters(Side.ASK, 100), OrderID(3),
                                limit_price=120, execution_rules = ExecutionRules.GTC)

        orders = [bid1, bid2, bid3, ask1, ask2]

        for order in orders:
            exec = LimitOrderExecution(order, orderbook)
            exec.execute()

        timestamp = datetime.datetime.time()

        saver = Saver()
        saver.orderbook_state_to_csv(orderbook)

        with open(f'{timestamp}.csv', 'r') as csv_file:
            
            reader = csv.reader(csv_file)

            """ reader.writerow(top_bid_state.keys[0], top_bid_state.values[0])
            reader.writerow(top_ask_state.keys[0], top_ask_state.values[0]) """
        
    
    pass



if __name__ == '__main__':
    unittest.main()