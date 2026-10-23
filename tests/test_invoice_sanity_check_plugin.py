import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

import pytest

SOURCE_DIR = Path(__file__).parents[1] / "executas" / "invoice-sanity-check"
sys.path.insert(0, str(SOURCE_DIR))

from invoice_sanity_check_plugin import MANIFEST, check_invoice, dispatch, invoke, money


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


def test_describe_matches_executa_protocol():
    executa = json.loads((SOURCE_DIR / "executa.json").read_text(encoding="utf-8"))
    described = dispatch({"method": "describe"})

    assert described["name"] == executa["tool_id"]
    assert described["version"] == executa["version"]
    for tool in described["tools"]:
        assert isinstance(tool["parameters"], list)
        for parameter in tool["parameters"]:
            assert {"name", "type", "description"} <= set(parameter)
    shipped = json.loads((SOURCE_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert shipped == json.loads(json.dumps(MANIFEST))


def test_versions_are_consistent():
    app = json.loads((SOURCE_DIR.parents[1] / "app.json").read_text(encoding="utf-8"))
    executa = json.loads((SOURCE_DIR / "executa.json").read_text(encoding="utf-8"))
    assert app["version"] == executa["version"] == MANIFEST["version"]


def test_fractional_quantity_is_not_rounded_to_cents():
    result = check_invoice(
        {
            "invoice_number": "INV-2",
            "items": [{"quantity": 0.333, "unit_price": 3, "amount": 1.00}],
            "subtotal": 1.00,
            "total": 1.00,
        }
    )
    assert result["valid"] is True


def test_tax_rate_is_applied_to_calculated_subtotal():
    invoice = valid_invoice()
    invoice.pop("tax")
    invoice["tax_rate"] = 18
    invoice["total"] = 43.07
    result = check_invoice(invoice)
    assert result["valid"] is True
    assert result["calculated_tax"] == "6.57"


def test_wrong_tax_for_rate_is_reported():
    invoice = valid_invoice()
    invoice["tax_rate"] = 10
    result = check_invoice(invoice)
    assert result["valid"] is False
    assert any("Stated tax" in issue for issue in result["issues"])


def test_optional_subtotal_and_tax_may_be_omitted():
    result = check_invoice(
        {
            "invoice_number": "INV-3",
            "items": [{"quantity": 1, "unit_price": 9.99, "amount": 9.99}],
            "total": 9.99,
        }
    )
    assert result["valid"] is True


def test_invalid_tax_rate_is_rejected():
    invoice = valid_invoice()
    invoice["tax_rate"] = 150
    with pytest.raises(ValueError, match="tax_rate"):
        check_invoice(invoice)