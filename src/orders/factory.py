# product = order
# concrete = limit / market orders

from orders.order import Order, LimitOrder, MarketOrder, OrderParameters, OrderID
from abc import ABC, abstractmethod
from bookkeeping.custom_types import OrderType, Side, ExecutionRules

class OrderFactory(ABC):

    def __init__(self):
        pass

    @abstractmethod
    def create_order(self, side: Side, initial_quantity: int,
                     user_id: int, **kwargs) -> Order:
        pass
        
class LimitOrderFactory(OrderFactory):
    def __init__(self):
        pass

    def create_order(self, side: Side, initial_quantity: int, user_id: int, 
                     limit_price: float, execution_rule: ExecutionRules = None) -> Order:
        
        order_parameters = OrderParameters(side, initial_quantity)
        order_id = OrderID(user_id)

        return LimitOrder(order_parameters, order_id, limit_price, execution_rule)

class MarketOrderFactory(OrderFactory):
    def __init__(self):
        pass

    def create_order(self, side: Side, initial_quantity: int, user_id: int) -> Order:
        
        order_parameters = OrderParameters(side, initial_quantity)
        order_id = OrderID(user_id)
        
        return MarketOrder(order_parameters, order_id)
    

map_type_to_factory = {
        OrderType.LIMIT: LimitOrderFactory,
        OrderType.MARKET: MarketOrderFactory
    }