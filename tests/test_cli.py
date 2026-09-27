from datetime import date
from pathlib import Path

import pytest
from selectolax.parser import HTMLParser

from finances.cli import find_inputs, run
from finances.config import load_config

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def written(tmp_path):
    """What a September run over the fixtures writes, by file name."""
    _, paths = run(
        folder=FIXTURES,
        config=load_config(FIXTURES / "amazon.toml"),
        since=date(2026, 9, 1),
        until=date(2026, 12, 31),
        out=tmp_path,
    )
    return {path.name: path.read_text() for path in paths}


def test_writes_an_import_per_account(written):
    # The desk's August charge is left out: its order is in September's run only
    # for the refund, and the charge belongs to August's run.
    assert {name: text for name, text in written.items() if name.endswith(".csv")} == {
        "amazon_20260901-20261231_visa.csv": """\
Date,Transaction ID,Description,Notes,Account,Memo,Amount
2026-09-02,1,Amazon Order 111-0000001-0000001: Wooden Spoons,PAT DOE,Liabilities:Visa,,-8.70
2026-09-02,1,,,Expenses:Amazon Uncategorized,Kitchen: Wooden Spoons,8.70
2026-09-04,2,Amazon Order 112-0000002-0000002: Sink Strainer Basket,PAT DOE,Liabilities:Visa,,-21.33
2026-09-04,2,,,Expenses:Amazon Uncategorized,Tools & Home Improvement: Sink Strainer Basket,21.33
2026-09-07,3,Amazon Order 112-0000002-0000002: Magnetic Hooks,PAT DOE,Liabilities:Visa,,-15.00
2026-09-07,3,,,Expenses:Amazon Uncategorized,Tools & Home Improvement: Magnetic Hooks,15.00
2026-09-20,4,Amazon Order 111-0000011-0000011 (2 items),PAT DOE,Liabilities:Visa,,-37.00
2026-09-20,4,,,Expenses:Amazon Uncategorized,Kitchen: Stovetop Tea Kettle,27.21
2026-09-20,4,,,Expenses:Amazon Uncategorized,Kitchen: Kettle Descaler,9.79
""",
        "amazon_20260901-20261231_amazon-balance.csv": """\
Date,Transaction ID,Description,Notes,Account,Memo,Amount
2026-09-15,1,Amazon Refund 111-0000003-0000003: Standing Desk Frame,PAT DOE,Assets:Amazon Balance,,195.92
2026-09-15,1,,,Expenses:Amazon Uncategorized,Office Products: Standing Desk Frame,-195.92
""",
    }


def test_reports_orders_to_do_by_hand(written):
    page = HTMLParser(written["amazon_20260901-20261231_escalations.html"])

    # Pending and skipped orders aren't listed; the rest are, by login, then date.
    assert [
        (
            section.css_first("h2").text(),
            [
                (
                    order.css_first("h3").text(),
                    (link := order.css_first("h3 a")) and link.attributes["href"],
                    order.css_first(".reason").text(),
                )
                for order in section.css("article")
            ],
        )
        for section in page.css("section")
    ] == [
        (
            "Pat",
            [
                (
                    "111-0000009-0000009 retail order",
                    "https://www.amazon.ca/gp/css/summary/edit.html?orderID=111-0000009-0000009",
                    "not in USD",
                ),
                (
                    "00000000-0000-4000-8000-000000000010 in-store purchase",
                    None,
                    "not in export",
                ),
            ],
        )
    ]


def test_finds_inputs_anywhere_below_the_folder(tmp_path):
    for path in [
        "sam/transactions-pages/1.html",  # "transaction" in a folder name
        "pat/my-transactions-2.html",  # or in the file name
        "sam/Your Amazon Orders/Order History.csv",
        "pat/Your Amazon Orders/Order History.csv",
        "sam/Your Amazon Orders/Digital Content Orders.csv",
        "sam/Your Amazon Orders/Media/cover.html",  # none of them
        "sam/Your Amazon Orders/Cart History.csv",
    ]:
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).touch()

    found = find_inputs(tmp_path)

    assert [[p.relative_to(tmp_path).as_posix() for p in paths] for paths in found] == [
        ["pat/my-transactions-2.html", "sam/transactions-pages/1.html"],
        [
            "pat/Your Amazon Orders/Order History.csv",
            "sam/Your Amazon Orders/Order History.csv",
        ],
        ["sam/Your Amazon Orders/Digital Content Orders.csv"],
    ]


@pytest.mark.parametrize(
    "missing", ["transaction pages", "order history exports", "digital order exports"]
)
def test_insists_on_every_kind_of_input(tmp_path, missing):
    for kind, name in [
        ("transaction pages", "transactions.html"),
        ("order history exports", "Order History.csv"),
        ("digital order exports", "Digital Content Orders.csv"),
    ]:
        if kind != missing:
            (tmp_path / name).touch()

    with pytest.raises(FileNotFoundError, match=missing):
        find_inputs(tmp_path)
