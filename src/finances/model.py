from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class Item(BaseModel):
    """One line of Amazon's order history export."""

    model_config = ConfigDict(frozen=True)

    order_id: str
    asin: str
    name: str
    department: str | None
    quantity: int
    currency: str
    total: Decimal  # this item's cost, tax included
    order_status: str
    ship_date: datetime | None
