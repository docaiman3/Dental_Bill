"""
Shared UI helpers used across all views.
"""
from datetime import datetime

from nicegui import ui

STATUS_COLOR = {"open": "orange", "paid": "green", "cancelled": "red"}


def validate_date(value: str) -> str | None:
    """Return an error message if *value* is not a valid date, else None.

    Accepts both German format DD.MM.YYYY (e.g. 18.10.1993)
    and ISO format YYYY-MM-DD (e.g. 1993-10-18).
    """
    if not value:
        return None          # empty is allowed – required-field checks happen elsewhere
    v = value.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            datetime.strptime(v, fmt)
            return None
        except ValueError:
            continue
    return "Ungültiges Datum – bitte DD.MM.YYYY oder YYYY-MM-DD eingeben (z.B. 18.10.1993)"


def normalise_date(value: str) -> str:
    """Convert DD.MM.YYYY → YYYY-MM-DD.  ISO dates are returned unchanged."""
    v = value.strip()
    try:
        return datetime.strptime(v, "%d.%m.%Y").strftime("%Y-%m-%d")
    except ValueError:
        return v   # already ISO or empty


def notify_error(msg: str) -> None:
    ui.notify(msg, color="negative", position="top")


def notify_ok(msg: str) -> None:
    ui.notify(msg, color="positive", position="top")


def nav() -> None:
    """Persistent top navigation bar."""
    with ui.header().classes("bg-blue-700 text-white px-6 py-3 flex items-center gap-6"):
        with ui.link(target="/").classes("flex items-center gap-2 mr-6 text-white no-underline"):
            ui.icon("local_hospital", size="1.8rem").props("color=white")
            ui.label("Patient Billing").classes("text-xl font-bold text-white")
        ui.button("Patients", on_click=lambda: ui.navigate.to("/patients"), icon="people").props("flat color=white")
        ui.button("Invoices", on_click=lambda: ui.navigate.to("/invoices"), icon="receipt_long").props("flat color=white")

