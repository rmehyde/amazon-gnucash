from datetime import date, datetime
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


class Charge(BaseModel):
    """One card transaction from Amazon's Your Payments > Transactions page."""

    model_config = ConfigDict(frozen=True)

    login: str  # the Amazon account the page was saved from
    order_id: str
    card: str
    date: date
    amount: Decimal  # as Amazon shows it: negative is a charge, positive a refund
    pending: bool
