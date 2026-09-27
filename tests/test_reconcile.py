from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from finances.config import load_config
from finances.model import Charge, Item, Order
from finances.orders import gather
from finances.parse.export import load_digital_items, load_retail_items
from finances.parse.transactions import parse_page
from finances.reconcile import Reason, Resolved, reconcile

FIXTURES = Path(__file__).parent / "fixtures"
CONFIG = load_config(FIXTURES / "amazon.toml")


def outcome(result):
    """What happened to an order, briefly: its transactions, or why there are none."""
    if isinstance(result, Resolved):
        return [
            (t.charge.date, t.account, t.charge.amount, [i.name for i in t.items])
            for t in result.transactions
        ]
    return type(result).__name__, result.reason


def test_reconciles_orders():
    items = [
        *load_retail_items(FIXTURES / "Order History.csv"),
        *load_digital_items(FIXTURES / "Digital Content Orders.csv"),
    ]
    charges = parse_page((FIXTURES / "transactions.html").read_text())
    orders = gather(items, charges, since=date(2026, 1, 1), until=date(2026, 12, 31))

    assert {o.order_id: outcome(reconcile(o, CONFIG)) for o in orders} == {
        "111-0000001-0000001": [
            (date(2026, 9, 2), "Liabilities:Visa", Decimal("-8.70"), ["Wooden Spoons, 4 Pack"]),
        ],
        "112-0000002-0000002": [
            (date(2026, 9, 7), "Liabilities:Visa", Decimal("-15.00"), ["Magnetic Hooks, 4 Pack"]),
            (date(2026, 9, 4), "Liabilities:Visa", Decimal("-21.33"), ["Sink Strainer Basket"]),
        ],
        "111-0000003-0000003": [
            (date(2026, 8, 28), "Liabilities:Visa", Decimal("-195.92"), ["Standing Desk Frame"]),
            (date(2026, 9, 15), "Assets:Amazon Balance", Decimal("195.92"), ["Standing Desk Frame"]),
        ],
        "111-0000011-0000011": [
            (
                date(2026, 9, 20),
                "Liabilities:Visa",
                Decimal("-37.00"),
                ["Stovetop Tea Kettle", "Kettle Descaler"],
            ),
        ],
        "D01-0000004-0000004": [
            (date(2026, 8, 22), "Liabilities:Visa", Decimal("-3.99"), ["The Paper Moon"]),
        ],
        "112-0000005-0000005": ("Skipped", Reason.PENDING),
        "111-0000006-0000006": ("Skipped", Reason.SKIPPED_CARD),
        "111-0000009-0000009": ("Escalated", Reason.NOT_IN_USD),
        "00000000-0000-4000-8000-000000000010": ("Escalated", Reason.NOT_IN_EXPORT),
    }


def item(name, total, quantity=1):
    return Item(
        order_id="O",
        asin=name,
        name=name,
        department=None,
        quantity=quantity,
        currency="USD",
        total=Decimal(total),
        order_status="Closed",
    )


def charge(amount, day=1, card="Visa ****4242", merchant="Amazon.com"):
    return Charge(
        login="Pat",
        order_id="O",
        card=card,
        date=date(2026, 9, day),
        amount=Decimal(amount),
        pending=False,
        currency="$",
        link=None,
        merchant=merchant,
    )


@pytest.mark.parametrize(
    "items, charges, expected",
    [
        # Either way round gives the same two transactions.
        ([item("Pen", "2.00"), item("Ink", "2.00")], [charge("-2.00"), charge("-2.00")], Resolved),
        # Different items at the same price, charged on different days: which went when?
        (
            [item("Pen", "2.00"), item("Ink", "2.00")],
            [charge("-2.00", day=1), charge("-2.00", day=2)],
            Reason.AMBIGUOUS,
        ),
        # The charge is covered, but nothing paid for the ink.
        ([item("Pen", "2.00"), item("Ink", "3.00")], [charge("-2.00")], Reason.NO_FIT),
        # One row, two units shipped and charged separately: agreed to escalate.
        ([item("Pen", "4.00", quantity=2)], [charge("-2.00"), charge("-2.00")], Reason.NO_FIT),
        (
            [item("Pen", "31.97")],
            [charge("-25.47"), charge("-6.50", card="Amazon Gift Card")],
            Reason.SPLIT_PAYMENT,
        ),
        ([item("Pen", "2.00")], [charge("-2.00", card="Discover ****6011")], Reason.UNMAPPED_CARD),
        ([], [charge("-2.00", merchant="Amazon Fresh 1234")], Reason.SKIPPED_MERCHANT),
        (
            [item("Pen", "2.00"), item("Ink", "3.00")],
            [charge("-2.00"), charge("-3.00", card="Mastercard ****5555")],
            Reason.PARTLY_SKIPPED,
        ),
    ],
)
def test_decides_small_orders(items, charges, expected):
    result = reconcile(Order(order_id="O", items=items, charges=charges), CONFIG)

    if expected is Resolved:
        assert isinstance(result, Resolved)
    else:
        assert not isinstance(result, Resolved) and result.reason == expected
