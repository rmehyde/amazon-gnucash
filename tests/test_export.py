from decimal import Decimal
from pathlib import Path

import polars as pl
import pytest

from amazon_gnucash.model import Item
from amazon_gnucash.parse.export import ExportFormatError, load_digital_items, load_retail_items

FIXTURES = Path(__file__).parent / "fixtures"
RETAIL = FIXTURES / "Order History.csv"
DIGITAL = FIXTURES / "Digital Content Orders.csv"


def test_loads_retail_items():
    items = load_retail_items(RETAIL)

    assert len(items) == 11
    assert items[0] == Item(
        order_id="111-0000001-0000001",
        asin="B000000001",
        name="Wooden Spoons, 4 Pack",
        department="Kitchen",
        quantity=1,
        currency="USD",
        total=Decimal("8.70"),
        order_status="Closed",
    )
    assert items[5].total == Decimal("1249.99")  # written "1,249.99"


def test_loads_digital_items():
    def item(order, asin, name, department, total):
        return Item(
            order_id=order,
            asin=asin,
            name=name,
            department=department,
            quantity=1,
            currency="USD",
            total=Decimal(total),
            order_status="SUCCESS",
        )

    # The cancelled cartoon is left out.
    assert load_digital_items(DIGITAL) == [
        item("D01-0000004-0000004", "B0DIGITAL1", "The Paper Moon", "Digital", "3.99"),
        item("D01-0000012-0000012", "B0DIGITAL2", "Tidewater S1", "Digital", "4.35"),  # coupon
        item(
            "D01-0000013-0000013",
            "B0DIGITAL3",
            "Unnamed item (B0DIGITAL3)",
            "Subscription",
            "9.79",
        ),
        item("D01-0000015-0000015", "B0DIGITAL5", "Harbor Lights: Episode 1", "Digital", "2.17"),
        item("D01-0000015-0000015", "B0DIGITAL6", "Harbor Lights: Episode 2", "Digital", "2.17"),
    ]


@pytest.mark.parametrize(
    "load, fixture, column",
    [
        (load_retail_items, RETAIL, "Total Amount"),
        (load_digital_items, DIGITAL, "Transaction Amount"),
    ],
)
def test_rejects_export_missing_a_column(tmp_path, load, fixture, column):
    evolved = tmp_path / "evolved.csv"
    pl.read_csv(fixture, infer_schema=False).drop(column).write_csv(evolved)

    with pytest.raises(ExportFormatError, match=column):
        load(evolved)
