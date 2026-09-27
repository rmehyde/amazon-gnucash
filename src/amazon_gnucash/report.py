"""Write the orders left to do by hand as a web page, grouped by Amazon login."""

from datetime import date
from html import escape
from itertools import groupby
from pathlib import Path

from amazon_gnucash.model import Charge, Item
from amazon_gnucash.reconcile import Escalated

STYLE = """
:root { --ink: #1d1d1f; --muted: #6e6e73; --line: #d9d9de; --paper: #fff; --link: #0b62c4; }
@media (prefers-color-scheme: dark) {
  :root { --ink: #f2f2f5; --muted: #a1a1a8; --line: #3a3a40; --paper: #161618; --link: #6cb0ff; }
}
body { font: 15px/1.45 system-ui, sans-serif; color: var(--ink); background: var(--paper);
       max-width: 52rem; margin: 2rem auto; padding: 0 1rem; }
h1 { font-size: 1.4rem; margin-bottom: 0; }
h2 { font-size: 1.15rem; margin-top: 2.5rem; border-bottom: 1px solid var(--line); }
h3 { font-size: 1rem; margin: 0; font-family: ui-monospace, monospace; }
a { color: var(--link); }
article { margin: 1.25rem 0; padding-left: 0.75rem; border-left: 3px solid var(--line); }
.muted, .kind, .items { color: var(--muted); }
.kind { font: normal 0.9rem system-ui, sans-serif; margin-left: 0.4rem; }
.reason { margin: 0.2rem 0 0.5rem; font-weight: 600; }
table { border-collapse: collapse; }
td { padding: 0.1rem 1.5rem 0.1rem 0; vertical-align: top; }
td.amount { text-align: right; font-variant-numeric: tabular-nums; }
"""


def write_report(escalations: list[Escalated], path: Path, since: date, until: date) -> Path:
    ordered = sorted(escalations, key=lambda e: (e.order.login, _first_date(e)))
    sections = [
        f"<section><h2>{escape(login)}</h2>{''.join(map(_order, group))}</section>"
        for login, group in groupby(ordered, key=lambda e: e.order.login)
    ]
    path.write_text(
        "<!doctype html>\n<html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>Amazon escalations</title><style>{STYLE}</style></head><body>"
        f"<h1>Amazon orders to do by hand</h1>"
        f"<p class='muted'>Charged {since} to {until}: {len(escalations)} orders</p>"
        f"{''.join(sections) or '<p>Nothing to do by hand.</p>'}</body></html>\n",
        encoding="utf-8",
    )
    return path


def _order(escalation: Escalated) -> str:
    order = escalation.order
    title = escape(order.order_id)
    if order.link:
        title = f"<a href='{escape(order.link)}'>{title}</a>"
    items = "".join(_row(escape(item.name), _item_total(item)) for item in order.items)
    return (
        f"<article><h3>{title} <span class='kind'>{order.kind}</span></h3>"
        f"<p class='reason'>{escape(escalation.reason)}</p>"
        f"<table>{''.join(_row(*_charge(charge)) for charge in order.charges)}</table>"
        + (f"<table class='items'>{items}</table>" if items else "")
        + "</article>"
    )


def _charge(charge: Charge) -> tuple[str, ...]:
    status = " (pending)" if charge.pending else ""
    sign = "+" if charge.amount > 0 else "−"
    amount = f"{sign}{charge.currency}{abs(charge.amount):,.2f}"
    return f"{charge.date}{status}", escape(charge.card), amount


def _item_total(item: Item) -> str:
    return f"{item.total:,.2f} {item.currency}"


def _row(*cells: str) -> str:
    *text, amount = cells
    return "<tr>" + "".join(f"<td>{c}</td>" for c in text) + f"<td class='amount'>{amount}</td></tr>"


def _first_date(escalation: Escalated) -> date:
    return min(charge.date for charge in escalation.order.charges)
