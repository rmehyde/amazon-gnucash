"""Attribute each order's items to the charges and refunds Amazon made for it."""

from collections import Counter
from datetime import date
from decimal import Decimal
from enum import StrEnum
from functools import reduce
from operator import or_

from pydantic import BaseModel, ConfigDict

from finances.config import Config
from finances.model import Charge, Item, Order

BUDGET = 100_000  # item subsets to try on one order before giving up


class Reason(StrEnum):
    SKIPPED_CARD = "on a skipped card"
    PENDING = "has a pending charge"
    PARTLY_SKIPPED = "partly on a skipped card"
    NOT_IN_EXPORT = "not in export"
    NOT_IN_USD = "not in USD"
    UNMAPPED_CARD = "unmapped card"
    NO_FIT = "items don't add up to the charges"
    AMBIGUOUS = "items fit the charges more than one way"
    TOO_COMPLEX = "too many ways to check"


SKIPS = {Reason.SKIPPED_CARD, Reason.PENDING}  # left out quietly, not escalated


class Transaction(BaseModel):
    """One charge or refund, with the items it paid for."""

    model_config = ConfigDict(frozen=True)

    order_id: str
    date: date
    account: str  # where the money came from, or went back to
    amount: Decimal  # negative is a charge, positive a refund
    items: tuple[Item, ...]


class Resolved(BaseModel):
    order: Order
    transactions: tuple[Transaction, ...]


class Skipped(BaseModel):
    order: Order
    reason: Reason


class Escalated(BaseModel):
    order: Order
    reason: Reason


def reconcile(order: Order, config: Config) -> Resolved | Skipped | Escalated:
    try:
        transactions = _attribute(order, config)
    except _Unresolved as problem:
        outcome = Skipped if problem.reason in SKIPS else Escalated
        return outcome(order=order, reason=problem.reason)
    return Resolved(order=order, transactions=transactions)


class _Unresolved(Exception):
    def __init__(self, reason: Reason):
        self.reason = reason


def _require(condition: object, reason: Reason) -> None:
    if not condition:
        raise _Unresolved(reason)


def _attribute(order: Order, config: Config) -> tuple[Transaction, ...]:
    charges = order.charges
    cards = {charge.card for charge in charges}
    _require(not cards <= config.skip, Reason.SKIPPED_CARD)
    _require(not cards & config.skip, Reason.PARTLY_SKIPPED)
    _require(not any(charge.pending for charge in charges), Reason.PENDING)
    _require(order.items, Reason.NOT_IN_EXPORT)
    _require(
        all(item.currency == "USD" for item in order.items)
        and all(charge.currency == "$" for charge in charges),
        Reason.NOT_IN_USD,
    )
    _require(cards <= config.accounts.keys(), Reason.UNMAPPED_CARD)

    # Every item was charged for; only some may have been refunded.
    purchases = _fit(order.items, [c for c in charges if c.amount < 0], use_all=True)
    refunds = _fit(order.items, [c for c in charges if c.amount > 0], use_all=False)
    return tuple(
        Transaction(
            order_id=order.order_id,
            date=charge.date,
            account=config.accounts[charge.card],
            amount=charge.amount,
            items=items,
        )
        for charge, items in purchases + refunds
    )


def _fit(
    items: tuple[Item, ...], charges: list[Charge], use_all: bool
) -> list[tuple[Charge, tuple[Item, ...]]]:
    """The one way to give each charge items adding up to it, or why there isn't one.

    Identical items are interchangeable, as are identical charges, so fits that
    differ only by swapping those count as the same fit.
    """
    kinds = Counter(items)  # identical items, counted
    cents = [_cents(item.total) for item in kinds]
    budget = BUDGET

    def subsets(counts: tuple[int, ...], target: int):
        """How many of each kind of item to take to add up to `target` cents."""
        # reach[i] has bit s set when kinds i onward can add up to s cents,
        # so the walk never follows a branch that can't reach the target.
        reach = [1] * (len(counts) + 1)
        for i in reversed(range(len(counts))):
            shifts = (reach[i + 1] << cents[i] * n for n in range(counts[i] + 1))
            reach[i] = reduce(or_, shifts)

        def walk(i: int, need: int):
            if i == len(counts):
                yield ()
                return
            for n in range(counts[i] + 1):
                rest = need - cents[i] * n
                if rest >= 0 and reach[i + 1] >> rest & 1:
                    for tail in walk(i + 1, rest):
                        yield (n, *tail)

        if reach[0] >> target & 1:
            yield from walk(0, target)

    def assign(counts: tuple[int, ...], targets: list[int]):
        nonlocal budget
        if not targets:
            if not (use_all and any(counts)):
                yield ()
            return
        for taken in subsets(counts, targets[0]):
            budget -= 1
            _require(budget >= 0, Reason.TOO_COMPLEX)
            left = tuple(have - take for have, take in zip(counts, taken))
            for rest in assign(left, targets[1:]):
                yield (taken, *rest)

    fits = {}
    for taken in assign(tuple(kinds.values()), [_cents(abs(c.amount)) for c in charges]):
        same = tuple(sorted(((c.date, c.card, c.amount), t) for c, t in zip(charges, taken)))
        fits.setdefault(same, taken)
        _require(len(fits) == 1, Reason.AMBIGUOUS)
    _require(fits, Reason.NO_FIT)
    [taken] = fits.values()
    return [
        (charge, tuple(item for item, n in zip(kinds, counts) for _ in range(n)))
        for charge, counts in zip(charges, taken)
    ]


def _cents(amount: Decimal) -> int:
    cents = amount * 100
    if cents != int(cents):
        raise ValueError(f"{amount} has a fraction of a cent")
    return int(cents)
