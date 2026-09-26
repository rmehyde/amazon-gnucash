from datetime import date
from pathlib import Path

from finances.orders import gather
from finances.parse.export import load_items
from finances.parse.transactions import parse_page

FIXTURES = Path(__file__).parent / "fixtures"


def test_gathers_orders_charged_since():
    items = load_items(FIXTURES / "order-history.csv")
    charges = parse_page((FIXTURES / "transactions.html").read_text())

    orders = gather(items, charges, since=date(2026, 1, 1))

    # Leaves out the 2019 order (never charged here) and the one charged in 2025.
    assert {o.order_id: (len(o.items), len(o.charges)) for o in orders} == {
        "111-0000001-0000001": (1, 1),
        "112-0000002-0000002": (2, 2),  # split across two charges
        "111-0000003-0000003": (1, 2),  # charged, then refunded
        "D01-0000004-0000004": (0, 1),  # digital: not in the export
        "112-0000005-0000005": (1, 1),
        "111-0000006-0000006": (1, 1),
        "111-0000009-0000009": (1, 1),  # in Canadian dollars
        "00000000-0000-4000-8000-000000000010": (0, 1),  # Whole Foods: not in the export
    }
