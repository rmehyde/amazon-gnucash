"""Parse the transactions scripts/transactions.js saves from Your Payments > Transactions."""

import re
from collections import Counter
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, ValidationError

from amazon_gnucash.model import Charge

AMOUNT = re.compile(r"([+-])\$([\d,]+\.\d\d)")  # "$" even for Canadian dollars
ORDER = re.compile(r"Order #(\S+)")
# Amazon shows every amount with "$", so the currency comes from the order link's site.
# In-store purchases have no link.
CURRENCIES = {None: "$", "www.amazon.com": "$", "www.amazon.ca": "CA$"}


class TransactionFormatError(ValueError):
    pass


# Amazon's names for the parts of each transaction this reads; it ignores the rest.
class _Order(BaseModel):
    orderDisplayString: str
    orderDetailsUrl: str


class _Status(BaseModel):
    status: Literal["Approved"]
    amountDetailsStatusType: Literal["Charge", "Refund"]


class _CardNumber(BaseModel):
    prefix: Literal["••••"]
    lastDigits: Annotated[str, Field(pattern=r"^\d{4}$")]


class _PaymentMethod(BaseModel):
    paymentMethodName: str
    paymentMethodNumber: _CardNumber | None = None  # gift cards have none


class _Transaction(BaseModel):
    formattedAmount: str
    formattedDate: str
    orderData: list[_Order]
    statementDescriptor: str
    statusInfo: _Status
    paymentMethodDisplayStringData: _PaymentMethod


class _Saved(BaseModel):
    login: str
    transactions: list[_Transaction]


def load_charges(files: list[Path]) -> list[Charge]:
    """Every charge across the files.

    Files saved at different times overlap, so a charge counts as many times as it
    appears in any single file, not the sum across files.
    """
    merged = Counter[Charge]()
    for file in files:
        merged |= Counter(parse_transactions(file.read_text(encoding="utf-8")))
    return list(merged.elements())


def parse_transactions(text: str) -> list[Charge]:
    try:
        saved = _Saved.model_validate_json(text)
    except ValidationError as error:
        raise TransactionFormatError(str(error)) from None
    if not saved.transactions:
        raise TransactionFormatError("found no transactions")
    return [_charge(transaction, saved.login) for transaction in saved.transactions]


def _charge(transaction: _Transaction, login: str) -> Charge:
    if len(transaction.orderData) != 1:
        raise TransactionFormatError(f"expected one order, found {transaction.orderData}")
    order = transaction.orderData[0]
    site = urlsplit(order.orderDetailsUrl).hostname
    if site not in CURRENCIES:
        raise TransactionFormatError(f"unknown site {site!r} in {order.orderDetailsUrl!r}")
    sign, digits = _match(AMOUNT, transaction.formattedAmount).groups()
    method = transaction.paymentMethodDisplayStringData
    number = method.paymentMethodNumber
    return Charge(
        login=login,
        order_id=_match(ORDER, order.orderDisplayString).group(1),
        link=order.orderDetailsUrl or None,
        merchant=transaction.statementDescriptor or None,
        card=f"{method.paymentMethodName} ****{number.lastDigits}"
        if number
        else method.paymentMethodName,
        date=_date(transaction.formattedDate),
        amount=Decimal(sign + digits.replace(",", "")),
        currency=CURRENCIES[site],
    )


def _date(text: str) -> date:
    try:
        return datetime.strptime(text, "%b %d, %Y").date()
    except ValueError:
        raise TransactionFormatError(f"expected a date like 'Nov 07, 2026', found {text!r}") from None


def _match(pattern: re.Pattern, text: str) -> re.Match:
    if not (match := pattern.fullmatch(text)):
        raise TransactionFormatError(f"expected {pattern.pattern!r}, found {text!r}")
    return match
