import random
from orders.order import Order
from bookkeeping.custom_types import Side, OrderType
from orders.factory import map_type_to_factory, OrderFactory
from abc import ABC, abstractmethod

class OrdersGenerator(ABC):

    def __init__(self):
        self.order_factory = OrderFactory()

    @abstractmethod
    def generate_orders(self, bid_count: int, ask_count: int, 
                        bid_volume: int, ask_volume: int, 
                        **kwargs) -> tuple[set[Order]]:
        pass
    
    @abstractmethod
    def generate_for_side(self) -> set[Order]:
        pass

class MarketOrdersGenerator(OrdersGenerator):

    def __init__(self):
        self.order_factory = map_type_to_factory[OrderType.MARKET]()

    def generate_for_side(self, side: Side, count: int, mean_volume: int) -> set[Order]:
        
        orders: set[Order] = set()

        for i in range(count):
            user_id = random.randint(10, 100000)
            volume = int(random.gauss(mean_volume, mean_volume/10))
            order: Order = self.order_factory.create_order(side=side, 
                                                           initial_quantity=volume,
                                                           user_id=user_id)
            orders.add(order)
        
        return orders

    def generate_orders(self, bid_count: int, ask_count: int, 
                        bid_volume: int, ask_volume: int, **kwargs) -> tuple[set[Order]]:
        
        bid_orders = self.generate_for_side(side = Side.BID, count = bid_count, 
                                            mean_volume = bid_volume)
        ask_orders = self.generate_for_side(side = Side.ASK, count = ask_count,
                                            mean_volume = ask_volume)
        
        return bid_orders, ask_orders

class LimitOrdersGenerator(OrdersGenerator):
    def __init__(self):
        self.order_factory = map_type_to_factory[OrderType.LIMIT]()

    def generate_for_side(self, side: Side, count: int, mean_volume: int,
                          best_price: float, vol: float) -> set[Order]:
        
        def compute_limit_price():
            
            tolerance = .01

            # arbitray assume client willing to pay x% worse than top of book

            order_price = random.gauss(mu = best_price, sigma = vol)

            if side == Side.BID:
                return min(best_price * (1 + tolerance), order_price)
            
            else:
                return max(best_price * (1 - tolerance), order_price)

        orders: set[Order] = set()

        for i in range(count):
            user_id = random.randint(10, 100000)
            limit_price = compute_limit_price()
            volume = int(random.gauss(mean_volume, mean_volume/10))
        
            order: Order = self.order_factory.create_order(side=side, 
                                                           initial_quantity=volume,
                                                           user_id=user_id, 
                                                           limit_price = limit_price)
            orders.add(order)
        
        return orders

    def generate_orders(self, bid_count: int, ask_count: int, 
                        bid_volume: int, ask_volume: int,
                        **kwargs) -> tuple[set[Order]]:
        
        best_bid = kwargs['best_bid']
        best_ask = kwargs['best_ask'] 
        bid_vol = kwargs['bid_vol']
        ask_vol = kwargs['ask_vol']

        bid_orders = self.generate_for_side(side = Side.BID, count = bid_count, 
                                            best_price = best_bid, vol = bid_vol,
                                            mean_volume = bid_volume)
        ask_orders = self.generate_for_side(side = Side.ASK, count = ask_count, 
                                            best_price = best_ask, vol = ask_vol,
                                            mean_volume = ask_volume)
        
        return bid_orders, ask_orders
    
map_order_type_to_generator = {
    OrderType.LIMIT: LimitOrdersGenerator,
    OrderType.MARKET: MarketOrdersGenerator
}