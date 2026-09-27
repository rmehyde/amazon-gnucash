from datetime import date
from pathlib import Path

from finances.orders import gather
from finances.parse.export import load_retail_items
from finances.parse.transactions import parse_page

FIXTURES = Path(__file__).parent / "fixtures"


def test_gathers_orders_charged_in_window():
    items = load_retail_items(FIXTURES / "Order History.csv")
    charges = parse_page((FIXTURES / "transactions.html").read_text())

    orders = gather(items, charges, since=date(2026, 1, 1), until=date(2026, 9, 25))

    # Leaves out the 2019 order (never charged here), the one charged in 2025,
    # and the one charged on September 26.
    assert {o.order_id: (o.kind, len(o.items), len(o.charges)) for o in orders} == {
        "111-0000001-0000001": ("retail order", 1, 1),
        "112-0000002-0000002": ("retail order", 2, 2),  # split across two charges
        "111-0000003-0000003": ("retail order", 1, 2),  # charged, then refunded
        "D01-0000004-0000004": ("digital order", 0, 1),
        "111-0000006-0000006": ("retail order", 1, 1),
        "111-0000009-0000009": ("retail order", 1, 1),  # in Canadian dollars
        "111-0000011-0000011": ("retail order", 2, 1),
        "00000000-0000-4000-8000-000000000010": ("in-store purchase", 0, 1),  # Whole Foods
    }
