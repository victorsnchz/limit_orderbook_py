import dataclasses
from custom_types import OrderType, BookSide, OrderExecutionRules


@dataclasses.dataclass(frozen=True)
class Order:

    type: OrderType
    execution_rules: OrderExecutionRules
    side: BookSide
    initial_quantity: float | int
    price: float | int

    def __post_init__(self):
        object.__setattr__(self, 'remaining_quantity', self.initial_quantity)

    def fill_quantity(self, quantity_to_fill: float):

        if self.execution_rules == OrderExecutionRules.FILL_OR_KILL:
            object.__setattr__(self, 'remaining_quantity', 0)
        
        else:
            object.__setattr__(self, 'remaining_quantity', self.remaining_quantity - quantity_to_fill)

    def is_filled(self):
        return self.remaining_quantity == 0