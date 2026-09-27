from datetime import date
from pathlib import Path

from finances.cli import run
from finances.config import load_config

FIXTURES = Path(__file__).parent / "fixtures"


def test_writes_an_import_per_account(tmp_path):
    _, paths = run(
        pages=FIXTURES,
        exports=[FIXTURES / "order-history.csv"],
        config=load_config(FIXTURES / "amazon.toml"),
        since=date(2026, 9, 1),
        until=date(2026, 12, 31),
        out=tmp_path,
    )

    # The desk's August charge is left out: its order is in September's run only
    # for the refund, and the charge belongs to August's run.
    assert {path.name: path.read_text() for path in paths} == {
        "visa.csv": """\
Date,Transaction ID,Description,Notes,Account,Memo,Amount
2026-09-02,1,Amazon Order 111-0000001-0000001 (1 item),PAT DOE,Liabilities:Visa,,-8.70
2026-09-02,1,,,Expenses:Amazon Uncategorized,"Wooden Spoons, 4 Pack",8.70
2026-09-04,2,Amazon Order 112-0000002-0000002 (1 item),PAT DOE,Liabilities:Visa,,-21.33
2026-09-04,2,,,Expenses:Amazon Uncategorized,Sink Strainer Basket,21.33
2026-09-07,3,Amazon Order 112-0000002-0000002 (1 item),PAT DOE,Liabilities:Visa,,-15.00
2026-09-07,3,,,Expenses:Amazon Uncategorized,"Magnetic Hooks, 4 Pack",15.00
2026-09-20,4,Amazon Order 111-0000011-0000011 (2 items),PAT DOE,Liabilities:Visa,,-37.00
2026-09-20,4,,,Expenses:Amazon Uncategorized,Stovetop Tea Kettle,27.21
2026-09-20,4,,,Expenses:Amazon Uncategorized,Kettle Descaler,9.79
""",
        "amazon-balance.csv": """\
Date,Transaction ID,Description,Notes,Account,Memo,Amount
2026-09-15,1,Amazon Refund 111-0000003-0000003 (1 item),PAT DOE,Assets:Amazon Balance,,195.92
2026-09-15,1,,,Expenses:Amazon Uncategorized,Standing Desk Frame,-195.92
""",
    }
