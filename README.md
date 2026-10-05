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
├── manifest.json
├── app.json
├── bundle/
│   ├── index.html
│   └── app.js
├── executas/
│   └── invoice-sanity-check-plugin/
│       ├── manifest.json
│       ├── requirements.txt
│       └── invoice_sanity_check_plugin.py
└── README.md
