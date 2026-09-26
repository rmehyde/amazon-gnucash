from decimal import Decimal
from pathlib import Path

import polars as pl
import pytest

from finances.model import Item
from finances.parse.export import ExportFormatError, load_items

FIXTURE = Path(__file__).parent / "fixtures" / "order-history.csv"


def test_loads_items():
    items = load_items(FIXTURE)

    assert len(items) == 9
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


def test_rejects_export_missing_a_column(tmp_path):
    evolved = tmp_path / "evolved.csv"
    pl.read_csv(FIXTURE, infer_schema=False).drop("Total Amount").write_csv(evolved)

    with pytest.raises(ExportFormatError, match="Total Amount"):
        load_items(evolved)
