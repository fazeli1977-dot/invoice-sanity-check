import { AnnaAppRuntime } from "/static/anna-apps/_sdk/latest/index.js";

const TOOL_ID = "tool-dev-invoice-sanity-check";

let anna = null;
let itemCounter = 0;

const elements = {
  invoiceNumber: document.getElementById("invoice-number"),
  tax: document.getElementById("tax"),
  total: document.getElementById("total"),
  subtotal: document.getElementById("subtotal"),
  items: document.getElementById("items-container"),
  addItem: document.getElementById("add-item-btn"),
  check: document.getElementById("check-btn"),
  status: document.getElementById("status"),
};

function showStatus(message, type = "info") {
  elements.status.textContent = message;
  elements.status.className = type;
}

function createItemRow(name = "Development Service", qty = "2.5", price = "100.00", amount = "250.00") {
  itemCounter += 1;
  const row = document.createElement("div");
  row.className = "item-row";
  row.innerHTML = `
    <div class="item-grid">
      <div class="field">
        <label>Description</label>
        <input class="item-name" type="text" value="${name}" />
      </div>
      <div class="field">
        <label>Qty</label>
        <input class="item-quantity" type="number" step="0.01" value="${qty}" />
      </div>
      <div class="field">
        <label>Price</label>
        <input class="item-price" type="number" step="0.01" value="${price}" />
      </div>
      <div class="field">
        <label>Amount</label>
        <input class="item-amount" type="number" step="0.01" value="${amount}" />
      </div>
    </div>
    <div style="text-align: right; margin-top: 4px;">
      <button class="btn btn-danger btn-sm remove-item" type="button">Remove</button>
    </div>
  `;

  row.querySelector(".remove-item").addEventListener("click", () => {
    if (elements.items.children.length === 1) {
      showStatus("At least one item is required.", "error");
      return;
    }
    row.remove();
  });

  elements.items.appendChild(row);
}

function numberFrom(input, label) {
  const value = Number(input?.value);
  if (!Number.isFinite(value) || value < 0) {
    throw new Error(`${label} must be a valid non-negative number.`);
  }
  return value;
}

function readInvoice() {
  const invNumber = elements.invoiceNumber ? elements.invoiceNumber.value.trim() : "";
  if (!invNumber) {
    throw new Error("Invoice number is required.");
  }

  const rows = [...elements.items.querySelectorAll(".item-row")];
  if (rows.length === 0) {
    throw new Error("At least one line item is required.");
  }

  const items = rows.map((row, index) => ({
    name: row.querySelector(".item-name")?.value || `Item ${index + 1}`,
    quantity: numberFrom(row.querySelector(".item-quantity"), `Item ${index + 1} Qty`),
    unit_price: numberFrom(row.querySelector(".item-price"), `Item ${index + 1} Price`),
    amount: numberFrom(row.querySelector(".item-amount"), `Item ${index + 1} Amount`),
  }));

  return {
    invoice_number: invNumber,
    items,
    subtotal: numberFrom(elements.subtotal, "Subtotal"),
    tax: numberFrom(elements.tax, "Tax"),
    total: numberFrom(elements.total, "Total"),
  };
}

async function checkInvoice() {
  try {
    const invoice = readInvoice();
    elements.check.disabled = true;
    showStatus("Checking invoice with Executa...", "info");

    if (!anna) {
      throw new Error("Anna SDK not connected.");
    }

    const result = await anna.tools.invoke({
      tool_id: TOOL_ID,
      method: "check_invoice",
      args: invoice,
    });

    const data = result?.data || result;
    if (!data) {
      throw new Error(result?.error || "No response received from tool.");
    }

    if (data.valid) {
      showStatus(
        `✅ VALID INVOICE (${data.invoice_number})\n` +
        `Subtotal: $${data.calculated_subtotal}\n` +
        `Total: $${data.expected_total}`,
        "success"
      );
    } else {
      showStatus(
        `❌ INVALID INVOICE (${data.invoice_number})\n` +
        (data.issues || []).map(i => `• ${i}`).join("\n"),
        "error"
      );
    }
  } catch (error) {
    showStatus(error.message || "An unexpected error occurred.", "error");
  } finally {
    elements.check.disabled = false;
  }
}

async function connect() {
  try {
    anna = await AnnaAppRuntime.connect();
    await anna.window.set_title({ title: "Invoice Sanity Check" });
    showStatus("Ready. Click 'Check Invoice' to validate.", "info");
  } catch (error) {
    showStatus("Dev Mode: Offline SDK loaded.", "info");
  }
}

elements.addItem.addEventListener("click", () => createItemRow("New Item", "1", "0.00", "0.00"));
elements.check.addEventListener("click", checkInvoice);

createItemRow();
connect();
