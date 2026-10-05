"""Invoice checks for the Anna App. One JSON-RPC request per input line."""

import json
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

MANIFEST = {
    "name": "tool-dev-invoice-sanity-check",
    "version": "0.1.0",
    "tools": [
        {
            "name": "ping",
            "description": "Smoke-test method.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
        {
            "name": "check_invoice",
            "description": "Check invoice line amounts, subtotal, tax, and total.",
            "parameters": {
                "type": "object",
                "properties": {
                    "invoice_number": {"type": "string"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "quantity": {"type": "number"},
                                "unit_price": {"type": "number"},
                                "amount": {"type": "number"},
                            },
                            "required": ["quantity", "unit_price", "amount"],
                        },
                    },
                    "subtotal": {"type": "number"},
                    "tax": {"type": "number"},
                    "total": {"type": "number"},
                },
                "required": ["invoice_number", "items", "subtotal", "tax", "total"],
            },
        },
    ],
}

CENT = Decimal("0.01")


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


def check_invoice(args):
    if not isinstance(args, dict):
        raise ValueError("Arguments must be an object")
    number = args.get("invoice_number")
    if not isinstance(number, str) or not number.strip():
        raise ValueError("invoice_number is required")
    items = args.get("items")
    if not isinstance(items, list) or not 1 <= len(items) <= 100:
        raise ValueError("items must contain 1 to 100 entries")

    issues = []
    calculated_subtotal = Decimal("0.00")
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Item {index} must be an object")
        quantity = money(item["quantity"])
        price = money(item["unit_price"])
        stated_amount = money(item["amount"])
        if quantity < 0 or price < 0 or stated_amount < 0:
            issues.append(f"Item {index}: negative values are not allowed")
        expected_amount = (quantity * price).quantize(CENT, rounding=ROUND_HALF_UP)
        calculated_subtotal += expected_amount
        if stated_amount != expected_amount:
            issues.append(
                f"Item {index}: stated amount {stated_amount} "
                f"does not match calculated amount {expected_amount}"
            )

    subtotal = money(args["subtotal"])
    tax = money(args["tax"])
    total = money(args["total"])
    if subtotal < 0 or tax < 0 or total < 0:
        issues.append("Subtotal, tax, and total must not be negative")
    if subtotal != calculated_subtotal:
        issues.append(
            f"Stated subtotal {subtotal} does not match "
            f"calculated subtotal {calculated_subtotal}"
        )
    expected_total = subtotal + tax
    if total != expected_total:
        issues.append(
            f"Stated total {total} does not match "
            f"subtotal plus tax {expected_total}"
        )

    return {
        "invoice_number": number.strip(),
        "valid": not issues,
        "issues": issues,
        "calculated_subtotal": str(calculated_subtotal),
        "expected_total": str(expected_total),
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


def main():
    for line in sys.stdin:
        if not line.strip():
            continue
        request_id = None
        try:
            request = json.loads(line)
            request_id = request.get("id")
            method = request.get("method")
            if method == "describe":
                result = MANIFEST
            elif method == "health":
                result = {"status": "ready"}
            elif method == "invoke":
                params = request["params"]
                result = invoke(params["tool"], params.get("arguments", {}))
            else:
                raise ValueError(f"unknown rpc: {method}")
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
