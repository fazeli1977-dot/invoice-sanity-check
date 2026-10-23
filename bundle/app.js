const DEV_FALLBACK_TOOL_ID = "tool-dev-invoice-sanity-check";
const TOOL_ID =
  (typeof window !== "undefined" &&
    window.__ANNA_TOOL_IDS__ &&
    window.__ANNA_TOOL_IDS__["invoice-sanity-check"]) ||
  DEV_FALLBACK_TOOL_ID;

let anna = null;

const $ = (id) => document.getElementById(id);
const elements = {
  paste: $("paste-text"),
  fill: $("fill-btn"),
  sample: $("sample-btn"),
  invoiceNumber: $("invoice-number"),
  currency: $("currency"),
  subtotal: $("subtotal"),
  taxRate: $("tax-rate"),
  tax: $("tax"),
  total: $("total"),
  items: $("items-container"),
  addItem: $("add-item-btn"),
  check: $("check-btn"),
  status: $("status"),
};

const SAMPLE_TEXT = [
  "Invoice INV-2026-014",
  "Design work  3 x 120.00 = 360.00",
  "Hosting  2 x 49.99 = 99.98",
  "Subtotal: 459.98",
  "Tax (10%): 45.99",
  "Total: 505.97",
].join("\n");

function showStatus(message, type = "info") {
  elements.status.textContent = message;
  elements.status.className = type;
}

function createItemRow(values = {}) {
  const { name = "Development Service", qty = "2.5", price = "100.00", amount = "250.00" } = values;
  const row = document.createElement("div");
  row.className = "item-row";
  row.innerHTML = `
    <div class="item-grid">
      <div class="field"><label>Description</label><input class="item-name" type="text" /></div>
      <div class="field"><label>Qty</label><input class="item-quantity" type="number" step="any" /></div>
      <div class="field"><label>Unit price</label><input class="item-price" type="number" step="any" /></div>
      <div class="field"><label>Stated amount</label><input class="item-amount" type="number" step="0.01" /></div>
    </div>
    <div class="item-actions">
      <button class="btn btn-danger btn-sm remove-item" type="button">Remove</button>
    </div>
  `;
  row.querySelector(".item-name").value = name;
  row.querySelector(".item-quantity").value = qty;
  row.querySelector(".item-price").value = price;
  row.querySelector(".item-amount").value = amount;

  row.querySelector(".remove-item").addEventListener("click", () => {
    if (elements.items.children.length === 1) {
      showStatus("At least one item is required.", "error");
      return;
    }
    row.remove();
  });

  elements.items.appendChild(row);
}

function setItems(items) {
  elements.items.replaceChildren();
  for (const item of items) createItemRow(item);
}

function numberFrom(input, label, { optional = false } = {}) {
  const raw = (input?.value ?? "").trim();
  if (optional && raw === "") return undefined;
  const value = Number(raw);
  if (raw === "" || !Number.isFinite(value) || value < 0) {
    throw new Error(`${label} must be a valid non-negative number.`);
  }
  return value;
}

function readInvoice() {
  const invNumber = elements.invoiceNumber.value.trim();
  if (!invNumber) {
    throw new Error("Invoice number is required.");
  }

  const rows = [...elements.items.querySelectorAll(".item-row")];
  if (rows.length === 0) {
    throw new Error("At least one line item is required.");
  }

  const items = rows.map((row, index) => ({
    description: row.querySelector(".item-name").value || `Item ${index + 1}`,
    quantity: numberFrom(row.querySelector(".item-quantity"), `Item ${index + 1} quantity`),
    unit_price: numberFrom(row.querySelector(".item-price"), `Item ${index + 1} unit price`),
    amount: numberFrom(row.querySelector(".item-amount"), `Item ${index + 1} amount`),
  }));

  const invoice = {
    invoice_number: invNumber,
    items,
    total: numberFrom(elements.total, "Total"),
  };
  const currency = elements.currency.value.trim();
  if (currency) invoice.currency = currency;
  for (const [key, input, label] of [
    ["subtotal", elements.subtotal, "Subtotal"],
    ["tax_rate", elements.taxRate, "Tax rate"],
    ["tax", elements.tax, "Tax"],
  ]) {
    const value = numberFrom(input, label, { optional: true });
    if (value !== undefined) invoice[key] = value;
  }
  return invoice;
}

function writeInvoice(invoice) {
  if (invoice.invoice_number) elements.invoiceNumber.value = invoice.invoice_number;
  if (invoice.currency) elements.currency.value = invoice.currency;
  if (Array.isArray(invoice.items) && invoice.items.length) {
    setItems(
      invoice.items.map((item) => ({
        name: item.description ?? item.name ?? "",
        qty: String(item.quantity ?? ""),
        price: String(item.unit_price ?? ""),
        amount: String(item.amount ?? ""),
      })),
    );
  }
  elements.subtotal.value = invoice.subtotal ?? "";
  elements.taxRate.value = invoice.tax_rate ?? "";
  elements.tax.value = invoice.tax ?? "";
  elements.total.value = invoice.total ?? "";
}

const AMOUNT = "(-?\\d[\\d,]*(?:\\.\\d+)?)";

function toNumber(text) {
  return Number(String(text).replace(/[$€£,\s]/g, ""));
}

// Labeled text is parsed here, directly; no model is involved.
function parseLabeledText(text) {
  const invoice = { items: [] };
  const labeled = (re) => {
    const m = text.match(re);
    return m ? toNumber(m[1]) : undefined;
  };
  const number = text.match(/invoice\s*(?:number|no\.?|#)?\s*[:#]?\s*([A-Za-z0-9][\w-]*\d[\w-]*)/i);
  if (number) invoice.invoice_number = number[1];
  invoice.subtotal = labeled(new RegExp(`sub\\s*-?total\\s*[:=]?\\s*[$€£]?\\s*${AMOUNT}`, "i"));
  invoice.total = labeled(new RegExp(`^\\s*(?:grand\\s+)?total(?:\\s+due)?\\s*[:=]?\\s*[$€£]?\\s*${AMOUNT}`, "im"));
  const taxRate = text.match(/(?:tax|vat)[^\d\n]*\(?\s*(\d+(?:\.\d+)?)\s*%/i);
  if (taxRate) invoice.tax_rate = Number(taxRate[1]);
  const tax = text.match(new RegExp(`^\\s*(?:tax|vat)[^:=\\n]*[:=]\\s*[$€£]?\\s*${AMOUNT}`, "im"));
  if (tax) invoice.tax = toNumber(tax[1]);

  const lineRe = new RegExp(`^\\s*(.+?)\\s+${AMOUNT}\\s*[x×*]\\s*[$€£]?\\s*${AMOUNT}\\s*=\\s*[$€£]?\\s*${AMOUNT}\\s*$`, "i");
  for (const line of text.split(/\r?\n/)) {
    const m = line.match(lineRe);
    if (m) {
      invoice.items.push({
        description: m[1],
        quantity: toNumber(m[2]),
        unit_price: toNumber(m[3]),
        amount: toNumber(m[4]),
      });
    }
  }
  return invoice;
}

function isComplete(invoice) {
  return Boolean(invoice.invoice_number) && invoice.items.length > 0 && invoice.total !== undefined;
}

function completionText(result) {
  const message = result?.message ?? result;
  const content = message?.content ?? result?.text ?? result?.completion;
  if (typeof content === "string") return content;
  if (Array.isArray(content)) return content.map((part) => part?.text ?? "").join("");
  return "";
}

async function extractWithModel(text) {
  const result = await anna.llm.complete({
    system:
      "You copy fields out of invoice text into JSON. Do not calculate, correct, or infer any number: copy each stated value exactly as written. " +
      'Reply with JSON only: {"invoice_number": string, "currency": string|null, "items": [{"description": string, "quantity": number, "unit_price": number, "amount": number}], "subtotal": number|null, "tax_rate": number|null, "tax": number|null, "total": number}. Use null for fields that are not in the text.',
    messages: [{ role: "user", content: text }],
    max_tokens: 800,
    temperature: 0,
  });
  const raw = completionText(result);
  const json = raw.slice(raw.indexOf("{"), raw.lastIndexOf("}") + 1);
  const parsed = JSON.parse(json);
  for (const key of ["subtotal", "tax_rate", "tax", "currency"]) {
    if (parsed[key] === null) delete parsed[key];
  }
  return parsed;
}

async function fillFromText() {
  const text = elements.paste.value.trim();
  if (!text) {
    showStatus("Paste some invoice text first.", "error");
    return;
  }
  elements.fill.disabled = true;
  try {
    let invoice = parseLabeledText(text);
    let source = "read directly from labeled text";
    if (!isComplete(invoice)) {
      if (!anna?.llm?.complete) {
        throw new Error("Could not find an invoice number, line items (qty x price = amount), and a total. Fill the form manually.");
      }
      showStatus("Reading the text with a model (fields are only copied, not checked)...", "info");
      invoice = await extractWithModel(text);
      source = "copied by a model";
    }
    writeInvoice(invoice);
    showStatus(`Form filled (${source}). Review it, then click Check Invoice.`, "info");
  } catch (error) {
    showStatus(error.message || "Could not read the text.", "error");
  } finally {
    elements.fill.disabled = false;
  }
}

function formatResult(data) {
  const currency = data.currency ? ` ${data.currency}` : "";
  const header = data.valid ? "PASS" : "FAIL";
  const lines = [
    `${header} - invoice ${data.invoice_number}`,
    `Calculated subtotal: ${data.calculated_subtotal}${currency}`,
    `Tax used: ${data.calculated_tax}${currency}`,
    `Expected total: ${data.expected_total}${currency} (stated ${data.stated_total})`,
  ];
  if (!data.valid) lines.push("", ...(data.issues || []).map((issue) => `- ${issue}`));
  return lines.join("\n");
}

async function checkInvoice() {
  try {
    const invoice = readInvoice();
    elements.check.disabled = true;
    showStatus("Checking invoice...", "info");

    if (!anna) {
      throw new Error("Anna SDK not connected. Open this app inside Anna to run the check.");
    }

    const result = await anna.tools.invoke({
      tool_id: TOOL_ID,
      method: "check_invoice",
      args: invoice,
    });

    const payload = result?.data ?? result;
    if (result?.success === false || payload?.success === false) {
      throw new Error(result?.error || payload?.error || "The check failed.");
    }
    const data = payload?.data ?? payload;
    if (!data || typeof data.valid !== "boolean") {
      throw new Error("No valid response received from the tool.");
    }
    showStatus(formatResult(data), data.valid ? "success" : "error");
  } catch (error) {
    showStatus(error.message || "An unexpected error occurred.", "error");
  } finally {
    elements.check.disabled = false;
  }
}

async function connect() {
  try {
    const { AnnaAppRuntime } = await import("/static/anna-apps/_sdk/latest/index.js");
    anna = await AnnaAppRuntime.connect();
    await anna.window.set_title({ title: "Invoice Sanity Check" });
    showStatus("Ready. Enter an invoice or paste its text, then click Check Invoice.", "info");
  } catch (error) {
    showStatus("Offline preview: open this app inside Anna to run checks.", "info");
  }
}

elements.addItem.addEventListener("click", () =>
  createItemRow({ name: "New item", qty: "1", price: "0.00", amount: "0.00" }),
);
elements.check.addEventListener("click", checkInvoice);
elements.fill.addEventListener("click", fillFromText);
elements.sample.addEventListener("click", () => {
  elements.paste.value = SAMPLE_TEXT;
  writeInvoice({
    invoice_number: "INV-2026-014",
    currency: "USD",
    items: [
      { description: "Design work", quantity: 3, unit_price: 120, amount: 360 },
      { description: "Hosting", quantity: 2, unit_price: 49.99, amount: 99.98 },
    ],
    subtotal: 459.98,
    tax_rate: 10,
    tax: 45.99,
    total: 505.97,
  });
  showStatus("Sample loaded with deliberate tax and total errors. Click Check Invoice.", "info");
});

createItemRow();
connect();
