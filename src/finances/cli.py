"""Turn Amazon order history and transactions into GnuCash imports.

    uv run finances PAGES EXPORT [EXPORT ...] --since 2026-09-01
"""

import argparse
from collections import Counter
from datetime import date
from pathlib import Path

from finances.config import Config, load_config
from finances.emit import write_imports
from finances.orders import gather
from finances.parse.export import load_items
from finances.parse.transactions import load_charges
from finances.reconcile import Escalated, Reason, Resolved, Skipped, reconcile

Outcome = Resolved | Skipped | Escalated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pages", type=Path, help="folder of saved transaction pages")
    parser.add_argument("exports", type=Path, nargs="+", help="order history CSVs")
    parser.add_argument("--since", type=date.fromisoformat, required=True)
    parser.add_argument("--until", type=date.fromisoformat, default=date.today())
    parser.add_argument(
        "--config", type=Path, default=Path.home() / "Documents/Finances/amazon.toml"
    )
    parser.add_argument("--out", type=Path, default=Path("."), help="folder for the CSVs")
    args = parser.parse_args()

    outcomes, paths = run(
        args.pages, args.exports, load_config(args.config), args.since, args.until, args.out
    )
    tally = Counter[str]()
    for outcome in outcomes:
        match outcome:
            case Resolved():
                tally["resolved"] += 1
            case Skipped(reason=reason):
                tally[f"skipped: {reason}"] += 1
            case Escalated(order=order, reason=reason):
                why = f"{reason} ({order.kind})" if reason is Reason.NOT_IN_EXPORT else reason
                tally[f"escalated: {why}"] += 1
                print(f"{order.login}  {order.order_id}  {why}")
    for label, count in sorted(tally.items()):
        print(f"{count:4}  {label}")
    for path in paths:
        print(f"wrote {path}")


def run(
    pages: Path, exports: list[Path], config: Config, since: date, until: date, out: Path
) -> tuple[list[Outcome], list[Path]]:
    items = [item for export in exports for item in load_items(export)]
    orders = gather(items, load_charges(pages), since, until)
    outcomes = [reconcile(order, config) for order in orders]
    # An order is checked against all its charges, but only those in the window are
    # written, so a charge from before `since` isn't imported a second time.
    transactions = [
        transaction
        for outcome in outcomes
        if isinstance(outcome, Resolved)
        for transaction in outcome.transactions
        if since <= transaction.charge.date <= until
    ]
    return outcomes, write_imports(transactions, config, out)
