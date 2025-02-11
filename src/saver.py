from order import Order
from orderbook import OrderBook

from files_manager import write_dict_to_csv
import os
import datetime
import csv

class Saver:

    """
    Save orderbook states in CSV files.
    """

    def __init__(self, data_directory: str = None):
        
        if data_directory is None:
            self._data_directory = f'{os.path.abspath(os.path.dirname(__file__))}/..'

        else:
            self._data_directory = data_directory

        self.now = datetime.datetime.now()

    def order_to_csv(self, order: Order, path: str = None) -> None:
        
        pass

    def orderbook_state_to_csv(self, orderbook: OrderBook, path: str = None) -> None:        

        date = self.now.date().strftime('%Y_%m_%d')
        
        if path is None:
            orderbook_state_dir = f'{self._data_directory}/orderbook_state_dir/{date}' 
        else:
            orderbook_state_dir = f'{self._data_directory}/{path}'
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     
        if not os.path.exists(orderbook_state_dir):
            os.makedirs(orderbook_state_dir)

        bids_state, asks_state = orderbook.get_orderbook_state()

        timestamp = self.now.time().strftime('%H_%M_%S')

        with open(f'{orderbook_state_dir}/bid_{timestamp}.csv', 'w') as csv_file:
            
            writer = csv.writer(csv_file)
            write_dict_to_csv(writer, bids_state)

        with open(f'{orderbook_state_dir}/ask_{timestamp}.csv', 'w') as csv_file:
            
            writer = csv.writer(csv_file)
            write_dict_to_csv(writer, asks_state)

    def top_of_book_state_to_csv(self, orderbook: OrderBook, path: str = None) -> None:        

        date = self.now.date().strftime('%Y_%m_%d')

        if path is None:
            top_of_book_states_dir = f'{self._data_directory}/top_of_book_states/{date}' 
        else:
            top_of_book_states_dir = f'{self._data_directory}/{path}' 
        
        if not os.path.exists(top_of_book_states_dir):
            os.makedirs(top_of_book_states_dir)

        top_bid_state, top_ask_state = orderbook.get_top_of_book_state()
        timestamp = self.now.time().strftime('%H_%M_%S')

        with open(f'{top_of_book_states_dir}/bid_{timestamp}.csv', 'w') as csv_file:
            
            writer = csv.writer(csv_file)
            write_dict_to_csv(writer, top_bid_state)
        
        with open(f'{top_of_book_states_dir}/ask_{timestamp}.csv', 'w') as csv_file:
            
            writer = csv.writer(csv_file)
            write_dict_to_csv(writer, top_ask_state)