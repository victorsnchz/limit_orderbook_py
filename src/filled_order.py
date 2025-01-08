import dataclasses
from order import Order

@dataclasses.dataclass(frozen=True)
class FilledOrder:

    order: Order
    filled_qty: float