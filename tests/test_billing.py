"""
Test suite – Patient Billing Application.

15 tests across three categories:
- unit tests for validation and orchestration
- DAO tests against an isolated in-memory SQLite database
- integration tests for full service-layer flows
"""
from datetime import date, timedelta

import pytest


class TestPatientValidation:
    """PatientService validation and normalisation."""

    def test_TC_001_create_patient_strips_and_normalises_optional_fields(self, monkeypatch):
        import controllers.services as services

        def fake_insert(patient):
            patient.id = 1
            return patient

        monkeypatch.setattr(services.PatientDAO, "insert", staticmethod(fake_insert))

        patient = services.PatientService.create(
            " Anna ",
            " Müller ",
            " ",
            " INS-1 ",
            " Bahnhofstrasse 1 ",
            " 8001 ",
            " Zürich ",
        )

        assert patient.first_name == "Anna"
        assert patient.last_name == "Müller"
        assert patient.date_of_birth is None
        assert patient.insurance_number == "INS-1"
        assert patient.street == "Bahnhofstrasse 1"
        assert patient.plz == "8001"
        assert patient.city == "Zürich"

    def test_TC_002_create_patient_requires_first_and_last_name(self):
        from controllers.services import PatientService

        with pytest.raises(ValueError, match="First name and last name are required."):
            PatientService.create("", "Müller")

        with pytest.raises(ValueError, match="First name and last name are required."):
            PatientService.create("Anna", " ")

    def test_TC_003_create_patient_rejects_non_digit_plz(self):
        from controllers.services import PatientService

        with pytest.raises(ValueError, match="PLZ must contain digits only."):
            PatientService.create("Anna", "Müller", plz="80A1")

    def test_TC_004_update_patient_requires_names(self):
        from controllers.services import PatientService

        with pytest.raises(ValueError, match="First name and last name are required."):
            PatientService.update(1, "Anna", "")


class TestInvoiceValidation:
    """InvoiceService validation rules."""

    def test_TC_005_create_invoice_defaults_due_date(self, monkeypatch):
        import controllers.services as services

        monkeypatch.setattr(services.InvoiceDAO, "insert", staticmethod(lambda invoice: invoice))

        invoice = services.InvoiceService.create(7)

        assert invoice.patient_id == 7
        assert invoice.due_date == (date.today() + timedelta(days=30)).isoformat()

    def test_TC_006_add_item_requires_description(self):
        from controllers.services import InvoiceService

        with pytest.raises(ValueError, match="Description is required."):
            InvoiceService.add_item(1, " ", 1, 10.0)

    def test_TC_007_add_item_rejects_invalid_numbers(self):
        from controllers.services import InvoiceService

        with pytest.raises(ValueError, match="Quantity must be > 0 and price >= 0."):
            InvoiceService.add_item(1, "Exam", 0, 10.0)

        with pytest.raises(ValueError, match="Quantity must be > 0 and price >= 0."):
            InvoiceService.add_item(1, "Exam", 1, -1.0)

    def test_TC_008_set_status_rejects_unknown_status(self):
        from controllers.services import InvoiceService

        with pytest.raises(ValueError, match="Status must be one of"):
            InvoiceService.set_status(1, "draft")

    def test_TC_009_delete_invoice_is_forbidden(self):
        from controllers.services import InvoiceService

        with pytest.raises(ValueError, match="Invoices are immutable."):
            InvoiceService.delete(1)


class TestDAOBehaviour:
    """DAO round-trips against the in-memory test database."""

    def test_TC_010_patient_dao_round_trip(self, billing_db):
        from controllers.dao import PatientDAO
        from domain.models import Patient

        patient = Patient(
            first_name="Anna",
            last_name="Müller",
            street="Bahnhofstrasse 1",
            plz="8001",
            city="Zürich",
        )
        created = PatientDAO.insert(patient)
        assert created.id is not None

        updated = Patient(
            id=created.id,
            first_name="Anna",
            last_name="Meier",
            street="Marktgasse 2",
            plz="3000",
            city="Bern",
        )
        stored = PatientDAO.update(updated)
        assert stored.last_name == "Meier"
        assert stored.city == "Bern"

        PatientDAO.delete(created.id)
        assert PatientDAO.get_by_id(created.id) is None

    def test_TC_011_patient_dao_get_all_sorts_by_last_name(self, billing_db):
        from controllers.dao import PatientDAO
        from domain.models import Patient

        PatientDAO.insert(Patient(first_name="Sophie", last_name="Zimmermann"))
        PatientDAO.insert(Patient(first_name="Anna", last_name="Aebi"))
        PatientDAO.insert(Patient(first_name="Laura", last_name="Müller"))

        last_names = [patient.last_name for patient in PatientDAO.get_all()]
        assert last_names == ["Aebi", "Müller", "Zimmermann"]

    def test_TC_012_invoice_dao_tracks_items_and_changes(self, billing_db):
        from controllers.dao import InvoiceDAO, PatientDAO
        from domain.models import Invoice, InvoiceChangeEntry, InvoiceItem, Patient

        patient = PatientDAO.insert(Patient(first_name="Markus", last_name="Weber"))
        invoice = InvoiceDAO.insert(Invoice(patient_id=patient.id, due_date="2026-01-01"))

        added = InvoiceDAO.add_item(
            InvoiceItem(
                invoice_id=invoice.id,
                description="Extraktion",
                quantity=1,
                unit_price=100.0,
            ),
            InvoiceChangeEntry(
                invoice_id=invoice.id,
                change_type="item_added",
                item_description="Extraktion",
                item_quantity=1,
                item_unit_price=100.0,
            ),
        )
        InvoiceDAO.soft_delete_item(
            added.id,
            InvoiceChangeEntry(
                invoice_id=invoice.id,
                change_type="item_removed",
                item_description="Extraktion",
                item_quantity=1,
                item_unit_price=100.0,
            ),
        )

        db_item = InvoiceDAO.get_item_by_id(added.id)
        changes = InvoiceDAO.get_changes(invoice.id)

        assert db_item is not None
        assert db_item.is_active is False
        assert [entry.change_type for entry in changes] == ["item_added", "item_removed"]


class TestInvoiceIntegration:
    """End-to-end service flows."""

    def test_TC_013_create_invoice_add_item_total_matches(self, billing_db):
        from controllers.services import InvoiceService, PatientService

        patient = PatientService.create("Sophie", "Koch")
        invoice = InvoiceService.create(patient.id)
        InvoiceService.add_item(invoice.id, "Befundaufnahme", quantity=1, unit_price=73.0)
        InvoiceService.add_item(invoice.id, "Anästhesie", quantity=2, unit_price=38.4)

        fresh = InvoiceService.get_by_id(invoice.id)
        assert fresh is not None
        assert pytest.approx(fresh.total, rel=1e-6) == 149.8

    def test_TC_014_delete_item_soft_removes_it_from_total(self, billing_db):
        from controllers.dao import InvoiceDAO
        from controllers.services import InvoiceService, PatientService

        patient = PatientService.create("Markus", "Weber")
        invoice = InvoiceService.create(patient.id)
        item = InvoiceService.add_item(invoice.id, "Extraktion", quantity=1, unit_price=100.0)

        InvoiceService.delete_item(item.id)

        db_item = InvoiceDAO.get_item_by_id(item.id)
        fresh = InvoiceService.get_by_id(invoice.id)

        assert db_item is not None
        assert db_item.is_active is False
        assert fresh is not None
        assert fresh.total == 0.0

    def test_TC_015_set_status_creates_change_log_entry(self, billing_db):
        from controllers.dao import InvoiceDAO
        from controllers.services import InvoiceService, PatientService

        patient = PatientService.create("Anna", "Müller")
        invoice = InvoiceService.create(patient.id)

        updated = InvoiceService.set_status(invoice.id, "paid")
        changes = InvoiceDAO.get_changes(invoice.id)

        assert updated.status == "paid"
        assert len(changes) == 1
        assert changes[0].change_type == "status_change"
        assert changes[0].old_status == "open"
        assert changes[0].new_status == "paid"
