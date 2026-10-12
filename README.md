# Invoice Sanity Check — Anna AI App

A deterministic invoice validation mini-app and Executa built for the **Anna AI App Builder Program**. It verifies line-item arithmetic, calculates exact sub-totals, applies tax, and cross-checks totals using Python's `decimal.Decimal` engine to eliminate floating-point discrepancies.

## Features
- **Exact Currency Arithmetic**: Powered by Python `Decimal` with `ROUND_HALF_UP` precision.
- **Dynamic Line Items**: Add/remove multiple invoice items with custom descriptions, quantities, and unit prices.
- **Anna App Harness Compatible**: Communicates via standard JSON-RPC over the Anna Browser SDK (`@anna-ai/app-runtime`).
- **Comprehensive Sanity Rules**:
  - `item.amount == item.quantity * item.unit_price`
  - `subtotal == sum(items.amount)`
  - `total == subtotal + tax`
  - Non-empty invoice numbers and non-negative financial values.

## Project Structure
```text
invoice-sanity-check/
├── manifest.json          # App manifest: UI bundle, views, host_api ACL, bundled executa refs
├── app.json               # Listing metadata + bundled_executas handle → path map
├── bundle/
│   ├── index.html         # SPA entry; loads anna-tool-ids.js then app.js
│   └── app.js             # Resolves the tool id from window.__ANNA_TOOL_IDS__
├── executas/
│   └── invoice-sanity-check/
│       ├── executa.json              # Dev identity (tool_id, type, enabled)
│       ├── pyproject.toml            # name + [project.scripts] key == minted tool_id
│       ├── uv.lock
│       └── invoice_sanity_check_plugin.py   # stdio JSON-RPC tool plugin (describe/invoke)
├── tests/
│   └── test_invoice_sanity_check_plugin.py
├── acltest.mjs            # Regression check: bundle tool id vs manifest ACL
└── README.md
```

## How the tool id is wired
The frontend never hardcodes a tool id. `anna-app apps publish` / `anna-app dev`
resolve the `bundled:invoice-sanity-check` handle declared in `manifest.json` to the
server-minted `tool_id` and write `bundle/anna-tool-ids.js`
(`window.__ANNA_TOOL_IDS__`). `bundle/app.js` reads that mapping at runtime, and
`bundle/index.html` loads the sidecar before `app.js`. Keep the `[project].name`
and the `[project.scripts]` key in `executas/invoice-sanity-check/pyproject.toml`
equal to the minted `tool_id`.
