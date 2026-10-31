# گزارش تحویل پروژهٔ Invoice Sanity Check — 2026-10-30

تهیه‌شده پس از بررسی مستقیم فایل‌های مخزن، تست‌ها، گزارش‌های review و باینری منتشرشده.

## 1. وضعیت فعلی (Verified)

- **شاخهٔ Git**: `main`.
- **HEAD commit**: `ac917c72a56eef6681331d46e5f57dab6c11454a`.
- **Commitهای pushنشده به `origin/main`** (4 عدد):
  - `ac917c7` Record completed contest update and source publication
  - `41e4f88` Merge existing v0.3.0 history with tested migration fixes
  - `8d37866` Fix Anna app migration and invoice import; verify Cloud installation
  - `0571260` v0.3.0: fix Executa describe/parameters protocol, add tax rate and text import, listing screenshots and description
- **وضعیت working tree**: فایل‌های جدید `HANDOVER-REPORT.md` و پوشهٔ تو در تو `invoice-sanity-check/` untracked؛ tracked file تغییر نکرده است.
- **تگ‌ها**: `invoice-sanity-check-v0.2.2` (تنها تگ محلی).
- **حساب Anna فعلی**: handle `alireza`، app ID `721` (`@alireza/invoice-sanity-check`).
- **نسخهٔ candidate اپ**: `0.3.1`، immutable version ID `1669`، وضعیت **pending_review**.
- **Executa فریزشده**: `0.3.0`، version ID `862`.
- **ابزار registry (server-minted)**: `tool-alireza-invoice-sanity-check-jrqmux6d`.
- **نام بستهٔ اجرایی (legacy، حفظ‌شده)**: `tool-naomi197-invoice-sanity-check-qhj8bq39`.
- **نسخهٔ قبلی**: `@naomi197/invoice-sanity-check` (app ID 432) رد شده؛ checkout قدیمی در `invoice-sanity-check/` (شاخهٔ `master`، commit `0571260`).
- **نصب Cloud**: app 0.3.1 روی Cloud Agent #4898 نصب شد؛ ابزار وضعیت Running، نسخهٔ server/agent 0.3.0، با دو tool.

### نتایج تست (اجرای واقعی در این بررسی)

| دستور | نتیجه |
|---|---|
| `python -m pytest -q tests` | **18 passed** در 0.08s |
| `npm run validate` | **passed** (strict Anna validation) |
| `npm run test:acl` | **PASSED** (8/8 checks) |
| `python scripts/verify_executa.py .review/windows.tar.gz --version 0.3.0` | **PASS** (init, describe×2, health, ping, PASS/FAIL, recovery, EOF) |

محیط اجرای تست‌ها: Python 3.12.0، Node.js v22.23.2، npm 10.9.8، Anna CLI 0.1.60، Windows؛ commit HEAD `ac917c72a56eef6681331d46e5f57dab6c11454a`. Executa بررسی‌شده: 0.3.0 (windows.tar.gz از `.review/`).


### شواهد Cloud (از REVIEW-STATUS.md)

- فاکتور صحیح پیش‌فرض: PASS (250.00 + 25.00 = 275.00).
- فاکتور ناصحیح عمدی: FAIL (tax 45.99 vs 46.00، total 505.97 vs 505.98).
- import متن برچسب‌دار: CLOUD-FRACTION-001، 0.333 × 3.00 → 1.00، tax 0.10، total 1.10: PASS.
- import متن با مدل واقعی Anna: CLOUD-MODEL-001، subtotal 20.00، tax 2.00، total 22.00 USD: PASS.
- پاسخ ناقص مدل: با خطای صریح رد شد و فرم overwrite نشد.
- صفحهٔ عمومی DoraHacks حاوی توضیحات دقیق و سه اسکرین‌شات.

## 2. تصمیم‌های معماری (Architecture Decisions)

1. **جداسازی استخراج از محاسبه**: مدل (`anna.llm.complete`) فقط فیلدها را کپی می‌کند؛ تصمیم `pass/fail` فقط از `check_invoice` (Executa Python) گرفته می‌شود.
2. **محاسبهٔ دقیق**: `decimal.Decimal` با `ROUND_HALF_UP`، quantize به `0.01`. `money()` برای مالی و `exact()` برای مقادیر خام (quantity اعشاری رند نمی‌شود).
3. **فرمت RPC**: JSON-RPC 2.0 روی stdio، یک request در هر خط. متدها: `initialize`, `describe`, `health`, `invoke` (پوشش `{success, data/error}`).
4. **پروتکل describe**: `name` سطح بالا + `parameters` به‌صورت **لیست** `{name, type, description, required}` (نه JSON-Schema). manifest آرشیو ریشه همین `name` را دارد.
5. **ابزارها**: `ping` (smoke) و `check_invoice`.
6. **فرمت توزیع**: پروفایل `binary` (PyInstaller one-file) per `{os, arch}` از GitHub Release، تأیید با sha256. پروفایل `local` فقط dev loop. `acltest.mjs` regression می‌کند اگر پروفایل به `local` برگردد.
7. **شناسهٔ ابزار دوگانه (intentional)**:
   - registry/server-minted tool_id = `tool-alireza-invoice-sanity-check-jrqmux6d` (sidecar، manifest ACL، `.anna/executas.lock.json`).
   - executable/package name = `tool-naomi197-invoice-sanity-check-qhj8bq39` (executa.json، pyproject.toml، MANIFEST، workflow env `TOOL_ID`، URLهای release).
   - Anna installer با server-provided `tool_id` شناسایی می‌کند و executable را با `executable_name` + `entrypoint` پیدا می‌کند. این رفتار در deployment فعلی تأیید شده است؛ ادعای قرارداد رسمی پلتفرم نیست.
   - **تعریف شناسه‌ها** (برای جلوگیری از اشتباه):

     | شناسه | محل | معنی |
     |---|---|---|
     | `tool-alireza-invoice-sanity-check-jrqmux6d` | sidecar، manifest ACL، `.anna/executas.lock.json` | tool_id سمت registry/Agent (server-minted) |
     | `tool-naomi197-invoice-sanity-check-qhj8bq39` | executa.json، pyproject.toml، MANIFEST، workflow env `TOOL_ID`، URLهای release | نام بسته/فایل اجرایی (legacy، حفظ‌شده) |
     | `bundled:invoice-sanity-check` | root `manifest.json` required_executas | handle محلی که در publish به tool_id تبدیل می‌شود |
     | `entrypoint` | manifest آرشیو ریشه | نام فایل اجرایی داخل tar.gz |


8. **هستهٔ UI**: SPA استاتیک در `bundle/`؛ `index.html` ابتدا `anna-tool-ids.js` سپس `app.js` (module). هرگز tool id hardcode نمی‌شود.
9. **import متن**: ابتدا `parseLabeledText` (بدون مدل)؛ اگر ناقص بود و `anna.llm.complete` موجود بود، مدل فراخوانی می‌شود. currency اختیاری هنگام import جدید پاک می‌شود. پاسخ ناقص مدل قبل از overwrite فرم رد می‌شود.
10. **tax_rate اختیاری**: اگر داده شود، tax محاسبه‌شده از subtotal محاسبه‌شده × rate مقایسه می‌شود؛ در غیر این صورت tax بیان‌شده (پیش‌فرض 0).
11. **اعتبارسنجی ورودی**: invoice_number غیرخالی، 1..100 item، مقدارهای غیرمنفی، total الزامی، subtotal/tax اختیاری.

## 3. فایل‌های کلیدی و نقش آن‌ها

| فایل | نقش |
|---|---|
| `README.md` | مستندات اصلی |
| `REVIEW-STATUS.md` | وضعیت candidate، شواهد تست |
| `manifest.json` (root) | app manifest: UI bundle، views، host_api ACL، required_executas |
| `app.json` | metadata listing + bundled_executas + screenshots |
| `bundle/index.html` | SPA entry |
| `bundle/app.js` | UI logic، readInvoice، parseLabeledText، extractWithModel، checkInvoice |
| `bundle/anna-tool-ids.js` | sidecar: handle → minted tool_id |
| `executas/invoice-sanity-check/executa.json` | identity + distribution (binary URLs) |
| `executas/invoice-sanity-check/manifest.json` | executa manifest (name = legacy tool_id) |
| `executas/invoice-sanity-check/invoice_sanity_check_plugin.py` | منطق RPC + check_invoice (Decimal) |
| `executas/invoice-sanity-check/pyproject.toml` | name + scripts key = legacy tool_id |
| `executas/invoice-sanity-check/uv.lock` | lock (version 0.3.0) |
| `tests/test_invoice_sanity_check_plugin.py` | 18 تست |
| `acltest.mjs` | regression ACL |
| `scripts/verify_executa.py` | بررسی باینری |
| `.github/workflows/build-executa.yml` | PyInstaller per-platform → GitHub Release |
| `.anna/app.json` | identity (app_id 721، handle alireza) |
| `.anna/executas.lock.json` | lock executa (tool_id alireza) |
| `.review/*` | archives، manifest، model.jsonl، model-invalid.jsonl، exe |

## 4. نقاط باقی‌مانده (Remaining / Next Actions)

1. **Await Anna reviewers' decision** — candidate 0.3.1 در وضعیت `pending_review`.
2. **Push commitهای محلی** — branch 4 commit جلوتر از origin/main.
3. **وضعیت انتشار Executa 0.3.0** — assets برای Windows و Linux از mirror Anna دانلود و SHA256 آن‌ها ثبت شد (`63396aa9ef0a8ca53fe2d38418bac9b6ab82c8add0111c7082c348a91acd86c9` برای Windows، `2329defdcaf8805b8a87d62271c50e9b42c8436b913c3a5169b21c89e2d28e3f` برای Linux) و `verify_executa` روی windows.tar.gz موفق بود. وجود/دانلود مستقیم هر چهار asset در GitHub Release قبل از cut بعدی باید دوباره تأیید شود (در این بررسی دوباره دانلود نشد).
4. **تست Cloud** — تست روی Agent #4898 انجام شده است. تکرار تست فقط پس از تغییرات جدید یا در صورت درخواست reviewer لازم است.
5. **بررسی `.review` model logs** — نمونهٔ پاسخ‌های مدل برای regression تست import.
6. **مقایسهٔ آرشیوها** — `invoice-sanity-check.zip` و `invoice-sanity-check-(2).zip`؛ از checkout تو در تو استفاده نشود.
7. **هشدار README**: از checkout تو در تو یا نسخهٔ مربوط به حساب قبلی برای انتشار استفاده نشود. (رعایت شده.)

## 4.1. ریسک‌های باقی‌مانده

- approval نهایی reviewers هنوز دریافت نشده است (candidate 0.3.1 در وضعیت `pending_review`).
- چهار commit محلی push نشده‌اند (`origin/main` = `ddd1b8ab...`).
- هر تغییر بعدی در manifest، bundle یا Executa می‌تواند candidate فعلی را از شواهد ثبت‌شده جدا کند.
- اجرای تست محلی و binary محلی موفق است، اما این به‌تنهایی تضمین نمی‌کند release assetها در تمام platformها قابل نصب باشند.
- تست مدل وابسته به رفتار واقعی Anna است و باید با fixtureهای `.review` (model.jsonl، model-invalid.jsonl) نیز regression شود.

## 4.2. اقدامات فوری (Immediate Actions)

1. ثبت/تأیید commit hash و وضعیت clean/dirty (HEAD = `ac917c72a56eef6681331d46e5f57dab6c11454a`).
2. push کردن چهار commit به `origin/main`.
3. تأیید وجود و دانلود هر چهار asset نسخهٔ `0.3.0` به همراه sha256.
4. نگه‌داشتن candidate `0.3.1` بدون تغییر تا تصمیم reviewer.
5. فقط در صورت رد یا درخواست اصلاح، ایجاد candidate جدید و تکرار تست Cloud.

---


## 5. تصمیم‌هایی که نباید تغییر کنند (Do Not Change)

- Sidecar `bundle/anna-tool-ids.js` باید توسط `anna-app apps publish` تولید شود.
- `executa.json` active profile باید `binary` بماند.
- URLهای release باید از tool_id legacy و tag `invoice-sanity-check-v0.3.0` استفاده کنند.
- `describe` باید `parameters` به‌صورت list برگرداند.
- محاسبات باید با `Decimal` و `ROUND_HALF_UP` باشند.
- مدل فقط استخراج می‌کند، تصمیم نهایی نمی‌گیرد.

## 6. دستورهای ادامهٔ کار (PowerShell، از root واقعی)

```powershell
cd 'D:\github_backup\invoice-sanity-check'
npm ci
npm run validate
npm run test:acl
python -m pytest -q tests
python scripts/verify_executa.py path\to\platform-release.tar.gz --version 0.3.0
git status
git log --oneline --decorate -10
git tag
```

برای build Executa: GitHub Actions → "Build Executa binaries" → Run workflow (یا push tag `invoice-sanity-check-v*`).

## 7. نکات مهم برای نفر بعدی

- پروژه یک Anna App + Executa Python است؛ هدف Executa بررسی قطعی محاسبات فاکتور است.
- مدل فقط برای استخراج اطلاعات از متن استفاده می‌شود.
- محاسبه باید با `Decimal` انجام شود.
- رابط کاربری در `bundle/` است.
- منطق اصلی ابزار در `executas/invoice-sanity-check/` است.
- تست‌ها در `tests/` (18 passed).
- بررسی ACL با `acltest.mjs` (passed).
- بررسی جامع باینری با `scripts/verify_executa.py` (passed روی windows.tar.gz).
- انتشار واقعی نیازمند binaryهای قابل دانلود و بخش `distribution` صحیح است (انجام شده برای 0.3.0).
- شناسهٔ ابزار نباید دستی از نسخهٔ قدیمی کپی شود (الگوی دوگانه را حفظ کنید).
- تست Cloud روی Agent #4898 انجام شده است (PASS/FAIL، import متن، import با مدل). تکرار فقط پس از تغییرات جدید یا در صورت درخواست reviewer.
- candidate 0.3.1 در وضعیت `pending_review` است؛ approval نهایی از reviewers دریافت نشده.

## 8. تصحیحات نسبت به خلاصهٔ اولیه

- در خلاصهٔ اولیه گفته شده بود فایل‌های review/test/manifest به‌طور کامل خوانده نشده‌اند. در این بررسی، `REVIEW-STATUS.md`، `.review/manifest.json`، `model.jsonl`، `model-invalid.jsonl`، تست‌ها، ACL و verify_executa به‌طور کامل بررسی و اجرا شدند.
- تست‌ها در واقع **موفق** هستند (18 passed، validate passed، acl passed، verify_executa passed).
- feedback Anna به‌صورت صریح در REVIEW-STATUS.md ثبت شده و candidate در وضعیت pending_review است.
- شناسهٔ ابزار "دوگانه" در deployment فعلی به صورت عملی تأیید شده است (Cloud Agent #4898 نصب و اجرا شد) و باید حفظ شود. این یک ادعای قرارداد رسمی پلتفرم نیست.
- پوشهٔ تو در تو `invoice-sanity-check/` یک checkout قدیمی (master، v0.3.0) است، نه بخشی از پروژهٔ فعلی.

---
تهیه‌شده بر اساس بررسی مستقیم مخزن در 2026-10-30. فایل‌های منبع: README.md، REVIEW-STATUS.md، package.json، app.json، manifest.json، executas/.../*، tests/*، acltest.mjs، scripts/verify_executa.py، bundle/*، .github/workflows/build-executa.yml، .anna/*، .review/*.
