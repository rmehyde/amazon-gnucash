"""Check that each order's items add up to what Amazon charged for it.

    uv run python -m finances.audit PAGES EXPORT [EXPORT ...] --since 2026-01-01

Prints only the orders that don't add up, then a count of each outcome.
"""

import argparse
from collections import Counter
from datetime import date
from pathlib import Path

from finances.model import Order
from finances.orders import gather
from finances.parse.export import load_items
from finances.parse.transactions import load_charges


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pages", type=Path, help="folder of saved transaction pages")
    parser.add_argument("exports", type=Path, nargs="+", help="order history CSVs")
    parser.add_argument("--since", type=date.fromisoformat, required=True)
    parser.add_argument("--until", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()

    items = [item for export in args.exports for item in load_items(export)]
    outcomes = Counter[str]()
    for order in gather(items, load_charges(args.pages), args.since, args.until):
        outcome, detail = check(order)
        outcomes[outcome] += 1
        if outcome != "adds up":
            print(f"{order.order_id}  {outcome}  {detail}".rstrip())
    print(", ".join(f"{count} {outcome}" for outcome, count in outcomes.most_common()))


def check(order: Order) -> tuple[str, str]:
    if not order.items:
        return f"not in export ({order.kind})", ""
    if any(item.currency != "USD" for item in order.items) or any(
        charge.currency != "$" for charge in order.charges
    ):
        return "not in USD", ""
    itemized = sum(item.total for item in order.items)
    charged = -sum(charge.amount for charge in order.charges if charge.amount < 0)
    if itemized == charged:
        return "adds up", ""
    return "differs", f"items {itemized}, charged {charged}, off by {itemized - charged}"


if __name__ == "__main__":
    main()
