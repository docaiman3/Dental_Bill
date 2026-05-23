"""
Application Logic (Server-Side) – Service classes that encapsulate all
business rules. The UI layer calls these; it never touches the ORM directly.

Data access is fully delegated to the DAO layer (controllers/dao.py).
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional

# Ensure project root (Bills/) is on sys.path regardless of how this is run
_here = Path(__file__).parent          # Bills/controllers/
_root = _here.parent                   # Bills/
for _p in (str(_here), str(_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from ..domain.models import Invoice, InvoiceChangeEntry, InvoiceItem, Patient
    from .dao import InvoiceDAO, PatientDAO, TariffDAO
except ImportError:
    from domain.models import Invoice, InvoiceChangeEntry, InvoiceItem, Patient  # type: ignore[import]
    from dao import InvoiceDAO, PatientDAO, TariffDAO                             # type: ignore[import]



class PatientService:
    """Validation + orchestration for Patient entities."""

    @staticmethod
    def get_all() -> List[Patient]:
        try:
            return PatientDAO.get_all()
        except Exception as exc:
            raise RuntimeError(f"Could not retrieve patients: {exc}") from exc

    @staticmethod
    def get_by_id(patient_id: int) -> Optional[Patient]:
        try:
            return PatientDAO.get_by_id(patient_id)
        except Exception as exc:
            raise RuntimeError(f"Could not retrieve patient {patient_id}: {exc}") from exc

    @staticmethod
    def _validate_plz(plz: str) -> str:
        v = plz.strip()
        if v and not v.isdigit():
            raise ValueError("PLZ must contain digits only.")
        return v or ""

    @staticmethod
    def create(first_name: str, last_name: str,
               dob: str = "", insurance: str = "",
               street: str = "", plz: str = "", city: str = "",
               gender: str = "") -> Patient:
        try:
            if not first_name.strip() or not last_name.strip():
                raise ValueError("First name and last name are required.")
            plz = PatientService._validate_plz(plz)
            patient = Patient(
                gender=gender.strip() or None,
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                date_of_birth=dob.strip() or None,
                insurance_number=insurance.strip() or None,
                street=street.strip() or None,
                plz=plz or None,
                city=city.strip() or None,
            )
            return PatientDAO.insert(patient)
        except ValueError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Could not create patient: {exc}") from exc

    @staticmethod
    def update(patient_id: int, first_name: str, last_name: str,
               dob: str = "", insurance: str = "",
               street: str = "", plz: str = "", city: str = "",
               gender: str = "") -> Patient:
        try:
            if not first_name.strip() or not last_name.strip():
                raise ValueError("First name and last name are required.")
            plz = PatientService._validate_plz(plz)
            patient = Patient(
                id=patient_id,
                gender=gender.strip() or None,
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                date_of_birth=dob.strip() or None,
                insurance_number=insurance.strip() or None,
                street=street.strip() or None,
                plz=plz or None,
                city=city.strip() or None,
            )
            return PatientDAO.update(patient)
        except ValueError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Could not update patient {patient_id}: {exc}") from exc

    @staticmethod
    def delete(patient_id: int) -> None:
        try:
            PatientDAO.delete(patient_id)
        except Exception as exc:
            raise RuntimeError(f"Could not delete patient {patient_id}: {exc}") from exc



class InvoiceService:
    """Validation + orchestration for Invoice entities."""

    @staticmethod
    def get_all() -> List[Invoice]:
        try:
            return InvoiceDAO.get_all()
        except Exception as exc:
            raise RuntimeError(f"Could not retrieve invoices: {exc}") from exc

    @staticmethod
    def get_by_patient(patient_id: int) -> List[Invoice]:
        try:
            return InvoiceDAO.get_by_patient(patient_id)
        except Exception as exc:
            raise RuntimeError(f"Could not retrieve invoices for patient {patient_id}: {exc}") from exc

    @staticmethod
    def get_by_id(invoice_id: int) -> Optional[Invoice]:
        try:
            return InvoiceDAO.get_by_id(invoice_id)
        except Exception as exc:
            raise RuntimeError(f"Could not retrieve invoice {invoice_id}: {exc}") from exc

    @staticmethod
    def create(patient_id: int, due_date: str = "") -> Invoice:
        try:
            if not due_date.strip():
                due_date = (date.today() + timedelta(days=30)).isoformat()
            invoice = Invoice(
                patient_id=patient_id,
                due_date=due_date.strip() or None,
            )
            return InvoiceDAO.insert(invoice)
        except ValueError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Could not create invoice: {exc}") from exc

    @staticmethod
    def set_status(invoice_id: int, status: str) -> Invoice:
        try:
            allowed = {"open", "paid", "cancelled"}
            if status not in allowed:
                raise ValueError(f"Status must be one of {allowed}")
            inv = InvoiceDAO.get_by_id(invoice_id)
            if not inv:
                raise ValueError("Invoice not found.")
            entry = InvoiceChangeEntry(
                invoice_id=invoice_id,
                change_type="status_change",
                old_status=inv.status,
                new_status=status,
            )
            return InvoiceDAO.update_status(invoice_id, status, entry)
        except ValueError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Could not update status for invoice {invoice_id}: {exc}") from exc

    @staticmethod
    def delete(invoice_id: int) -> None:
        raise ValueError(
            "Invoices are immutable. Use set_status('cancelled') to void an invoice."
        )

    @staticmethod
    def get_changes(invoice_id: int) -> List[InvoiceChangeEntry]:
        try:
            return InvoiceDAO.get_changes(invoice_id)
        except Exception as exc:
            raise RuntimeError(f"Could not retrieve change log for invoice {invoice_id}: {exc}") from exc

    @staticmethod
    def add_item(invoice_id: int, description: str,
                 quantity: float, unit_price: float) -> InvoiceItem:
        try:
            if not description.strip():
                raise ValueError("Description is required.")
            if quantity <= 0 or unit_price < 0:
                raise ValueError("Quantity must be > 0 and price >= 0.")
            item = InvoiceItem(
                invoice_id=invoice_id,
                description=description.strip(),
                quantity=quantity,
                unit_price=unit_price,
            )
            entry = InvoiceChangeEntry(
                invoice_id=invoice_id,
                change_type="item_added",
                item_description=description.strip(),
                item_quantity=quantity,
                item_unit_price=unit_price,
            )
            return InvoiceDAO.add_item(item, entry)
        except ValueError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Could not add item to invoice {invoice_id}: {exc}") from exc

    @staticmethod
    def delete_item(item_id: int) -> None:
        try:
            item = InvoiceDAO.get_item_by_id(item_id)
            if not item:
                return
            entry = InvoiceChangeEntry(
                invoice_id=item.invoice_id,
                change_type="item_removed",
                item_description=item.description,
                item_quantity=item.quantity,
                item_unit_price=item.unit_price,
            )
            InvoiceDAO.soft_delete_item(item_id, entry)
        except Exception as exc:
            raise RuntimeError(f"Could not remove item {item_id}: {exc}") from exc



class TariffService:
    """Read-only access to the dental tariff catalogue – delegates to TariffDAO."""

    @staticmethod
    def get_all() -> List[dict]:
        return TariffDAO.get_all()

    @staticmethod
    def search(query: str, limit: int = 50) -> List[dict]:
        return TariffDAO.search(query, limit)

    @staticmethod
    def get_sections() -> List[dict]:
        return TariffDAO.get_sections()
