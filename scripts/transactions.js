// Save your Amazon transactions as JSON, back to a date you choose.
//
// Open amazon.com's Your Payments > Transactions, then paste this into the browser's
// developer console within 30 minutes (the page's token expires). It asks Amazon for
// the same pages the transactions page loads as you scroll, and downloads the result.
(async () => {
  // Amazon's page seems to silence console.log, so borrow an untouched console from a new frame.
  const frame = document.body.appendChild(document.createElement("iframe"));
  frame.style.display = "none";
  const { console } = frame.contentWindow;
  const ENDPOINT = "/payments-portal/data/iris/live/v1/data/manage/get-transactions";
  const since = prompt("Save transactions back to which date? (YYYY-MM-DD)");
  if (!/^\d{4}-\d\d-\d\d$/.test(since ?? "")) throw new Error(`not a date: ${since}`);

  const { props } = JSON.parse(document.getElementById("__NEXT_DATA__").textContent);
  const { token, state } = props.pageProps;
  const first = state.transactionResponseState;
  const login = document
    .getElementById("nav-link-accountList-nav-line-1")
    .textContent.trim()
    .replace(/^Hello, /, "");

  const transactions = [...first.visibleTransactionResponse.transactionList];
  let key = first.lastEvaluatedPageKey;
  const appTrace = "A" + crypto.randomUUID().replaceAll("-", "");
  const day = (t) => new Date(`${t.formattedDate} UTC`).toISOString().slice(0, 10);
  const range = (list) => (list.length ? `${day(list.at(-1))} to ${day(list[0])}` : "none");
  console.log(`${login}: ${transactions.length} transactions on the page, ${range(transactions)}`);

  while (key && day(transactions.at(-1)) >= since) {
    const response = await fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-amzn-upx-token": token },
      body: JSON.stringify({
        type: "GetTransactions",
        locale: "en_US",
        surfaceInfo: {
          surfaceType: "desktop",
          clientApplicationType: "browser",
          surfaceFeatures: [],
          userAgent: navigator.userAgent,
        },
        requestTraceId: crypto.randomUUID().replaceAll("-", "").slice(0, 20).toUpperCase(),
        applicationInstanceTraceId: appTrace,
        transactionsViewRequest: { filtersControls: { includeFilters: true } },
        exclusiveStartKey: key,
        widgetName: "ViewTransactions",
      }),
    });
    const body = await response.json();
    if (!response.ok || body.responseCode !== "success") {
      throw new Error(`Amazon said ${response.status} ${JSON.stringify(body).slice(0, 300)}`);
    }
    const page = body.displayResponse.transactionsList;
    transactions.push(...page);
    key = body.displayResponse.lastEvaluatedKey;
    console.log(`got ${page.length} more, ${range(page)} (${transactions.length} so far)`);
    await new Promise((resolve) => setTimeout(resolve, 500));
  }

  console.log(`saving ${transactions.length} transactions, ${range(transactions)}${key ? "" : " (all of them)"}`);
  const data = { login, saved: new Date().toISOString(), since, complete: !key, transactions };
  const span = [transactions.at(-1), transactions[0]].map((t) => day(t).replaceAll("-", ""));
  Object.assign(document.createElement("a"), {
    href: URL.createObjectURL(new Blob([JSON.stringify(data, null, 1)], { type: "application/json" })),
    download: `transactions_${login.toLowerCase()}_${span.join("-")}.json`,
  }).click();
})().catch((error) => alert(`Saving transactions failed: ${error.message}`));
