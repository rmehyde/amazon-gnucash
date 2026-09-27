"""Write transactions for GnuCash's multi-split CSV import, one file per account."""

import csv
import re
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from finances.config import Config
from finances.model import Item
from finances.reconcile import Transaction

HEADER = ["Date", "Transaction ID", "Description", "Notes", "Account", "Memo", "Amount"]
# Where a product's name gives way to its sales pitch: "Magnetic Hooks, 4 Pack".
# A dash only counts after a space, so "Wi-Fi" and "4-Pack" stay whole.
PITCH = re.compile(r"\s*[,|]|\s+[\-‐‑‒–—―]|\s*\bwith\b", re.IGNORECASE)


def write_imports(
    transactions: list[Transaction], config: Config, folder: Path, prefix: str
) -> list[Path]:
    by_account = defaultdict(list)
    for transaction in transactions:
        by_account[transaction.account].append(transaction)
    paths = {account: folder / f"{prefix}{_slug(account)}.csv" for account in by_account}
    if len(set(paths.values())) < len(paths):
        raise ValueError(f"accounts would share a file name: {sorted(paths)}")

    for account, path in paths.items():
        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file, lineterminator="\n")
            writer.writerow(HEADER)
            dated = sorted(by_account[account], key=lambda t: t.charge.date)
            for number, transaction in enumerate(dated, 1):
                writer.writerows(_rows(transaction, number, config))
    return list(paths.values())


def _rows(transaction: Transaction, number: int, config: Config) -> list[list]:
    """The card's split, then a split per item that balances it."""
    charge, items = transaction.charge, transaction.items
    refund = charge.amount > 0
    title = f"Amazon {'Refund' if refund else 'Order'} {charge.order_id}"
    description = (
        f"{title}: {shorten(items[0].name)}" if len(items) == 1 else f"{title} ({len(items)} items)"
    )
    payer = config.payers.get(charge.login, charge.login)
    return [
        [charge.date, number, description, payer, transaction.account, "", _money(charge.amount)],
        *(
            [charge.date, number, "", "", config.uncategorized, _memo(item),
             _money(-item.total if refund else item.total)]
            for item in items
        ),
    ]


def shorten(name: str) -> str:
    """The name up to its first comma, spaced dash, pipe or "with" that leaves something."""
    cuts = (match.start() for match in PITCH.finditer(name) if match.start() > 0)
    return name[: next(cuts, len(name))]


def _memo(item: Item) -> str:
    """The product, after Amazon's department for it: "Paperback: The Paper Moon"."""
    name = shorten(item.name)
    return f"{item.department}: {name}" if item.department else name


def _slug(account: str) -> str:
    """The account's own name, for a file name: "Liabilities:Travel Card" -> "travel-card"."""
    return re.sub(r"[^a-z0-9]+", "-", account.rsplit(":", 1)[-1].lower()).strip("-")


def _money(amount: Decimal) -> str:
    return f"{amount:.2f}"
