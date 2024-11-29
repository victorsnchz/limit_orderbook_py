import dataclasses
from custom_types import OrderType, BookSide, OrderExecutionRules
import datetime

@dataclasses.dataclass(frozen=True)
class Order:

    side: BookSide
    type: OrderType
    execution_rules: OrderExecutionRules
    initial_quantity: float | int
    price: float | int


    def __post_init__(self):
        object.__setattr__(self, 'remaining_quantity', self.initial_quantity)
        object.__setattr__(self, 'creation_time', datetime.datetime.now())

        id_from_creation_date = str(hash(f'{self.creation_time}'))[1:8]
        object.__setattr__(self, 'id', id_from_creation_date)

    def fill_quantity(self, quantity_to_fill: float) -> None:

        to_fill = min(self.remaining_quantity, quantity_to_fill)
        object.__setattr__(self, 'remaining_quantity', self.remaining_quantity - to_fill)

    def is_filled(self) -> bool:
        return self.remaining_quantity == 0
    
@dataclasses.dataclass(frozen=True)
class LimitOrder:

    order: Order
    
    def fill_quantity(self, quantity_to_fill) -> None:
        self.order.fill_quantity(quantity_to_fill)
        
    def is_filled(self) -> bool:
        return self.order.is_filled()
        
@dataclasses.dataclass(frozen=True)
class MarketOrder:

    order: Order

    def fill_quantity(self, quantity_to_fill) -> None:
        self.order.fill_quantity(quantity_to_fill)
        
    def is_filled(self) -> bool:
        return self.order.is_filled()


class OrderFactory:

    orders = {
        OrderType.LIMIT: LimitOrder,
        OrderType.MARKET: MarketOrder
    }
    
    def create_order(self, order_type: OrderType,
                     side: BookSide, execution_rules: OrderExecutionRules,
                     initial_quantity: float, price: float):

        new_order = Order(side, execution_rules, initial_quantity, price)

        return self.orders[order_type](new_order)