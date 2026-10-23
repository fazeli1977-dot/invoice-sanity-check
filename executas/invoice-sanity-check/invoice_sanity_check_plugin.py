"""Invoice checks for the Anna App (JSON-RPC 2.0 over stdio, one request per line)."""

import json
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

TOOL_ID = "tool-naomi197-invoice-sanity-check-qhj8bq39"
VERSION = "0.3.0"

MANIFEST = {
    "name": TOOL_ID,
    "display_name": "Invoice Sanity Check",
    "version": VERSION,
    "description": (
        "Check invoice line amounts, subtotal, tax, and total using exact "
        "Decimal arithmetic. The result of check_invoice is the only pass or fail."
    ),
    "author": "fazeli1977-dot",
    "homepage": "https://github.com/fazeli1977-dot/invoice-sanity-check",
    "category": "productivity",
    "license": "MIT",
    "credentials": [],
    "tools": [
        {
            "name": "ping",
            "description": "Smoke-test method.",
            "parameters": [],
        },
        {
            "name": "check_invoice",
            "description": (
                "Deterministically check invoice line amounts "
                "(quantity x unit price), the subtotal, an optional tax rate "
                "and the total. Returns valid=true/false and a list of issues."
            ),
            "parameters": [
                {
                    "name": "invoice_number",
                    "type": "string",
                    "description": "Invoice number, e.g. INV-2026-001.",
                    "required": True,
                },
                {
                    "name": "items",
                    "type": "array",
                    "description": (
                        "Line items. Each item is an object with quantity, "
                        "unit_price, amount and an optional description."
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "quantity": {"type": "number"},
                            "unit_price": {"type": "number"},
                            "amount": {"type": "number"},
                        },
                        "required": ["quantity", "unit_price", "amount"],
                    },
                    "required": True,
                },
                {
                    "name": "subtotal",
                    "type": "number",
                    "description": "Stated subtotal. Omit to skip the stated-subtotal check.",
                    "required": False,
                },
                {
                    "name": "tax_rate",
                    "type": "number",
                    "description": "Optional tax rate in percent (e.g. 10 for 10%).",
                    "required": False,
                },
                {
                    "name": "tax",
                    "type": "number",
                    "description": "Stated tax amount. Defaults to 0 when no tax_rate is given.",
                    "required": False,
                },
                {
                    "name": "total",
                    "type": "number",
                    "description": "Stated invoice total.",
                    "required": True,
                },
                {
                    "name": "currency",
                    "type": "string",
                    "description": "Optional currency code, e.g. USD. Echoed in the result.",
                    "required": False,
                },
            ],
        },
    ],
    "runtime": {"type": "binary"},
}

CENT = Decimal("0.01")
MAX_ITEMS = 100


def exact(value, label="value"):
    """Parse a number exactly (no cent rounding)."""
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{label}: Boolean or empty value is not a valid number")
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, TypeError):
        raise ValueError(f"Invalid numeric value for {label}: {value!r}") from None
    if not number.is_finite():
        raise ValueError(f"{label} must be finite")
    return number


def money(value):
    if isinstance(value, bool):
        raise ValueError("Boolean is not a valid amount")
    try:
        number = Decimal(str(value))
        if not number.is_finite():
            raise ValueError("Amount must be finite")
        return number.quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError):
        raise ValueError(f"Invalid numeric value: {value!r}") from None


def cents(number):
    return number.quantize(CENT, rounding=ROUND_HALF_UP)


def check_invoice(args):
    if not isinstance(args, dict):
        raise ValueError("Arguments must be an object")
    number = args.get("invoice_number")
    if not isinstance(number, str) or not number.strip():
        raise ValueError("invoice_number is required")
    items = args.get("items")
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_ITEMS:
        raise ValueError(f"items must contain 1 to {MAX_ITEMS} entries")
    if args.get("total") in (None, ""):
        raise ValueError("total is required")

    issues = []
    calculated_subtotal = Decimal("0.00")
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Item {index} must be an object")
        for key in ("quantity", "unit_price", "amount"):
            if item.get(key) in (None, ""):
                raise ValueError(f"Item {index}: {key} is required")
        quantity = exact(item["quantity"], f"Item {index} quantity")
        price = exact(item["unit_price"], f"Item {index} unit_price")
        stated_amount = money(item["amount"])
        if quantity < 0 or price < 0 or stated_amount < 0:
            issues.append(f"Item {index}: negative values are not allowed")
        expected_amount = cents(quantity * price)
        calculated_subtotal += expected_amount
        if stated_amount != expected_amount:
            issues.append(
                f"Item {index}: stated amount {stated_amount} "
                f"does not match calculated amount {expected_amount}"
            )

    stated_subtotal = args.get("subtotal")
    if stated_subtotal not in (None, ""):
        subtotal = money(stated_subtotal)
        if subtotal < 0:
            issues.append("Subtotal must not be negative")
        if subtotal != calculated_subtotal:
            issues.append(
                f"Stated subtotal {subtotal} does not match "
                f"calculated subtotal {calculated_subtotal}"
            )

    tax_rate = None
    if args.get("tax_rate") not in (None, ""):
        tax_rate = exact(args["tax_rate"], "tax_rate")
        if tax_rate < 0 or tax_rate > 100:
            raise ValueError("tax_rate must be between 0 and 100 percent")

    stated_tax = money(args["tax"]) if args.get("tax") not in (None, "") else None
    if stated_tax is not None and stated_tax < 0:
        issues.append("Tax must not be negative")

    calculated_tax = None
    if tax_rate is not None:
        calculated_tax = cents(calculated_subtotal * tax_rate / Decimal(100))
        if stated_tax is not None and stated_tax != calculated_tax:
            issues.append(
                f"Stated tax {stated_tax} does not match "
                f"{tax_rate.normalize():f}% of subtotal ({calculated_tax})"
            )
        tax_used = calculated_tax
    else:
        tax_used = stated_tax if stated_tax is not None else Decimal("0.00")

    total = money(args["total"])
    if total < 0:
        issues.append("Total must not be negative")
    expected_total = calculated_subtotal + tax_used
    if total != expected_total:
        issues.append(
            f"Stated total {total} does not match "
            f"subtotal plus tax {expected_total}"
        )

    return {
        "invoice_number": number.strip(),
        "currency": str(args.get("currency") or "").strip().upper(),
        "valid": not issues,
        "issues": issues,
        "calculated_subtotal": str(calculated_subtotal),
        "calculated_tax": str(tax_used),
        "expected_total": str(expected_total),
        "stated_total": str(total),
    }


def invoke(method, args):
    if method == "ping":
        return {"success": True, "data": {"pong": True}}
    if method == "check_invoice":
        try:
            return {"success": True, "data": check_invoice(args)}
        except (ValueError, KeyError) as error:
            return {"success": False, "error": str(error)}
    return {"success": False, "error": f"unknown method: {method}"}


def dispatch(request):
    method = request.get("method")
    if method == "initialize":
        return {
            "protocolVersion": "2.0",
            "server_info": {
                "name": MANIFEST["display_name"],
                "version": MANIFEST["version"],
            },
            "capabilities": {},
        }
    if method == "describe":
        return MANIFEST
    if method == "health":
        return {"status": "ready", "message": "", "details": {}}
    if method == "invoke":
        params = request.get("params") or {}
        return invoke(params.get("tool", ""), params.get("arguments") or {})
    raise ValueError(f"unknown rpc: {method}")


def main():
    for line in sys.stdin:
        if not line.strip():
            continue
        request_id = None
        try:
            request = json.loads(line)
            request_id = request.get("id")
            result = dispatch(request)
            response = {"jsonrpc": "2.0", "id": request_id, "result": result}
        except Exception as error:
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": str(error)},
            }
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
