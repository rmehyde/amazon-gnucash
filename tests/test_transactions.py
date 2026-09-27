import shutil
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from finances.model import Charge
from finances.parse.transactions import PageFormatError, load_charges, parse_page

FIXTURE = Path(__file__).parent / "fixtures" / "transactions.html"


def charge(
    order_id, day, amount, pending=False, card="Visa ****4242", currency="$", site="com"
):
    return Charge(
        login="Pat",
        order_id=order_id,
        card=card,
        date=day,
        amount=Decimal(amount),
        pending=pending,
        currency=currency,
        link=site and f"https://www.amazon.{site}/gp/css/summary/edit.html?orderID={order_id}",
    )


def test_parses_page():
    charges = parse_page(FIXTURE.read_text())

    assert len(charges) == 12
    assert charge("112-0000005-0000005", date(2026, 9, 26), "-47.47", pending=True) in charges
    gift_card = "Amazon Gift Card"
    assert charge("111-0000003-0000003", date(2026, 9, 15), "+195.92", card=gift_card) in charges
    assert charge("112-0000002-0000002", date(2026, 9, 7), "-15.00") in charges  # shares a day
    mastercard = "Mastercard ****5555"
    assert charge("111-0000006-0000006", date(2026, 9, 7), "-1249.99", card=mastercard) in charges
    assert charge("111-0000009-0000009", date(2026, 9, 10), "-56.24", currency="CA$", site="ca") in charges
    whole_foods = "00000000-0000-4000-8000-000000000010"  # in store, so not a link
    assert charge(whole_foods, date(2026, 9, 12), "-34.62", site=None) in charges


def test_overlapping_pages_count_each_charge_once(tmp_path):
    for name in ("first.html", "again.html"):
        shutil.copy(FIXTURE, tmp_path / name)

    assert sorted(load_charges(tmp_path), key=repr) == sorted(
        parse_page(FIXTURE.read_text()), key=repr
    )


@pytest.mark.parametrize(
    "old, new",
    [
        ("apx-transactions-line-item-component-container", "renamed"),
        ("-$8.70", "-8.70 USD"),
    ],
)
def test_rejects_evolved_page(old, new):
    with pytest.raises(PageFormatError):
        parse_page(FIXTURE.read_text().replace(old, new))
