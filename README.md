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
├── app.json               # Listing metadata (description, logo, screenshots) + bundled_executas
├── assets/logo.svg        # Store logo
├── screenshots/           # Store listing screenshots
├── .github/workflows/
│   └── build-executa.yml  # PyInstaller per-platform build → GitHub Release assets
├── bundle/
│   ├── index.html         # SPA entry; loads anna-tool-ids.js then app.js
│   └── app.js             # Resolves the tool id from window.__ANNA_TOOL_IDS__
├── executas/
│   └── invoice-sanity-check/
│       ├── executa.json              # Dev identity + `distribution` (binary URLs)
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

## How the tool is installed on an Agent

`executas/invoice-sanity-check/executa.json` carries a `distribution` block. Without
one the Executa is **dev-only**: `anna-app dev` runs it from this directory, but a
published app has no locator and the Agent cannot install it — so a reviewer on a
fresh Cloud Agent sees an error and cannot test any feature.

The active profile is `binary`: the Agent downloads a self-contained PyInstaller
binary per `{os, arch}` from the GitHub Release `invoice-sanity-check-v<version>`,
verified by sha256 (pinned at `apps cut`). `.github/workflows/build-executa.yml`
builds and attaches those assets; run it with **Actions → Build Executa binaries →
Run workflow** (or push a matching tag) before publishing a new version.

The `local` profile is kept for the dev loop (`anna-app apps push --profile local`).
`acltest.mjs` fails if the active profile ever regresses to `local`/dev-only.

Before submitting a release, run `python -m pytest tests/test_invoice_sanity_check_plugin.py`.
The distribution regression test checks that every declared URL uses the current
tool id, version tag, platform archive name, and executable entrypoint. If an app
was already cut with stale Executa metadata, publish a fresh version after its
release assets are publicly downloadable, then cut and submit that version and
verify it with a fresh install.

## Executa protocol notes
`describe` must return a top-level `name` equal to the minted tool id and `parameters` as a **list** of
`{name, type, description, required}` entries (not a JSON-Schema object). The archive-root `manifest.json`
in each release asset uses the same `name`. `tests/` asserts this, and the CI smoke test checks it against the built binary.
