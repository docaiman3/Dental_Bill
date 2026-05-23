"""
View – Invoices page.
"""
from datetime import date

from dateutil.relativedelta import relativedelta
from nicegui import ui

from controllers.services import InvoiceService, PatientService
from views.patients import invoice_card
from views.shared import nav, notify_error, notify_ok, validate_date, normalise_date

_DEFAULT_DUE = lambda: (date.today() + relativedelta(months=1)).isoformat()

@ui.page("/invoices")
def invoices_page(patient_id: int = None) -> None:
    nav()

    if patient_id:
        patient = PatientService.get_by_id(patient_id)
        title = f"Invoices – {patient.first_name} {patient.last_name}" if patient else "Invoices"
    else:
        title = "All Invoices"

    ui.label(title).classes("text-2xl font-bold mb-4")

    with ui.card().classes("w-full mb-6"):
        ui.label("New Invoice").classes("text-lg font-semibold mb-2")

        # ── Patient selection (only shown when not pre-filtered by patient_id) ──
        pat_select = None
        if not patient_id:
            patients = PatientService.get_all()
            pat_options = {p.id: f"{p.last_name}, {p.first_name} (ID {p.id})" for p in patients}

            with ui.row().classes("gap-4 flex-wrap items-end mb-3"):
                search_pid   = ui.number("Search by Patient ID", min=1, step=1, format="%d").classes("w-44")
                search_label = ui.label("").classes("text-sm text-gray-500 self-center")

                def find_patient_for_invoice():
                    val = search_pid.value
                    if not val:
                        search_label.set_text("Enter an ID.")
                        return
                    p = PatientService.get_by_id(int(val))
                    if p:
                        pat_select.set_value(p.id)
                        search_label.set_text(
                            f"✓  {p.gender or ''} {p.first_name} {p.last_name}".strip()
                        )
                    else:
                        pat_select.set_value(None)
                        search_label.set_text(f"No patient found with ID {int(val)}.")

                ui.button("Find", icon="search",
                          on_click=find_patient_for_invoice).props("color=primary dense")

            pat_select = ui.select(
                pat_options,
                label="Patient",
                with_input=True,
                clearable=True,
            ).classes("w-72 mb-2")

        with ui.row().classes("gap-4 flex-wrap items-end"):
            due = ui.input(
                "Fälligkeitsdatum (DD.MM.YYYY oder YYYY-MM-DD)",
                value=_DEFAULT_DUE(),
                validation=validate_date,
            ).classes("w-96")

        def create_invoice():
            pid = patient_id if patient_id else (pat_select.value if pat_select else None)
            if not pid:
                notify_error("Please select a patient.")
                return
            if validate_date(due.value):
                notify_error(validate_date(due.value))
                return
            inv = InvoiceService.create(pid, normalise_date(due.value))
            notify_ok(f"Invoice #{inv.id} created.")
            due.value = _DEFAULT_DUE()
            refresh_invoices()

        ui.button("Create Invoice", on_click=create_invoice, icon="add").classes("mt-3")

    inv_container = ui.column().classes("w-full gap-4")

    def refresh_invoices():
        inv_container.clear()
        invoices = (
            InvoiceService.get_by_patient(patient_id)
            if patient_id
            else InvoiceService.get_all()
        )
        with inv_container:
            if not invoices:
                ui.label("No invoices yet.").classes("text-gray-400")
                return
            for inv in invoices:
                invoice_card(inv, refresh_invoices)

    refresh_invoices()

