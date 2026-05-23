# 🏥 Patient Billing – Dental Practice Billing App (Browser App)
![UI Showcase](/Home-D.png)
---

For this project I built a browser-based billing application for a dental practice using **NiceGUI**, **SQLModel**, and **SQLite**. The goal was to apply everything from the Advanced Programming module: clean architecture, data validation, ORM, and automated testing.

---

## 📝 Application Requirements

### Problem

In small dental practices, patient invoices are still managed manually. This causes errors, missing records, inconsistent pricing, and no way to track what changed on a bill.

---

### Scenario

The application allows users to:
- manage patients (create, edit, delete) including a **salutation** (Herr / Frau / Divers)
- **search for a patient by ID** and immediately create an invoice or view their history
- create invoices per patient with a due date automatically set to **one calendar month after the bill date**
- add treatment line items from the official Swiss dental tariff (SSO/UVMV)
- automatically calculate invoice totals
- track every change in an immutable audit log
- download professional PDF invoices where the **salutation appears as the first line of the address block**

---

## 📖 User Stories

### 1. Manage Patients
**As a receptionist, I want to create, edit, and delete patient records.**

- **Inputs:** salutation (Anrede), first name, last name, date of birth, insurance number, address (street, PLZ, city)
- **Outputs:** updated patient list (`list[Patient]`)

---

### 2. Search Patient by ID
**As a receptionist, I want to look up a patient by their ID and immediately create an invoice or view their invoice history.**

- **Inputs:** patient ID (`int`)
- **Outputs:** patient details + action buttons (Create Invoice / View Invoices & History)

---

### 3. Create an Invoice
**As a receptionist, I want to create an invoice for a patient with a due date automatically one month after today.**

- **Inputs:** patient (selected from dropdown or found via ID search), optional due date override
- **Outputs:** new invoice (`Invoice`) with due date = bill date + 1 calendar month

---

### 4. Add Treatment Items from Tariff
**As a receptionist, I want to select treatments from the Swiss dental tariff and add them to an invoice.**

- **Inputs:** tariff code / description, quantity
- **Outputs:** updated invoice with line items and auto-calculated total

---

### 5. Generate PDF Invoice
**As a receptionist, I want to download a professional PDF invoice for the patient.**

- **Inputs:** invoice ID (`int`)
- **Outputs:** PDF file (bytes), downloadable in the browser. The patient's salutation (e.g. *Herr* / *Frau*) appears as the first line of the patient address on the PDF.

---

### 6. View Invoice History and Audit Log
**As a receptionist, I want to see all past invoices and a full change history per invoice.**

- **Inputs:** optional patient filter (`int`)
- **Outputs:** list of invoices (`list[Invoice]`), change log entries

---

## 🧩 Use Cases

### Main Use Cases
- Manage Patients (Receptionist)
- Search Patient by ID (Receptionist)
- Create Invoice (Receptionist)
- Add / Remove Treatment Items (Receptionist)
- Change Invoice Status (Receptionist)
- Download PDF Invoice (Receptionist)
- View Change Audit Log (Receptionist / Admin)

### Actors
- Receptionist
- Admin

---

### Wireframes / Mockups

> Screenshots of the main pages can be found in `docs/` (see How to Run → Usage below).

---

## 🏛️ Architecture

I structured the project in four layers so that each part has one clear job:

### Layers
- **UI (`views/`):** NiceGUI browser pages — only calls services, never touches the DB directly
- **Controllers (`controllers/`):** business logic + DAO data access + PDF generation
- **Domain (`domain/`):** SQLModel / SQLAlchemy ORM models and session factories
- **Persistence (`db/`):** SQLite databases, seed scripts, and source data

### Design Decisions
- I chose **MVC** because the app has a UI, user interactions, business objects, and a database — keeping them separate makes it much easier to change one without breaking another.
- I introduced the **DAO pattern** so that all SQL queries live in one place. Services never open sessions themselves.
- I wrapped all ORM models in a **`domain/` package (Facade)** so the rest of the app never imports SQLModel directly.
- I packaged the **ReportLab PDF logic as an Adapter** (`pdf_service.py`) behind a single `generate_invoice_pdf(invoice_id)` function.

### Design Patterns Used
- **MVC:** separates UI, business logic, and data persistence
- **DAO:** all DB queries and session management in `dao.py`; services orchestrate only
- **Facade:** `domain/__init__.py` exposes a clean API to models and sessions
- **Adapter:** `pdf_service.py` wraps ReportLab so the rest of the app stays PDF-library-agnostic

---

## 🗄️ Database and ORM

The application uses **two separate SQLite databases** intentionally:

- **`billing.db`** – stores all patient-related data: patients, invoices, invoice items, and the audit log. This database contains personally identifiable information (PII) and must be kept isolated so that access controls, backups, and data-retention policies can be applied to it independently.
- **`zahnarzttarif.db`** – stores the read-only Swiss dental tariff catalogue (SSO/UVMV). This is reference data with no personal information. Keeping it separate means it can be updated or replaced without touching patient records, and patient data is never at risk during a tariff import.

Separating these concerns follows the principle of **data minimisation**: code that only needs tariff look-ups never has access to patient records, which reduces the attack surface and makes compliance easier.

I used **SQLModel** (built on SQLAlchemy) for `billing.db` and **SQLAlchemy** directly for the read-only `zahnarzttarif.db`.

### Entities
- `Patient` *(includes `gender` field: Herr / Frau / Divers)*
- `Invoice`
- `InvoiceItem`
- `InvoiceChangeEntry`
- `Tariff` *(read-only tariff catalogue)*
- `Section` *(tariff chapter groupings)*

### Relationships
- One `Patient` → many `Invoice`
- One `Invoice` → many `InvoiceItem`
- One `Invoice` → many `InvoiceChangeEntry`

### Invoice Immutability
I decided that invoices should be **immutable records** — once created they can only be voided, not deleted. Every change is written to an audit log:

| Action | Change type | Fields recorded |
|---|---|---|
| Status changed | `status_change` | `old_status`, `new_status` |
| Item added | `item_added` | description, quantity, unit price |
| Item removed | `item_removed` | soft-delete (`is_active = False`) |

Calling `delete()` on an invoice always raises a `ValueError` — use `set_status("cancelled")` instead.

---

### 1. Browser-based App (NiceGUI)

The app runs entirely in the browser. I used NiceGUI because it lets me write the UI in Python without needing a separate frontend. Users can:

- Browse and manage patients (with salutation)
- Search a patient by ID and jump directly to create an invoice or view their history
- Create invoices — patient can be found by ID search or selected from the dropdown
- See live-calculated totals
- Download PDF invoices (salutation shown as first address line)
- View the full per-invoice change history

**Architecture note:** the browser is a thin client — all UI state and business logic live on the Python server.

---

### 2. Data Validation

I validate all inputs before they reach the database:
- First name and last name are required
- Salutation (Anrede) is optional but stored when provided
- PLZ must contain digits only
- **Date of Birth** accepts both `DD.MM.YYYY` and `YYYY-MM-DD` formats
- **Invoice Due Date** defaults to exactly **one calendar month** after the invoice date (uses `dateutil.relativedelta` — correctly handles month-end edge cases, e.g. Jan 31 → Feb 28)
- Invoice items require `quantity > 0` and `price ≥ 0`
- Invoice status must be one of `open | paid | cancelled`
- Invoices cannot be hard-deleted

#### Date Validation

A shared `validate_date(value)` helper and `normalise_date(value)` converter in `views/shared.py` are wired to both the **Date of Birth** field (add + edit patient forms) and the **Due Date** field (new invoice form).

- While typing, the input field turns **red** and shows an inline error message as soon as the format is wrong.
- On submit, a **toast notification** (red banner) appears and the form is blocked until the date is corrected.
- Both formats are accepted:
  - German format `DD.MM.YYYY` — e.g. `18.10.1993` ✅
  - ISO format `YYYY-MM-DD` — e.g. `1993-10-18` ✅
- Dates entered in German format are automatically converted to `YYYY-MM-DD` before being saved to the database.
- Rejected inputs: `18-10-1993`, `10/18/1993`, `9999-99-99` ❌

Every service method is wrapped in structured `try/except` blocks:
- **`ValueError`** raised by validation rules is always re-raised unchanged so the UI and tests receive the exact error message
- **Unexpected errors** (e.g. database failures) are caught and re-raised as `RuntimeError` with a descriptive message, keeping the root cause accessible via `__cause__`

| Validation rule | Where checked | Example message |
|---|---|---|
| Empty first / last name | service layer | `First name and last name are required.` |
| Non-digit PLZ | UI + service layer | `PLZ darf nur Ziffern enthalten.` |
| Invalid date of birth format | UI (`validate_date`) | `Ungültiges Datum – bitte DD.MM.YYYY oder YYYY-MM-DD eingeben` |
| Invalid invoice due-date format | UI (`validate_date`) | `Ungültiges Datum – bitte DD.MM.YYYY oder YYYY-MM-DD eingeben` |
| `quantity ≤ 0` or `price < 0` | service layer | `Quantity must be > 0 and price >= 0.` |
| Invalid invoice status | service layer | `Status must be one of {'open', 'paid', 'cancelled'}` |
| Hard-delete attempt on invoice | service layer | `Invoices are immutable. Use set_status('cancelled') …` |
| DB / unexpected failure | service layer | `Could not create patient: …` |

---

### 3. Database Management

I manage the billing data with **SQLModel** and the tariff catalogue with **SQLAlchemy**. Both databases live in `db/` and are populated by dedicated seed scripts.

New columns are added automatically via `_run_migrations()` in `domain/models.py`, which runs `ALTER TABLE` statements on every startup so existing databases are upgraded without data loss. The `gender` column was added this way.

---

## ⚙️ Implementation

### Technology

- Python 3.13
- NiceGUI
- SQLModel / SQLAlchemy
- ReportLab
- python-dateutil
- pytest + pytest-cov

---

### 📚 Libraries Used

- **nicegui** – browser-based UI framework
- **sqlmodel** – ORM for billing data
- **sqlalchemy** – ORM for tariff catalogue & DAO layer
- **reportlab** – PDF invoice generation
- **python-dateutil** – reliable calendar-month arithmetic for due dates (`relativedelta`)
- **pytest** – testing
- **pytest-cov** – test coverage

---

## 📂 Repository Structure

```text
Bills/
├── main.py                    ← entry point
├── __init__.py
├── requirements.txt
├── README.md
├── text_normalization.py      ← normalises legacy macron → umlaut in imported tariff text
│
├── domain/                    ← ORM models (data layer)
│   ├── __init__.py
│   ├── models.py              ← Patient (incl. gender), Invoice, InvoiceItem, InvoiceChangeEntry
│   └── tariff_models.py       ← Tariff, Section (SQLAlchemy)
│
├── controllers/               ← business logic + data access + PDF
│   ├── __init__.py
│   ├── services.py            ← PatientService, InvoiceService, TariffService
│   ├── dao.py                 ← PatientDAO, InvoiceDAO, TariffDAO
│   └── pdf_service.py         ← generate_invoice_pdf()
│
├── views/                     ← NiceGUI UI pages
│   ├── __init__.py
│   ├── home.py                ← / home dashboard page
│   ├── patients.py            ← /patients page + invoice_card component
│   ├── invoices.py            ← /invoices page
│   └── shared.py              ← nav bar, notify helpers, STATUS_COLOR, validate_date
│
├── db/                        ← databases + seed scripts + source data
│   ├── billing.db             ← SQLite billing database
│   ├── zahnarzttarif.db       ← SQLite tariff catalogue
│   ├── zahnarzttarif.json     ← source data for tariff seed
│   ├── seed.py                ← seeds patients (with gender/salutation) + invoices
│   └── seed_tariff.py         ← seeds tariff catalogue from JSON
│
    └── tests/                     ← pytest test suite
    ├── conftest.py            ← in-memory DB fixture
    └── test_billing.py        ← 15 tests (unit / DB / integration)
```

---

## 🚀 How to Run

### 1. Project Setup
- Python 3.13 is required
- Create and activate a virtual environment:
   - **macOS/Linux:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - **Windows:**
     ```bash
     python -m venv .venv
     .venv\Scripts\Activate
     ```
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

### 2. Seed the Databases
```bash
# Seed the Swiss dental tariff catalogue
python db/seed_tariff.py

# Seed sample patients (with salutation) and invoices
python db/seed.py
```

> **Fresh start:** delete `db/billing.db` before re-running `seed.py` to reset all patient and invoice data.

### 3. Launch
```bash
python main.py
```
Open **http://localhost:8080** in your browser.

### 4. Usage

**Manage Patients:**
1. Open the **Patients** page.
2. Select an **Anrede** (Herr / Frau / Divers), fill in the form, and click **Add Patient**.
   - Date of Birth accepts `DD.MM.YYYY` (e.g. `18.10.1993`) or `YYYY-MM-DD` (e.g. `1993-10-18`).
3. Use the ✏️ button to edit a patient.
4. Use the 🧾 button to open that patient's invoices.

**Search Patient by ID:**
1. Enter a patient ID in the **Search Patient by ID** card and click **Search**.
2. If found, the patient's details appear along with two action buttons:
   - **Create Invoice** → navigates to that patient's invoice page ready to create a new invoice
   - **View Invoices / History** → opens the full invoice list and audit log for that patient

**Create & Manage Invoices:**
1. On the **Invoices** page, use **Search by Patient ID** to find and auto-select a patient, or choose from the dropdown.
2. The **Fälligkeitsdatum** (due date) is pre-filled to exactly **one month** after today — adjust if needed.
3. Click **Create Invoice**.
4. Expand the invoice card → open **Items**.
5. Search and select treatments from the tariff picker, set quantities, click **Add Selected Treatments**.
6. Change status via the dropdown (`open → paid / cancelled`).
7. Click the 📄 PDF button to download the invoice. The salutation (e.g. *Frau*) appears as the first line of the patient address on the PDF.

---

## 🧪 Testing

I wrote 15 tests covering all three layers of the application.

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ -v --cov=controllers --cov=domain --cov-report=term-missing
```

**Test mix – 15 tests total:** 9 Unit · 3 DB · 3 Integration

---

### 🔬 Unit Tests (TC_001 – TC_009)
*Pure business-logic validation – no database required.*

---

| Field | Details |
|---|---|
| **Test case ID** | TC_001 |
| **Title** | Empty first name is rejected before any DB call |
| **Preconditions** | None |
| **Test steps** | Call `PatientService.create("", "Müller")` |
| **Test data / input** | `first_name=""`, `last_name="Müller"` |
| **Expected result** | `ValueError: First name and last name are required` |
| **Actual result** | `ValueError: First name and last name are required` |
| **Status** | ✅ Pass |
| **Comments** | Validation fires before any DB session is opened |

---

| Field | Details |
|---|---|
| **Test case ID** | TC_002 |
| **Title** | PLZ containing non-digit characters is rejected |
| **Preconditions** | None |
| **Test steps** | Call `PatientService._validate_plz("12AB")` |
| **Test data / input** | `plz="12AB"` |
| **Expected result** | `ValueError: PLZ must contain digits only` |
| **Actual result** | `ValueError: PLZ must contain digits only` |
| **Status** | ✅ Pass |
| **Comments** | Swiss postal codes must be numeric |

---

| Field | Details |
|---|---|
| **Test case ID** | TC_003 |
| **Title** | `Invoice.total` sums qty × price for all active items |
| **Preconditions** | In-memory `Invoice` with two active `InvoiceItem` objects |
| **Test steps** | 1. Create `Invoice` with items directly. 2. Read `.total` property |
| **Test data / input** | item1: qty=2, price=10.0 · item2: qty=1, price=25.0 |
| **Expected result** | `total == 45.0` |
| **Actual result** | `total == 45.0` |
| **Status** | ✅ Pass |
| **Comments** | Pure property calculation – no DB needed |

---

| Field | Details |
|---|---|
| **Test case ID** | TC_004 |
| **Title** | `Invoice.total` excludes soft-deleted items (`is_active=False`) |
| **Preconditions** | In-memory `Invoice` with one active and one inactive item |
| **Test steps** | 1. Create `Invoice` with mixed items. 2. Read `.total` |
| **Test data / input** | active: qty=1, price=50.0 · inactive: qty=3, price=100.0 |
| **Expected result** | `total == 50.0` |
| **Actual result** | `total == 50.0` |
| **Status** | ✅ Pass |
| **Comments** | Soft-deleted items must never contribute to the total |

---

| Field | Details |
|---|---|
| **Test case ID** | TC_005 |
| **Title** | Unrecognised invoice status is rejected immediately |
| **Preconditions** | None |
| **Test steps** | Call `InvoiceService.set_status(1, "pending")` |
| **Test data / input** | `status="pending"` |
| **Expected result** | `ValueError: Status must be one of ...` |
| **Actual result** | `ValueError: Status must be one of {'open', 'paid', 'cancelled'}` |
| **Status** | ✅ Pass |
| **Comments** | Guard fires before any DB lookup is made |

---

| Field | Details |
|---|---|
| **Test case ID** | TC_006 |
| **Title** | Adding an invoice item with quantity ≤ 0 is rejected |
| **Preconditions** | None |
| **Test steps** | Call `InvoiceService.add_item(1, "X", quantity=0, unit_price=10.0)` |
| **Test data / input** | `quantity=0` |
| **Expected result** | `ValueError: Quantity must be > 0 and price >= 0` |
| **Actual result** | `ValueError: Quantity must be > 0 and price >= 0` |
| **Status** | ✅ Pass |
| **Comments** | Zero quantity would silently produce a CHF 0 line item |

---

| Field | Details |
|---|---|
| **Test case ID** | TC_007 |
| **Title** | Adding an invoice item with a negative unit price is rejected |
| **Preconditions** | None |
| **Test steps** | Call `InvoiceService.add_item(1, "X", quantity=1, unit_price=-5.0)` |
| **Test data / input** | `unit_price=-5.0` |
| **Expected result** | `ValueError: ... price >= 0` |
| **Actual result** | `ValueError: Quantity must be > 0 and price >= 0` |
| **Status** | ✅ Pass |
| **Comments** | Negative prices would corrupt the invoice total |

---

| Field | Details |
|---|---|
| **Test case ID** | TC_008 |
| **Title** | Hard-deleting an invoice always raises `ValueError` |
| **Preconditions** | None |
| **Test steps** | Call `InvoiceService.delete(99)` |
| **Test data / input** | `invoice_id=99` (any id) |
| **Expected result** | `ValueError` mentioning "cancelled" |
| **Actual result** | `ValueError: Invoices are immutable. Use set_status('cancelled') ...` |
| **Status** | ✅ Pass |
| **Comments** | Invoices are immutable — use `set_status("cancelled")` to void |

---

| Field | Details |
|---|---|
| **Test case ID** | TC_009 |
| **Title** | Legacy macron characters are normalised to German umlauts |
| **Preconditions** | None |
| **Test steps** | Call `normalize_umlauts("Infiltrationsanāsthesie, 2 Kanāle, Zāhne")` |
| **Test data / input** | String containing ā / ū / ō macron substitutions |
| **Expected result** | `"Infiltrationsanästhesie, 2 Kanäle, Zähne"` |
| **Actual result** | `"Infiltrationsanästhesie, 2 Kanäle, Zähne"` |
| **Status** | ✅ Pass |
| **Comments** | Ensures imported tariff descriptions render with correct German umlauts |

---

### 🗄️ DB Tests (TC_010 – TC_012)
*DAO layer against an isolated in-memory SQLite database.*

---

| Field | Details |
|---|---|
| **Test case ID** | TC_010 |
| **Title** | Inserting a patient persists it and `get_by_id` retrieves it |
| **Preconditions** | Empty in-memory SQLite DB (`billing_db` fixture) |
| **Test steps** | 1. `PatientDAO.insert(Patient(...))` 2. `PatientDAO.get_by_id(p.id)` |
| **Test data / input** | `first_name="Anna"`, `last_name="Müller"` |
| **Expected result** | Returned patient has `id != None`, correct name |
| **Actual result** | Patient retrieved with correct name and assigned id |
| **Status** | ✅ Pass |
| **Comments** | Verifies full round-trip: insert → commit → query |

---

| Field | Details |
|---|---|
| **Test case ID** | TC_011 |
| **Title** | A saved invoice carries the correct `patient_id` |
| **Preconditions** | One patient exists in in-memory DB |
| **Test steps** | 1. Insert patient. 2. `InvoiceDAO.insert(Invoice(patient_id=...))` 3. `get_by_id` |
| **Test data / input** | `first_name="Thomas"`, `last_name="Schneider"` |
| **Expected result** | `fetched.patient_id == patient.id` |
| **Actual result** | `patient_id` matches |
| **Status** | ✅ Pass |
| **Comments** | Ensures the foreign-key relationship is persisted correctly |

---

| Field | Details |
|---|---|
| **Test case ID** | TC_012 |
| **Title** | A brand-new invoice has an empty change log |
| **Preconditions** | One patient + one invoice in in-memory DB |
| **Test steps** | 1. Insert patient and invoice. 2. `InvoiceDAO.get_changes(inv.id)` |
| **Test data / input** | `first_name="Laura"`, `last_name="Fischer"` |
| **Expected result** | `changes == []` |
| **Actual result** | Empty list returned |
| **Status** | ✅ Pass |
| **Comments** | No change entries should exist before any status/item mutation |

---

### 🔗 Integration Tests (TC_013 – TC_015)
*Full service-layer flows — all layers cooperate against in-memory DB.*

---

| Field | Details |
|---|---|
| **Test case ID** | TC_013 |
| **Title** | Full flow: create patient → invoice → add items → total matches |
| **Preconditions** | Empty in-memory DB |
| **Test steps** | 1. `PatientService.create("Sophie","Koch")` 2. `InvoiceService.create(patient.id)` 3. `add_item("Befundaufnahme", qty=1, price=73.0)` 4. `add_item("Anästhesie", qty=2, price=38.4)` 5. `get_by_id` and check `.total` |
| **Test data / input** | Two items: CHF 73.00 + 2×CHF 38.40 |
| **Expected result** | `total == 149.80` |
| **Actual result** | `total == 149.80` |
| **Status** | ✅ Pass |
| **Comments** | End-to-end test covering PatientService → InvoiceService → DAO → DB |

---

| Field | Details |
|---|---|
| **Test case ID** | TC_014 |
| **Title** | Deleting an item soft-removes it and total drops to 0 |
| **Preconditions** | Patient + invoice + one active item in in-memory DB |
| **Test steps** | 1. Create patient, invoice, add item (qty=1, price=100.0). 2. `InvoiceService.delete_item(item.id)` 3. Check `item.is_active` and `invoice.total` |
| **Test data / input** | Item: `"Extraktion"`, qty=1, price=CHF 100.00 |
| **Expected result** | `item.is_active == False`, `total == 0.0` |
| **Actual result** | `is_active=False`, `total=0.0` |
| **Status** | ✅ Pass |
| **Comments** | Soft-delete must persist to DB and be reflected in the total |

---

| Field | Details |
|---|---|
| **Test case ID** | TC_015 |
| **Title** | Changing status creates a `status_change` entry in the audit log |
| **Preconditions** | Patient + open invoice in in-memory DB |
| **Test steps** | 1. Create patient + invoice. 2. `InvoiceService.set_status(inv.id, "paid")` 3. `InvoiceDAO.get_changes(inv.id)` |
| **Test data / input** | `old_status="open"`, `new_status="paid"` |
| **Expected result** | One change entry with `change_type="status_change"`, correct old/new status |
| **Actual result** | One entry: `status_change`, `open → paid` |
| **Status** | ✅ Pass |
| **Comments** | Verifies the full audit trail: service → DAO → DB → query |

---

## 👥 Student & Contributions

| Name | Contributions |
|---|---|
| Aiman El-Mohtaseb | Designed and implemented the full application: domain models (incl. `gender` field & auto-migration), DAO layer, service logic, NiceGUI views (patient ID search with action buttons, invoice patient ID search, due-date fix), PDF generation (salutation as first address line), seed scripts, test suite (15 tests), and documentation |

---

## 📝 License

This project was developed as a student submission for the Advanced Programming module and is for educational use only.
