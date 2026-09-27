"""Parse the order CSVs from Amazon's "Request Your Data" export."""

from decimal import Decimal
from pathlib import Path

import polars as pl

from amazon_gnucash.model import Item

RETAIL = {
    "Order ID": "order_id",
    "ASIN": "asin",
    "Product Name": "name",
    "Department": "department",
    "Original Quantity": "quantity",
    "Currency": "currency",
    "Total Amount": "total",
    "Order Status": "order_status",
}
DIGITAL = [
    "Order ID",
    "Digital Order Item ID",
    "ASIN",
    "Product Name",
    "Quantity Ordered",
    "Base Currency Code",
    "Transaction Amount",
    "Order Status",
    "Subscription Order Type",
]


class ExportFormatError(ValueError):
    pass


def load_retail_items(path: Path) -> list[Item]:
    """Items from "Order History.csv", one per line."""
    rows = (
        _read(path, RETAIL)
        .select(RETAIL.keys())
        .rename(RETAIL)
        .with_columns(pl.col("total").str.replace_all(",", ""))  # 1,088.74
        .iter_rows(named=True)
    )
    return [Item(**row) for row in rows]


def load_digital_items(path: Path) -> list[Item]:
    """Items from "Digital Content Orders.csv", each spread over price, coupon and tax lines."""
    rows = (
        _read(path, DIGITAL)
        .filter(pl.col("Order Status") == "SUCCESS")  # cancelled items were never charged
        .group_by("Digital Order Item ID", maintain_order=True)
        .agg(pl.all())
        .iter_rows(named=True)
    )
    return [_digital_item(lines) for lines in rows]


def _digital_item(lines: dict[str, list]) -> Item:
    """One item from its lines, each column a list over them."""
    asin = lines["ASIN"][0]
    names = [name for name in lines["Product Name"] if name]
    return Item(
        order_id=lines["Order ID"][0],
        asin=asin,
        name=names[0] if names else f"Unnamed item ({asin})",
        # Digital items have no department, so say what kind of purchase it was.
        department="Subscription" if any(lines["Subscription Order Type"]) else "Digital",
        quantity=lines["Quantity Ordered"][0],
        currency=lines["Base Currency Code"][0],
        total=sum(map(Decimal, lines["Transaction Amount"])),
        order_status=lines["Order Status"][0],
    )


def _read(path: Path, columns) -> pl.DataFrame:
    # Read everything as text so amounts reach Decimal without a float in between.
    frame = pl.read_csv(
        path, infer_schema=False, null_values=["Not Available", "Not Applicable"]
    )
    if missing := set(columns) - set(frame.columns):
        raise ExportFormatError(f"{path} is missing columns: {sorted(missing)}")
    return frame
