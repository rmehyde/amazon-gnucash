"""Parse saved copies of Amazon's Your Payments > Transactions page."""

import re
from collections import Counter
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from selectolax.parser import HTMLParser, Node

from finances.model import Charge

SECTIONS = {"In Progress": True, "Completed": False}  # heading -> pending
AMOUNT = re.compile(r"([+-])(\D+)([\d,]+\.\d\d)")
CARD = re.compile(r"(Amazon Gift Card|.+ \*{4}\d{4})")
ORDER = re.compile(r"(?:Refund: )?Order #(\S+)")
GREETING = re.compile(r"Hello, (.+)")


class PageFormatError(ValueError):
    pass


def load_charges(pages: list[Path]) -> list[Charge]:
    """Every charge across the pages.

    Pages downloaded at different times overlap, so a charge counts as many times
    as it appears on any single page, not the sum across pages.
    """
    merged = Counter[Charge]()
    for page in pages:
        merged |= Counter(parse_page(page.read_text(encoding="utf-8")))
    return list(merged.elements())


def parse_page(html: str) -> list[Charge]:
    tree = HTMLParser(html)
    login = _text(GREETING, tree.css_first("#nav-link-accountList-nav-line-1"))
    charges = [
        _charge(item, login, day, pending)
        for pending, section in _sections(tree)
        for day, item in _dated_items(section)
    ]
    if not charges:
        raise PageFormatError("found no transactions on the page")
    return charges


def _sections(tree: HTMLParser):
    for group in tree.css(".a-box-group"):
        heading = group.css_first(".apx-transactions-sleeve-header-container")
        if heading is None:
            continue
        title = heading.text(strip=True)
        if title not in SECTIONS:
            raise PageFormatError(f"unknown section {title!r}")
        yield SECTIONS[title], group


def _dated_items(section: Node):
    # Each date heading is followed by a sibling holding that day's line items.
    for heading in section.css(".apx-transaction-date-container"):
        day = datetime.strptime(heading.text(strip=True), "%B %d, %Y").date()
        sibling = heading.next
        while sibling is not None and sibling.tag == "-text":
            sibling = sibling.next
        if sibling is None:
            raise PageFormatError(f"no transactions follow the {day} heading")
        for item in sibling.css(".apx-transactions-line-item-component-container"):
            yield day, item


def _charge(item: Node, login: str, day: date, pending: bool) -> Charge:
    sign, currency, digits = _match(AMOUNT, item.css_first(".a-span-last span")).groups()
    # The order (a link, or text for in-store purchases), then usually the merchant.
    rows = item.css(".a-span12 > *")
    if not 1 <= len(rows) <= 2:
        raise PageFormatError(f"expected an order and a merchant, found {len(rows)} rows")
    return Charge(
        login=login,
        order_id=_text(ORDER, rows[0]),
        link=rows[0].attributes.get("href"),
        merchant=rows[1].text(strip=True) if len(rows) == 2 else None,
        card=_text(CARD, item.css_first(".a-span9 span")),
        date=day,
        amount=Decimal(sign + digits.replace(",", "")),
        currency=currency,
        pending=pending,
    )


def _text(pattern: re.Pattern, node: Node | None) -> str:
    """The pattern's one group in the node's text."""
    return _match(pattern, node).group(1)


def _match(pattern: re.Pattern, node: Node | None) -> re.Match:
    """The pattern matched against the node's text, or an error naming what was found."""
    text = node.text(strip=True) if node is not None else ""
    if not (match := pattern.fullmatch(text)):
        raise PageFormatError(f"expected {pattern.pattern!r}, found {text!r}")
    return match
