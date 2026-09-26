"""Parse the order history CSV from Amazon's "Request Your Data" export."""

from pathlib import Path

import polars as pl

from finances.model import Item

COLUMNS = {
    "Order ID": "order_id",
    "ASIN": "asin",
    "Product Name": "name",
    "Department": "department",
    "Original Quantity": "quantity",
    "Currency": "currency",
    "Total Amount": "total",
    "Order Status": "order_status",
}


class ExportFormatError(ValueError):
    pass


def load_items(path: Path) -> list[Item]:
    # Read everything as text so amounts reach Decimal without a float in between.
    frame = pl.read_csv(
        path, infer_schema=False, null_values=["Not Available", "Not Applicable"]
    )
    if missing := COLUMNS.keys() - set(frame.columns):
        raise ExportFormatError(f"{path} is missing columns: {sorted(missing)}")
    rows = (
        frame.select(COLUMNS.keys())
        .rename(COLUMNS)
        .with_columns(pl.col("total").str.replace_all(",", ""))  # 1,088.74
        .iter_rows(named=True)
    )
    return [Item(**row) for row in rows]
