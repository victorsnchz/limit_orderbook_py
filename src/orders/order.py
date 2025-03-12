from dataclasses import dataclass
from bookkeeping.custom_types import ExecutionRules, Side
import datetime
from abc import ABC, abstractmethod    

@dataclass(frozen = True)
class OrderParameters:

    side: Side
    initial_quantity: float | int

@dataclass(frozen = True)
class OrderID:

    """
    Store user and order information.
    """

    user_id: int

    def __post_init__(self):

        # ideally users should have unique ID
        # given ID new order should have unique ID via hash
        # should be able to verufy that given order belongs to given customer 
        # not necessary but cool feature

        object.__setattr__(self, 'creation_time', datetime.datetime.now())

        id_as_hash = int(str(hash(f'{self.creation_time}'))[1:8])
        object.__setattr__(self, 'order_id', id_as_hash)

    
class Order(ABC):

    """
    Store order informations and any relevant order updates.
    """

    def __init__(self, parameters: OrderParameters, id: OrderID):
        
        self._parameters: OrderParameters = parameters
        self.id: OrderID = id

        self.remaining_quantity = self._parameters.initial_quantity

    def __hash__(self):
        return int(self.id.order_id)
    

    def fill_quantity(self, quantity_to_fill: float) -> None:
        to_fill = min(self.remaining_quantity, quantity_to_fill)
        self.remaining_quantity -= to_fill

    def is_filled(self) -> bool:
        return self.remaining_quantity == 0
    
    def get_side(self) -> Side:
        return self._parameters.side
    
    def get_initial_quantity(self) -> int | float:
        return self._parameters.initial_quantity
    
    def get_id(self) -> int:
        return self.id.order_id

class MarketOrder(Order):

    """
    Market orders matched against opposite side in book. Will not live in the book (not postable).
    """
    
    def __init__(self, parameters: OrderParameters, id: OrderID):
        super().__init__(parameters, id)
          
class LimitOrder(Order):

    """
    Limit orders matched against opposite side in book, 
    remaining quantity will be posted.
    By default GoodTillCancelled.
    """

    def __init__(self, parameters: OrderParameters, id: OrderID,
                limit_price: float, execution_rules: ExecutionRules = None):
        super().__init__(parameters, id)

        self.limit_price = limit_price
        self.execution_rules = execution_rules

    def __post_init__(self):
        if self.execution_rules == None:
            self.execution_rules = ExecutionRules.GTC