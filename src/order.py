from dataclasses import dataclass
from custom_types import ExecutionRules, Side
import datetime
    
@dataclass(frozen = True)
class OrderParameters:

    side: Side
    initial_quantity: float | int

@dataclass(frozen = True)
class OrderID:

    user_id: int

    def __post_init__(self):

        object.__setattr__(self, 'creation_time', datetime.datetime.now())

        id_as_hash = str(hash(f'{self.creation_time}'))[1:8]
        object.__setattr__(self, 'order_id', id_as_hash)
    
class Order:

    def __init__(self, parameters: OrderParameters, id: OrderID):
        
        self._parameters: OrderParameters = parameters
        self.id: OrderID = id

        self.remaining_quantity = self._parameters.initial_quantity

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
    
    def __init__(self, parameters: OrderParameters, id: OrderID):
        super().__init__(parameters, id)
          
class LimitOrder(Order):

    def __init__(self, parameters: OrderParameters, id: OrderID,
                limit_price: float, execution_rules: ExecutionRules):
        super().__init__(parameters, id)

        self.limit_price = limit_price
        self.execution_rules = execution_rules