"""
Data Access Object (DAO) Layer
──────────────────────────────
All raw database queries live here.  Service classes call DAOs;
they never open sessions or write SQL themselves.

DAOs own:  session management, query construction, ORM ↔ dict conversion
Services own: validation, business rules, orchestration
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

# Ensure project root (Bills/) is on sys.path regardless of how this is run
_here = Path(__file__).parent          # Bills/controllers/
_root = _here.parent                   # Bills/
for _p in (str(_here), str(_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from sqlalchemy import or_
from sqlmodel import select

try:
    from ..domain.models import Invoice, InvoiceChangeEntry, InvoiceItem, Patient, get_session
    from ..domain.tariff_models import Section, Tariff, get_tariff_session
except ImportError:
    from domain.models import Invoice, InvoiceChangeEntry, InvoiceItem, Patient, get_session          # type: ignore[import]
    from domain.tariff_models import Section, Tariff, get_tariff_session                              # type: ignore[import]



class PatientDAO:
    """Raw CRUD for the Patient table."""

    @staticmethod
    def get_all() -> List[Patient]:
        with get_session() as s:
            return s.exec(select(Patient).order_by(Patient.last_name)).all()

    @staticmethod
    def get_by_id(patient_id: int) -> Optional[Patient]:
        with get_session() as s:
            return s.get(Patient, patient_id)

    @staticmethod
    def insert(patient: Patient) -> Patient:
        with get_session() as s:
            s.add(patient)
            s.commit()
            s.refresh(patient)
            return patient

    @staticmethod
    def update(patient: Patient) -> Patient:
        with get_session() as s:
            p = s.get(Patient, patient.id)
            if not p:
                raise ValueError("Patient not found.")
            p.first_name       = patient.first_name
            p.last_name        = patient.last_name
            p.gender           = patient.gender
            p.date_of_birth    = patient.date_of_birth
            p.insurance_number = patient.insurance_number
            p.street           = patient.street
            p.plz              = patient.plz
            p.city             = patient.city
            s.add(p)
            s.commit()
            s.refresh(p)
            return p

    @staticmethod
    def delete(patient_id: int) -> None:
        with get_session() as s:
            p = s.get(Patient, patient_id)
            if p:
                s.delete(p)
                s.commit()



def _eager_load(inv: Invoice) -> Invoice:
    """Touch lazy relationships so they are accessible outside the session."""
    _ = inv.patient
    _ = inv.items
    _ = inv.changes
    return inv


class InvoiceDAO:
    """Raw CRUD for Invoice, InvoiceItem, and InvoiceChangeEntry tables."""


    @staticmethod
    def get_all() -> List[Invoice]:
        with get_session() as s:
            invoices = s.exec(
                select(Invoice).order_by(Invoice.invoice_date.desc())
            ).all()
            return [_eager_load(inv) for inv in invoices]

    @staticmethod
    def get_by_patient(patient_id: int) -> List[Invoice]:
        with get_session() as s:
            invoices = s.exec(
                select(Invoice)
                .where(Invoice.patient_id == patient_id)
                .order_by(Invoice.invoice_date.desc())
            ).all()
            return [_eager_load(inv) for inv in invoices]

    @staticmethod
    def get_by_id(invoice_id: int) -> Optional[Invoice]:
        with get_session() as s:
            inv = s.get(Invoice, invoice_id)
            return _eager_load(inv) if inv else None

    @staticmethod
    def insert(invoice: Invoice) -> Invoice:
        with get_session() as s:
            s.add(invoice)
            s.commit()
            s.refresh(invoice)
            return _eager_load(invoice)

    @staticmethod
    def update_status(invoice_id: int, new_status: str,
                      change_entry: InvoiceChangeEntry) -> Invoice:
        with get_session() as s:
            inv = s.get(Invoice, invoice_id)
            if not inv:
                raise ValueError("Invoice not found.")
            inv.status = new_status
            s.add(inv)
            s.add(change_entry)
            s.commit()
            s.refresh(inv)
            return _eager_load(inv)


    @staticmethod
    def get_item_by_id(item_id: int) -> Optional[InvoiceItem]:
        with get_session() as s:
            return s.get(InvoiceItem, item_id)

    @staticmethod
    def add_item(item: InvoiceItem, change_entry: InvoiceChangeEntry) -> InvoiceItem:
        with get_session() as s:
            s.add(item)
            s.add(change_entry)
            s.commit()
            s.refresh(item)
            return item

    @staticmethod
    def soft_delete_item(item_id: int, change_entry: InvoiceChangeEntry) -> None:
        with get_session() as s:
            item = s.get(InvoiceItem, item_id)
            if item:
                item.is_active = False
                s.add(item)
                s.add(change_entry)
                s.commit()


    @staticmethod
    def get_changes(invoice_id: int) -> List[InvoiceChangeEntry]:
        with get_session() as s:
            return s.exec(
                select(InvoiceChangeEntry)
                .where(InvoiceChangeEntry.invoice_id == invoice_id)
                .order_by(InvoiceChangeEntry.changed_at)
            ).all()



def _tariff_to_dict(r: Tariff) -> dict:
    return {
        "id": r.id, "ziffer": r.ziffer, "leistung": r.leistung,
        "uvmv_iv": r.uvmv_iv, "pp_min": r.pp_min,
        "pp_max": r.pp_max, "pp_raw": r.pp_raw,
    }


class TariffDAO:
    """Read-only access to the dental tariff catalogue (db/zahnarzttarif.db)."""

    @staticmethod
    def get_all() -> List[dict]:
        with get_tariff_session() as session:
            rows = (
                session.query(Tariff)
                .filter(Tariff.leistung.isnot(None), Tariff.leistung != "")
                .order_by(Tariff.ziffer)
                .all()
            )
            return [_tariff_to_dict(r) for r in rows]

    @staticmethod
    def search(query: str, limit: int = 50) -> List[dict]:
        q = f"%{query}%"
        with get_tariff_session() as session:
            rows = (
                session.query(Tariff)
                .filter(
                    Tariff.leistung.isnot(None),
                    Tariff.leistung != "",
                    or_(Tariff.ziffer.ilike(q), Tariff.leistung.ilike(q)),
                )
                .order_by(Tariff.ziffer)
                .limit(limit)
                .all()
            )
            return [_tariff_to_dict(r) for r in rows]

    @staticmethod
    def get_sections() -> List[dict]:
        with get_tariff_session() as session:
            rows = session.query(Section).order_by(Section.prefix).all()
            return [{"prefix": r.prefix, "name": r.name} for r in rows]

