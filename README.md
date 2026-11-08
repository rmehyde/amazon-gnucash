# amazon-gnucash

Turn your Amazon order history into [GnuCash](https://www.gnucash.org) CSV imports,
one transaction per card charge, split per item.

Amazon charges your card per shipment, not per order, and one card charge can cover
several unrelated items. `amazon-gnucash` works out which items each charge paid for and
writes GnuCash transactions that match your card statement to the cent, each split into
the products it bought. When you later import the statement, GnuCash's matcher pairs its
lines with these transactions, so the items are already there.

Everything is deterministic: no scraping, no logging in, and nothing is written to your
GnuCash book. You import the CSVs yourself.

## What you need

- **Amazon's data export.** Request "Your Orders" at *Account › Request Your
  Information*. The zip includes `Order History.csv` and `Digital Content Orders.csv`.
- **Your transactions, saved as JSON.** Amazon's export doesn't say which items went on
  which charge, but *Your Payments › Transactions* does. Open that page and, within 30
  minutes, paste [`scripts/transactions.js`](scripts/transactions.js) into your
  browser's developer console. It asks how far back to go, then downloads the
  transactions as, for example, `transactions_pat_20260402-20261107.json`.

Put everything in one folder, in any layout, with one export and at least one
transactions file per Amazon account. Transactions files may overlap.

## Install

```sh
uv tool install git+https://github.com/rmehyde/amazon-gnucash
```

## Configure

`~/.config/amazon-gnucash/config.toml` (or pass `--config`):

```toml
uncategorized = "Expenses:Amazon Uncategorized"  # where item splits go
skip = ["Visa ****1234"]              # cards to leave out
skip_merchants = ["Whole Foods"]      # merchants to leave out, by name start

[accounts]  # payment method, as Amazon names it, then "****" and its last digits -> GnuCash account
"American Express Gold Card ****1005" = "Liabilities:Amex"
"Amazon Gift Card" = "Assets:Receivables:Amazon Balance"

[payers]  # Amazon account -> who paid, written to each transaction's Notes
Pat = "PAT DOE"
```

## Run

```sh
amazon-gnucash path/to/amazon-folder --since 2026-09-01 [--until 2026-09-30]
```

This writes, into the current folder (or `--out`):

- `amazon_20260901-20260930_<gnucash-account>.csv`: one GnuCash import per account.
- `amazon_20260901-20260930_escalations.html`: the orders left for you to enter by
  hand, with links to them on Amazon and the reason each one needed a person.

Only charges inside the dates are written out, so consecutive runs don't import a charge
twice. Amazon dates charges in UTC, so a charge made in the evening can be dated a day
later than on your card statement.

## Import into GnuCash

*File › Import › Import Transactions from CSV*, then:

- Tick **Multi-split**. Skip 1 header line, and set the date format to `y-m-d`.
- Map the columns: Date, Transaction ID, Description, Notes, Account, Memo, Amount.

Each item lands in your `uncategorized` account, with Amazon's department and a shortened
product name as its memo, ready for you to recategorize.

## What it leaves to you

Orders are never imported in part. An order that can't be fully resolved appears in the
escalations report instead:

- **Foreign currency:** Amazon's data only has the foreign amount, not the dollars your
  card was charged.
- **Split payments:** one shipment paid partly by gift card and partly by card.
- **Ambiguity:** more than one way the items could fit the charges.
- **Unmapped cards:** a payment method your config doesn't mention.

Skipped cards and merchants are left out quietly. Amazon lists a charge only once it has
billed your card, so an order still shipping may be escalated as not adding up until
its remaining charges appear.

---

Amazon® is a registered trademark of Amazon.com, Inc. or its affiliates. This project is
not affiliated with, endorsed by, or sponsored by Amazon.
