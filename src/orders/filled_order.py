import dataclasses
from orders.order import Order

@dataclasses.dataclass(frozen=True)
class FilledOrder:

    order: Order
    filled_qty: float