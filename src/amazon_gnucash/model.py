import re
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

IN_STORE = re.compile(r"[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}")


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


class Charge(BaseModel):
    """One card transaction from Amazon's Your Payments > Transactions page."""

    model_config = ConfigDict(frozen=True)

    login: str  # the Amazon account the transactions were saved from
    order_id: str
    card: str
    date: date
    amount: Decimal  # as Amazon shows it: negative is a charge, positive a refund
    currency: str  # the symbol Amazon shows, e.g. "$" or "CA$"
    link: str | None  # to the order on Amazon; in-store purchases have none
    merchant: str | None  # who was paid, e.g. "Whole Foods FTG 10000", when shown


class Order(BaseModel):
    """An order's items with every charge and refund Amazon made for it."""

    model_config = ConfigDict(frozen=True)

    order_id: str
    items: tuple[Item, ...]  # empty when the order isn't in the export
    charges: tuple[Charge, ...]

    @property
    def link(self) -> str | None:
        return next((charge.link for charge in self.charges if charge.link), None)

    @property
    def login(self) -> str:
        return self.charges[0].login

    @property
    def kind(self) -> str:
        if self.order_id.startswith("D01-"):
            return "digital order"
        if IN_STORE.fullmatch(self.order_id):  # e.g. Whole Foods
            return "in-store purchase"
        return "retail order"
