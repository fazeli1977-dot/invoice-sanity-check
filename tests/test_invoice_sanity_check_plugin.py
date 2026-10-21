import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

import pytest

SOURCE_DIR = Path(__file__).parents[1] / "executas" / "invoice-sanity-check"
sys.path.insert(0, str(SOURCE_DIR))

from invoice_sanity_check_plugin import check_invoice, invoke, money


def valid_invoice():
    return {
        "invoice_number": "INV-2026-001",
        "items": [
            {"quantity": 2, "unit_price": 10.00, "amount": 20.00},
            {"quantity": 3, "unit_price": 5.50, "amount": 16.50},
        ],
        "subtotal": 36.50,
        "tax": 6.57,
        "total": 43.07,
    }


def test_valid_invoice():
    result = check_invoice(valid_invoice())

    assert result["invoice_number"] == "INV-2026-001"
    assert result["valid"] is True
    assert result["issues"] == []
    assert result["calculated_subtotal"] == "36.50"
    assert result["expected_total"] == "43.07"


def test_subtotal_mismatch_is_reported():
    invoice = valid_invoice()
    invoice["subtotal"] = 36.00

    result = check_invoice(invoice)

    assert result["valid"] is False
    assert any("Stated subtotal" in issue for issue in result["issues"])


def test_total_mismatch_is_reported():
    invoice = valid_invoice()
    invoice["total"] = 44.00

    result = check_invoice(invoice)

    assert result["valid"] is False
    assert any("Stated total" in issue for issue in result["issues"])


def test_item_amount_mismatch_is_reported():
    invoice = valid_invoice()
    invoice["items"][0]["amount"] = 19.99

    result = check_invoice(invoice)

    assert result["valid"] is False
    assert any("Item 1" in issue for issue in result["issues"])
    assert any("does not match calculated amount 20.00" in issue for issue in result["issues"])


def test_decimal_rounding_uses_half_up():
    assert money("10.005") == money("10.01")
    assert money("2.675") == money("2.68")


def test_boolean_is_not_a_valid_amount():
    with pytest.raises(ValueError, match="Boolean is not a valid amount"):
        money(True)


def test_empty_invoice_number_is_rejected():
    invoice = valid_invoice()
    invoice["invoice_number"] = "   "

    with pytest.raises(ValueError, match="invoice_number is required"):
        check_invoice(invoice)


def test_invalid_items_count_is_rejected():
    invoice = valid_invoice()
    invoice["items"] = []

    with pytest.raises(ValueError, match="1 to 100 entries"):
        check_invoice(invoice)


def test_ping_invoke():
    result = invoke("ping", {})

    assert result == {"success": True, "data": {"pong": True}}


def test_invoke_returns_validation_error_without_raising():
    invoice = valid_invoice()
    invoice["invoice_number"] = ""

    result = invoke("check_invoice", invoice)

    assert result["success"] is False
    assert result["error"] == "invoice_number is required"


def test_binary_distribution_urls_match_release_assets():
    executa = json.loads((SOURCE_DIR / "executa.json").read_text(encoding="utf-8"))
    tool_id = executa["tool_id"]
    distribution = executa["distribution"]

    assert distribution["active"] == "binary"
    binary = distribution["profiles"]["binary"]
    assert binary["executable_name"] == tool_id
    assert set(binary["binary_urls"]) == {
        "darwin-arm64",
        "darwin-x86_64",
        "linux-x86_64",
        "windows-x86_64",
    }

    release_tag = f'{executa["slug"]}-v{executa["version"]}'
    for platform, asset in binary["binary_urls"].items():
        archive_name = f"{tool_id}-{platform}.tar.gz"
        parsed_url = urlsplit(asset["url"])

        assert parsed_url.netloc == "github.com"
        assert parsed_url.path.endswith(
            f"/releases/download/{release_tag}/{archive_name}"
        )
        expected_entrypoint = tool_id + (".exe" if platform == "windows-x86_64" else "")
        assert asset["entrypoint"] == expected_entrypoint
