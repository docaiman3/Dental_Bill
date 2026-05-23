"""
Seed script – populates the database with realistic fake data for testing.
Safe to run multiple times: skips seeding if patients already exist.

Run once before starting the app:  python db/seed.py
"""
import sys
from pathlib import Path

# Ensure project root (Bills/) is on sys.path
_root = Path(__file__).parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from domain.models import create_db_and_tables
from controllers.services import InvoiceService, PatientService

create_db_and_tables()

if PatientService.get_all():
    print("⚠️  Database already has patients – seed skipped to avoid duplicates.")
    print("   Delete db/billing.db and re-run to start fresh.")
    sys.exit(0)

patients_data = [
    # (gender, first, last, dob, insurance, street, plz, city)
    ("Frau",  "Anna",   "Müller",    "1985-03-12", "CH-12345678", "Bahnhofstrasse 12", "8001", "Zürich"),
    ("Herr",  "Thomas", "Schneider", "1972-07-24", "CH-87654321", "Hauptgasse 5",      "3011", "Bern"),
    ("Frau",  "Laura",  "Fischer",   "1990-11-05", "CH-11223344", "Freiestrasse 22",   "4051", "Basel"),
    ("Herr",  "Markus", "Weber",     "1965-01-30", "CH-55667788", "Marktgasse 8",      "3011", "Bern"),
    ("Frau",  "Sophie", "Koch",      "1998-06-18", "CH-99887766", "Rue du Rhône 45",   "1204", "Genf"),
]

created_patients = []
for gender, fn, ln, dob, ins, street, plz, city in patients_data:
    p = PatientService.create(fn, ln, dob, ins, street, plz, city, gender=gender)
    created_patients.append(p)
    print(f"  ✔ Patient: {gender} {fn} {ln} – {street}, {plz} {city}")

# Descriptions use the canonical "ziffer – leistung" format from zahnarzttarif.db
# Prices are the UVMV/IV reference rates (uvmv_iv) from the same database.

invoice_data = [
    # (patient_index, status, [(description, qty, unit_price), ...])
    # due_date is omitted – InvoiceService defaults to bill date + 1 month

    # Anna Müller – routine recall + X-ray
    (0, "paid", [
        ("4.0000 – Befundaufnahme oder Zweitmeinung Befundaufnahme beim Recallpatienten", 1, 73.00),
        ("4.0530 – OPT 4",                                                               1, 156.90),
        ("4.0980 – Mundhygieneanamnese, Instruktion, Motivation",                        1, 69.70),
    ]),

    # Anna Müller – follow-up with anaesthesia and filling
    (0, "open", [
        ("4.0020 – Kurzbefundaufnahme beim Notfallpatienten",                            1,  33.00),
        ("4.0650 – Infiltrationsanästhesie",                                             2,  38.40),
        ("4.5020 – Glasionomerzement, 2-fl.",                                            1,  87.20),
    ]),

    # Thomas Schneider – root-canal treatment (3 canals)
    (1, "paid", [
        ("4.0000 – Befundaufnahme oder Zweitmeinung Befundaufnahme beim Recallpatienten", 1,  73.00),
        ("4.0650 – Infiltrationsanästhesie",                                             1,  38.40),
        ("4.4400 – Pulpaexstirpation, 1 Kanal",                                          1, 181.30),
        ("4.4410 – Pulpaexstirpation, 2 Kanäle",                                         1, 233.60),
    ]),

    # Thomas Schneider – cancelled appointment
    (1, "cancelled", [
        ("4.2060 – Operative Entfernung retinierter Zahn, einfach",                      1, 289.40),
    ]),

    # Laura Fischer – prophylaxis session
    (2, "open", [
        ("4.0000 – Befundaufnahme oder Zweitmeinung Befundaufnahme beim Recallpatienten", 1,  73.00),
        ("4.1040 – Gingivaindex ausführlich",                                             1,  12.00),
        ("4.1080 – Fluoridlack (1-4 Zähne)",                                             3,  26.00),
        ("4.0980 – Mundhygieneanamnese, Instruktion, Motivation",                         1,  69.70),
    ]),

    # Markus Weber – emergency extraction
    (3, "paid", [
        ("4.0020 – Kurzbefundaufnahme beim Notfallpatienten",                            1,  33.00),
        ("4.0650 – Infiltrationsanästhesie",                                             2,  38.40),
        ("4.2000 – Zahnextraktion, einfach",                                             1,  52.30),
        ("4.0530 – OPT 4",                                                               1, 156.90),
    ]),

    # Sophie Koch – apicectomy (Wurzelspitzenresektion)
    (4, "open", [
        ("4.0000 – Befundaufnahme oder Zweitmeinung Befundaufnahme beim Recallpatienten", 1,  73.00),
        ("4.0650 – Infiltrationsanästhesie",                                             1,  38.40),
        ("4.2310 – Wurzelspitzenresektion",                                              1, 296.40),
    ]),
]

for pat_idx, status, items in invoice_data:
    patient = created_patients[pat_idx]
    inv = InvoiceService.create(patient.id)   # due_date auto = today + 1 month
    for desc, qty, price in items:
        InvoiceService.add_item(inv.id, desc, qty, price)
    InvoiceService.set_status(inv.id, status)
    total = sum(q * p for _, q, p in items)
    print(f"  ✔ Invoice #{inv.id} for {patient.gender} {patient.first_name} {patient.last_name} "
          f"| due {inv.due_date} | CHF {total:.2f} | {status}")

print("\nSeed complete! Run: python main.py")
