# Invoice Sanity Check review status — 2026-10-26

## Current candidate

- Project root: `D:\github_backup\invoice-sanity-check`.
- Anna account handle: `alireza` (current browser account).
- App: `@alireza/invoice-sanity-check`, app ID `721`.
- App candidate: `0.3.1`, immutable version ID `1669`, **pending_review**.
- Bundled registry tool: `tool-alireza-invoice-sanity-check-jrqmux6d`.
- Frozen Executa: `0.3.0`, version ID `862`.
- Previous app: `@naomi197/invoice-sanity-check`, app ID `432`, rejected.
- Previous checkout is retained in the nested `invoice-sanity-check/` folder.

## Completed

- Copied the newer 0.3.0 implementation, screenshots, logo and listing into the
  intended project root, preserving the previous nested checkout.
- Migrated the app and bundled Executa registration to the accessible account.
- Corrected model API request names (`systemPrompt`, `maxTokens`) and parsing
  of the standard `{content: {type: "text", text: "..."}}` response.
- Rejects incomplete model output before changing the form; clears optional
  currency when importing a new invoice instead of retaining a previous value.
- Corrected the stale `uv.lock` version and pinned the app's Executa dependency.
- Replaced machine-specific ACL test imports with a pinned npm dependency.
- Added native release-archive verification to the build workflow, including
  persistent JSON-RPC, PASS/FAIL, error recovery and clean shutdown checks.
- Clarified listing behavior, model-assisted text handling and arithmetic scope.

## Evidence

- `python -m pytest -q tests`: 18 passed.
- `npm run validate`: strict Anna validation passed.
- `npm run test:acl`: passed against the new account's resolved tool ID.
- Published Windows archive downloaded from Anna's mirror: SHA256
  `63396aa9ef0a8ca53fe2d38418bac9b6ab82c8add0111c7082c348a91acd86c9`.
- Published Linux archive downloaded from Anna's mirror: SHA256
  `2329defdcaf8805b8a87d62271c50e9b42c8436b913c3a5169b21c89e2d28e3f`.
- `python scripts/verify_executa.py .review/windows.tar.gz`: passed using a fresh
  extraction and one persistent executable process.
- Browser harness used the actual released Windows executable, with the SDK
  and ACL bridge: default invoice PASS; deliberate tax/total mismatches FAIL;
  labeled text with quantity 0.333 PASS.
- Model-import path tested using a canned standard response: fields populated,
  currency cleared, and imported invoice PASS via the actual binary.
- Incomplete model response rejected with an explicit error and no form overwrite.
- Public DoraHacks page contains the detailed description and three screenshots.
- Fresh install of app 0.3.1 succeeded on Cloud Agent #4898. Bundled tool
  `tool-alireza-invoice-sanity-check-jrqmux6d` reports Running, server/agent
  version 0.3.0, with two tools.
- Cloud UI: default invoice PASS (250.00 + 25.00 = 275.00); deliberately
  incorrect invoice FAIL (tax 45.99 vs 46.00, total 505.97 vs 505.98).
- Cloud labeled-text import: CLOUD-FRACTION-001, 0.333 x 3.00 rounded to
  1.00, tax 0.10, total 1.10: PASS.
- Real Anna model-assisted prose import: CLOUD-MODEL-001, subtotal 20.00,
  tax 2.00, total 22.00 USD: PASS through the Cloud executable.
- Submitted candidate 0.3.1 for review. Developer API confirms pending_review,
  review_candidate_version 0.3.1, is_published false.
- Saved and verified the public DoraHacks description: accurate arithmetic
  scope, current Anna handle/version, Cloud verification and pending review.
  All three original screenshots remain present; team GitHub spelling fixed.
- Source fixes committed and pushed to the existing GitHub master branch;
  previous v0.3.0 history preserved (merge commit 41e4f88).

## Required before claiming completion

1. Await Anna reviewers' decision; submission is pending, not approval.

The original account's failure logs are unavailable. The migrated candidate
successfully installs and runs on the new account's real Cloud Agent.
No approval from the competition reviewers is implied by these test results.
