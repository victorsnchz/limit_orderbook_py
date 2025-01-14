import unittest
import sys
import datetime
import os
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

import pathlib

import shutil

import helper


test_saver_data_dir = 'test_data/test_saver'


class TestSaverBookState(unittest.TestCase):

    abs_path = os.path.dirname(__file__)

    test_data_directory = f'{abs_path}/{test_saver_data_dir}/book_state/one_state'

    results_data_directory = f'{test_data_directory}/results'
    targets_data_directory = f'{test_data_directory}/targets'

    def test_case_one_state(self):

        orderbook = OrderBook()

        bid1 = LimitOrder(OrderParameters(Side.BID, 100), OrderID(0),
                                limit_price=100, execution_rules = ExecutionRules.GTC)

        ask1 = LimitOrder(OrderParameters(Side.ASK, 100), OrderID(2),
                                limit_price=110, execution_rules = ExecutionRules.GTC)

        orders = [bid1, ask1]

        for order in orders:
            exec = LimitOrderExecution(order, orderbook)
            exec.execute()
        
        saver = Saver(master_directory=self.results_data_directory)
        saver.orderbook_state_to_csv(orderbook, path = None)

        date = datetime.datetime.now().date().strftime('%Y_%m_%d')
        timestamp = datetime.datetime.now().time().strftime('%H_%M_%S')

        target_bid_file = f'{self.targets_data_directory}/bid'
        results_bid_file = f'{self.results_data_directory}/{date}/bid_{timestamp}'

        for target_bid_state, results_bid_state in helper.read_two_csvs(target_bid_file, results_bid_file):
            self.assertEqual(target_bid_state, results_bid_state)

        target_ask_file = f'{self.targets_data_directory}/ask'
        results_ask_file = f'{self.results_data_directory}/{date}/ask_{timestamp}'

        for target_ask_state, results_ask_state in helper.read_two_csvs(target_ask_file, results_ask_file):
            self.assertEqual(target_ask_state, results_ask_state)

        shutil.rmtree(f'{self.results_data_directory}/{date}')

        



class TestSaverTopOfBook(unittest.TestCase):
    pass
    
class TestSaverOrders(unittest.TestCase):
    pass

if __name__ == '__main__':
    unittest.main()