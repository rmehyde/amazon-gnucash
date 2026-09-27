"""Turn Amazon order history and transactions into GnuCash imports.

    amazon-transactions FOLDER --since 2026-09-01

FOLDER holds, anywhere below it, Amazon's "Order History.csv" and "Digital Content
Orders.csv" exports and saved transaction pages: .html files with "transaction"
somewhere in their path.
"""

import argparse
import logging
import os
from collections import Counter
from datetime import date
from pathlib import Path

from finances.config import Config, load_config
from finances.emit import write_imports
from finances.orders import gather
from finances.parse.export import load_digital_items, load_retail_items
from finances.parse.transactions import load_charges
from finances.reconcile import Escalated, Resolved, Skipped, reconcile
from finances.report import write_report

Outcome = Resolved | Skipped | Escalated

log = logging.getLogger(__name__)
CONFIG = (
    Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    / "amazon-transactions"
    / "config.toml"
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("folder", type=Path, help="where to find the Amazon data")
    parser.add_argument("--since", type=date.fromisoformat, required=True)
    parser.add_argument("--until", type=date.fromisoformat, default=date.today())
    parser.add_argument("--config", type=Path, default=CONFIG, help="default: %(default)s")
    parser.add_argument("--out", type=Path, default=Path("."), help="folder for the CSVs")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    outcomes, paths = run(
        args.folder, load_config(args.config), args.since, args.until, args.out
    )
    tally = Counter[str]()
    for outcome in outcomes:
        match outcome:
            case Resolved():
                tally["resolved"] += 1
            case Skipped(reason=reason):
                tally[f"skipped: {reason}"] += 1
            case Escalated():
                tally[f"escalated: {outcome.why}"] += 1
    for label, count in sorted(tally.items()):
        print(f"{count:4}  {label}")
    for path in paths:
        print(f"wrote {path}")


def run(
    folder: Path, config: Config, since: date, until: date, out: Path
) -> tuple[list[Outcome], list[Path]]:
    pages, retail, digital = find_inputs(folder)
    items = [
        *(item for export in retail for item in load_retail_items(export)),
        *(item for export in digital for item in load_digital_items(export)),
    ]
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
    escalations = [outcome for outcome in outcomes if isinstance(outcome, Escalated)]
    prefix = f"amazon_{since:%Y%m%d}-{until:%Y%m%d}_"
    report = write_report(escalations, out / f"{prefix}escalations.html", since, until)
    return outcomes, [*write_imports(transactions, config, out, prefix), report]


def find_inputs(folder: Path) -> tuple[list[Path], list[Path], list[Path]]:
    """The saved transaction pages, and retail and digital exports, anywhere in `folder`."""
    found = {
        "transaction pages": [
            path
            for path in folder.rglob("*.html")
            if "transaction" in str(path.relative_to(folder)).lower()
        ],
        "order history exports": list(folder.rglob("Order History.csv")),
        "digital order exports": list(folder.rglob("Digital Content Orders.csv")),
    }
    for kind, paths in found.items():
        if not paths:
            raise FileNotFoundError(f"found no {kind} in {folder}")
        log.info(f"{len(paths)} {kind}:")
        for path in sorted(paths):
            log.info(f"  {path.relative_to(folder)}")
    pages, retail, digital = (sorted(paths) for paths in found.values())
    return pages, retail, digital
