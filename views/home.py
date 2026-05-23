"""
View – Home / Dashboard page.
"""
from nicegui import ui

from controllers.services import InvoiceService, PatientService
from views.shared import nav


@ui.page("/")
def home_page() -> None:
    nav()

    with ui.row().classes("items-center gap-3 mt-2 mb-1"):
        ui.icon("local_hospital", size="2.5rem").props("color=primary")
        ui.label("Patient Billing Dashboard").classes("text-3xl font-bold")
    ui.label("Welcome! Use the navigation above or the quick-access cards below.").classes(
        "text-gray-500 mb-8"
    )

    try:
        all_patients = PatientService.get_all()
        all_invoices = InvoiceService.get_all()
    except Exception:
        all_patients = []
        all_invoices = []

    total_patients     = len(all_patients)
    open_invoices      = [i for i in all_invoices if i.status == "open"]
    paid_invoices      = [i for i in all_invoices if i.status == "paid"]
    cancelled_invoices = [i for i in all_invoices if i.status == "cancelled"]
    revenue            = sum(i.total for i in paid_invoices)
    outstanding        = sum(i.total for i in open_invoices)

    # each tuple: (label, value, icon, quasar-color)
    stats = [
        ("Patients",          str(total_patients),            "people",                   "blue"),
        ("Open Invoices",     str(len(open_invoices)),        "hourglass_empty",          "orange"),
        ("Paid Invoices",     str(len(paid_invoices)),        "check_circle",             "positive"),
        ("Cancelled",         str(len(cancelled_invoices)),   "cancel",                   "negative"),
        ("Revenue (CHF)",     f"{revenue:,.2f}",              "payments",                 "positive"),
        ("Outstanding (CHF)", f"{outstanding:,.2f}",          "account_balance_wallet",   "warning"),
    ]

    with ui.row().classes("gap-4 flex-wrap w-full mb-8"):
        for label, value, icon, color in stats:
            with ui.card().classes("flex-1 min-w-40 shadow-sm"):
                with ui.row().classes("items-center gap-3 p-1"):
                    ui.icon(icon, size="2rem").props(f"color={color}")
                    with ui.column().classes("gap-0"):
                        ui.label(value).classes("text-2xl font-bold")
                        ui.label(label).classes("text-sm text-gray-500")

    ui.label("Quick Access").classes("text-xl font-semibold mb-4")
    with ui.row().classes("gap-6 flex-wrap w-full mb-8"):
        with ui.card().classes("w-64 cursor-pointer").on("click", lambda: ui.navigate.to("/patients")):
            with ui.column().classes("items-center p-4 gap-2"):
                ui.icon("people", size="3rem").props("color=primary")
                ui.label("Patients").classes("text-lg font-semibold")
                ui.label("Manage patient records").classes("text-sm text-gray-400 text-center")

        with ui.card().classes("w-64 cursor-pointer").on("click", lambda: ui.navigate.to("/invoices")):
            with ui.column().classes("items-center p-4 gap-2"):
                ui.icon("receipt_long", size="3rem").props("color=secondary")
                ui.label("Invoices").classes("text-lg font-semibold")
                ui.label("View and manage all invoices").classes("text-sm text-gray-400 text-center")

    if open_invoices:
        ui.label("Open Invoices").classes("text-xl font-semibold mb-2")
        columns = [
            {"name": "id",      "label": "Invoice #", "field": "id",      "align": "left"},
            {"name": "patient", "label": "Patient",   "field": "patient", "align": "left"},
            {"name": "date",    "label": "Date",       "field": "date",   "align": "left"},
            {"name": "due",     "label": "Due",        "field": "due",    "align": "left"},
            {"name": "total",   "label": "Total CHF",  "field": "total",  "align": "right"},
            {"name": "status",  "label": "Status",     "field": "status", "align": "left"},
        ]
        rows = [
            {
                "id":      inv.id,
                "patient": (
                    f"{inv.patient.first_name} {inv.patient.last_name}"
                    if inv.patient else "—"
                ),
                "date":   inv.invoice_date,
                "due":    inv.due_date or "—",
                "total":  f"{inv.total:.2f}",
                "status": inv.status.upper(),
            }
            for inv in sorted(open_invoices, key=lambda i: i.id, reverse=True)[:10]
        ]
        tbl = ui.table(columns=columns, rows=rows, row_key="id").classes("w-full")
        tbl.add_slot("body-cell-status", """
            <q-td :props="props">
                <q-badge color="orange">{{ props.value }}</q-badge>
            </q-td>
        """)
