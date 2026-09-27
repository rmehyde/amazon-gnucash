"""Write transactions for GnuCash's multi-split CSV import, one file per account."""

import csv
import re
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from finances.config import Config
from finances.reconcile import Transaction

HEADER = ["Date", "Transaction ID", "Description", "Notes", "Account", "Memo", "Amount"]


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
    description = (
        f"Amazon {'Refund' if refund else 'Order'} {charge.order_id}"
        f" ({len(items)} item{'s' if len(items) != 1 else ''})"
    )
    payer = config.payers.get(charge.login, charge.login)
    return [
        [charge.date, number, description, payer, transaction.account, "", _money(charge.amount)],
        *(
            [charge.date, number, "", "", config.uncategorized, item.name,
             _money(-item.total if refund else item.total)]
            for item in items
        ),
    ]


def _slug(account: str) -> str:
    """The account's own name, for a file name: "Liabilities:Travel Card" -> "travel-card"."""
    return re.sub(r"[^a-z0-9]+", "-", account.rsplit(":", 1)[-1].lower()).strip("-")


def _money(amount: Decimal) -> str:
    return f"{amount:.2f}"
