import dataclasses
from src.orders.order import Order


@dataclasses.dataclass(frozen=True)
class FilledOrder:
    order: Order  # must have its own module, not in custom_types else circular import
    filled_qty: int
