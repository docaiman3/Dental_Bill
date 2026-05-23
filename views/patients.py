"""
View – Patients page.
"""
import tempfile
import os

from nicegui import ui

from controllers.services import InvoiceService, PatientService, TariffService
from controllers.pdf_service import generate_invoice_pdf
from views.shared import STATUS_COLOR, nav, notify_error, notify_ok, validate_date, normalise_date
def invoice_card(inv, refresh_cb) -> None:
    """Renders one invoice as a collapsible card with item management."""
    color = STATUS_COLOR.get(inv.status, "gray")
    with ui.card().classes("w-full"):
        with ui.row().classes("items-center justify-between w-full"):
            with ui.column().classes("cursor-pointer").on("click", lambda inv_id=inv.id: ui.navigate.to(f"/invoices/{inv_id}")):
                patient_name = (
                    f"{inv.patient.first_name} {inv.patient.last_name}"
                    if inv.patient else "Unknown"
                )
                ui.label(f"Invoice {inv.id}  –  {patient_name}").classes("font-bold text-lg hover:text-primary")
                ui.label(f"Date: {inv.invoice_date}   Due: {inv.due_date or '—'}").classes("text-sm text-gray-500")

            with ui.row().classes("items-center gap-3"):
                ui.badge(inv.status.upper(), color=color)
                ui.label(f"CHF {inv.total:.2f}").classes("font-semibold text-lg")

                status_select = ui.select(
                    ["open", "paid", "cancelled"],
                    value=inv.status,
                    label="Status",
                ).classes("w-32")

                def update_status(invoice_id=inv.id):
                    InvoiceService.set_status(invoice_id, status_select.value)
                    notify_ok("Status updated.")
                    refresh_cb()

                status_select.on("update:model-value", lambda _e: update_status())

                def download_pdf(invoice_id=inv.id):
                    try:
                        pdf_bytes = generate_invoice_pdf(invoice_id)
                        # Write to a temp file; NiceGUI will serve it once then it's removed.
                        tmp = tempfile.NamedTemporaryFile(
                            delete=False, suffix=".pdf",
                            prefix=f"invoice_{invoice_id}_",
                        )
                        tmp.write(pdf_bytes)
                        tmp.close()
                        ui.download(tmp.name, filename=f"invoice_{invoice_id}.pdf")
                        # Schedule cleanup after a short delay
                        async def _cleanup():
                            import asyncio
                            await asyncio.sleep(5)
                            try:
                                os.unlink(tmp.name)
                            except OSError:
                                pass
                        import asyncio
                        asyncio.ensure_future(_cleanup())
                    except Exception as e:
                        notify_error(f"PDF error: {e}")

                ui.button(icon="picture_as_pdf", on_click=download_pdf).props(
                    "flat dense color=primary"
                ).tooltip("Download PDF")

        with ui.expansion("Items", icon="list").classes("w-full mt-2"):
            items_col = ui.column().classes("w-full gap-1")

            def render_items():
                items_col.clear()
                fresh = InvoiceService.get_by_id(inv.id)
                active_items = [i for i in fresh.items if i.is_active] if fresh else []
                with items_col:
                    if not active_items:
                        ui.label("No items yet.").classes("text-gray-400 text-sm")
                    else:
                        for item in active_items:
                            with ui.row().classes("items-center gap-4 w-full"):
                                ui.label(item.description).classes("flex-1")
                                ui.label(f"{item.quantity} ×").classes("w-10 text-right text-sm")
                                ui.label(f"CHF {item.unit_price:.2f}").classes("w-20 text-right text-sm")
                                ui.label(f"= CHF {item.quantity * item.unit_price:.2f}").classes("w-24 text-right font-semibold text-sm")

                                def del_item(item_id=item.id):
                                    InvoiceService.delete_item(item_id)
                                    render_items()
                                    refresh_cb()

                                ui.button(icon="close", on_click=del_item).props("flat dense size=xs color=negative")

            render_items()

            all_tariffs = TariffService.get_all()
            tariff_options = {
                t["id"]: f"{t['ziffer']}  –  {t['leistung']}"
                for t in all_tariffs
            }
            tariff_map = {t["id"]: t for t in all_tariffs}

            # staged_qtys holds  id -> ui.number  for the currently staged rows
            staged_qtys: dict = {}

            ui.label("Add Treatments from Tariff").classes("text-sm font-semibold text-gray-600 mt-4")

            tariff_select = (
                ui.select(
                    tariff_options,
                    label="Search & select one or more treatments…",
                    with_input=True,
                    multiple=True,
                    clearable=True,
                )
                .classes("w-full mt-1")
            )

            staging_col = ui.column().classes("w-full gap-1 mt-2")

            def render_staging():
                staging_col.clear()
                staged_qtys.clear()
                selected_ids = tariff_select.value or []
                if not selected_ids:
                    return
                with staging_col:
                    with ui.row().classes("w-full text-xs text-gray-400 font-semibold px-1 gap-3"):
                        ui.label("Treatment").classes("flex-1")
                        ui.label("Qty").classes("w-20 text-center")
                        ui.label("Unit CHF").classes("w-24 text-right")
                        ui.label("Total CHF").classes("w-24 text-right")
                    for tid in selected_ids:
                        t = tariff_map.get(tid)
                        if not t:
                            continue
                        unit = float(t["uvmv_iv"]) if t["uvmv_iv"] else 0.0
                        label_text = f"{t['ziffer']} – {t['leistung']}"
                        with ui.row().classes("items-center gap-3 w-full flex-wrap bg-gray-50 rounded px-2 py-1"):
                            ui.label(label_text).classes("flex-1 text-sm min-w-48")
                            q_widget = ui.number(
                                "Qty", value=1, min=0.5, step=0.5, format="%.2f"
                            ).classes("w-20")
                            staged_qtys[tid] = q_widget
                            ui.label(f"{unit:.2f}").classes("w-24 text-right text-sm text-gray-500")
                            # live total label – updated when qty changes
                            total_lbl = ui.label(f"{unit:.2f}").classes("w-24 text-right text-sm font-semibold")

                            def _update_total(_, lbl=total_lbl, u=unit, qw=q_widget):
                                try:
                                    lbl.set_text(f"{float(qw.value or 1) * u:.2f}")
                                except Exception:
                                    pass

                            q_widget.on("update:model-value", _update_total)

            tariff_select.on("update:model-value", lambda _e: render_staging())

            def add_staged_items(invoice_id=inv.id):
                selected_ids = tariff_select.value or []
                if not selected_ids:
                    notify_error("No treatments selected.")
                    return
                added = 0
                for tid in selected_ids:
                    t = tariff_map.get(tid)
                    if not t:
                        continue
                    q_widget = staged_qtys.get(tid)
                    qty_val = float(q_widget.value or 1) if q_widget else 1.0
                    price_val = float(t["uvmv_iv"]) if t["uvmv_iv"] else 0.0
                    desc_val = f"{t['ziffer']} – {t['leistung']}"
                    try:
                        InvoiceService.add_item(invoice_id, desc_val, qty_val, price_val)
                        added += 1
                    except ValueError as e:
                        notify_error(str(e))
                if added:
                    tariff_select.set_value([])
                    staging_col.clear()
                    staged_qtys.clear()
                    render_items()
                    refresh_cb()
                    notify_ok(f"{added} treatment(s) added.")

            ui.button("Add Selected Treatments", icon="add_shopping_cart",
                      on_click=add_staged_items).props("color=primary").classes("mt-2")

            ui.separator().classes("my-4")
            ui.label("Or add a custom item manually:").classes("text-xs text-gray-400")
            with ui.row().classes("gap-3 mt-1 flex-wrap items-end"):
                desc = ui.input("Description").classes("w-48")
                qty  = ui.number("Qty", value=1, min=0.5, step=0.5, format="%.2f").classes("w-20")
                price = ui.number("Unit Price (CHF)", value=0.0, min=0, step=0.01, format="%.2f").classes("w-36")

            def add_manual_item(invoice_id=inv.id):
                try:
                    InvoiceService.add_item(invoice_id, desc.value, qty.value, price.value)
                    desc.value = ""
                    qty.value = 1
                    price.value = 0.0
                    render_items()
                    refresh_cb()
                except ValueError as e:
                    notify_error(str(e))

            ui.button("Add Item", icon="add", on_click=add_manual_item).classes("mt-1")

        with ui.expansion("Change History", icon="history").classes("w-full mt-1"):
            history_col = ui.column().classes("w-full gap-1")

            CHANGE_COLOR = {
                "status_change": "blue",
                "item_added": "green",
                "item_removed": "red",
            }

            def render_history():
                history_col.clear()
                entries = InvoiceService.get_changes(inv.id)
                with history_col:
                    if not entries:
                        ui.label("No changes recorded.").classes("text-gray-400 text-sm")
                        return
                    for entry in entries:
                        badge_color = CHANGE_COLOR.get(entry.change_type, "gray")
                        if entry.change_type == "status_change":
                            summary = f"Status: {entry.old_status} → {entry.new_status}"
                        elif entry.change_type == "item_added":
                            summary = (
                                f"Added: {entry.item_description} "
                                f"× {entry.item_quantity} @ CHF {entry.item_unit_price:.2f}"
                            )
                        elif entry.change_type == "item_removed":
                            summary = f"Removed: {entry.item_description} × {entry.item_quantity}"
                        else:
                            summary = entry.change_type

                        try:
                            from datetime import datetime
                            ts = datetime.fromisoformat(entry.changed_at).astimezone().strftime("%Y-%m-%d %H:%M")
                        except Exception:
                            ts = entry.changed_at[:16]

                        with ui.row().classes("items-center gap-3 text-sm"):
                            ui.label(ts).classes("text-gray-500 w-36")
                            ui.badge(entry.change_type.replace("_", " ").upper(), color=badge_color)
                            ui.label(summary)

            render_history()
@ui.page("/patients")
def patients_page() -> None:
    nav()
    ui.label("Patients").classes("text-2xl font-bold mb-4")

    with ui.card().classes("w-full mb-6"):
        ui.label("New Patient").classes("text-lg font-semibold mb-2")
        with ui.row().classes("gap-4 flex-wrap"):
            fn  = ui.input("First Name").classes("w-40")
            ln  = ui.input("Last Name").classes("w-40")
            dob = ui.input("Geburtsdatum (DD.MM.YYYY oder YYYY-MM-DD)", validation=validate_date).classes("w-52")
            ins = ui.input("Insurance Number").classes("w-44")
        with ui.row().classes("gap-4 flex-wrap mt-2"):
            street = ui.input("Street").classes("w-56")
            plz    = ui.input(
                "PLZ",
                validation=lambda v: None if (v == "" or v.isdigit())
                           else "PLZ darf nur Ziffern enthalten",
            ).classes("w-24")
            city   = ui.input("City").classes("w-44")

        def add_patient():
            if plz.value and not plz.value.isdigit():
                notify_error("PLZ darf nur Ziffern enthalten.")
                return
            if validate_date(dob.value):
                notify_error(validate_date(dob.value))
                return
            try:
                PatientService.create(
                    fn.value, ln.value, normalise_date(dob.value), ins.value,
                    street.value, str(int(plz.value)) if plz.value else "", city.value,
                )
                notify_ok("Patient added.")
                fn.value = ln.value = dob.value = ins.value = ""
                street.value = city.value = ""
                plz.value = ""
                refresh_table()
            except ValueError as e:
                notify_error(str(e))

        ui.button("Add Patient", on_click=add_patient, icon="person_add").classes("mt-3")

    table_container = ui.column().classes("w-full")

    with ui.dialog() as edit_dialog, ui.card().classes("w-full max-w-2xl"):
        ui.label("Edit Patient").classes("text-lg font-semibold mb-2")
        with ui.row().classes("gap-4 flex-wrap"):
            e_fn  = ui.input("First Name").classes("w-40")
            e_ln  = ui.input("Last Name").classes("w-40")
            e_dob = ui.input("Geburtsdatum (DD.MM.YYYY oder YYYY-MM-DD)", validation=validate_date).classes("w-52")
            e_ins = ui.input("Insurance Number").classes("w-44")
        with ui.row().classes("gap-4 flex-wrap mt-2"):
            e_street = ui.input("Street").classes("w-56")
            e_plz    = ui.input(
                "PLZ",
                validation=lambda v: None if (v == "" or v.isdigit())
                           else "PLZ darf nur Ziffern enthalten",
            ).classes("w-24")
            e_city   = ui.input("City").classes("w-44")

        edit_patient_id: list = [None]   # mutable container to hold current id

        def save_edit():
            if e_plz.value and not e_plz.value.isdigit():
                notify_error("PLZ darf nur Ziffern enthalten.")
                return
            if validate_date(e_dob.value):
                notify_error(validate_date(e_dob.value))
                return
            try:
                PatientService.update(
                    edit_patient_id[0],
                    e_fn.value, e_ln.value, normalise_date(e_dob.value), e_ins.value,
                    e_street.value,
                    str(int(e_plz.value)) if e_plz.value else "",
                    e_city.value,
                )
                notify_ok("Patient updated.")
                edit_dialog.close()
                refresh_table()
            except ValueError as ex:
                notify_error(str(ex))

        with ui.row().classes("gap-3 mt-4"):
            ui.button("Save", icon="save", on_click=save_edit).props("color=primary")
            ui.button("Cancel", on_click=edit_dialog.close).props("flat")

    def open_edit(row: dict):
        """Pre-fill the edit dialog and open it."""
        pid = row["id"]
        p   = PatientService.get_by_id(pid)
        if not p:
            notify_error("Patient not found.")
            return
        edit_patient_id[0] = pid
        e_fn.value     = p.first_name
        e_ln.value     = p.last_name
        e_dob.value    = p.date_of_birth or ""
        e_ins.value    = p.insurance_number or ""
        e_street.value = p.street or ""
        e_plz.value    = p.plz or ""
        e_city.value   = p.city or ""
        edit_dialog.open()

    def refresh_table():
        table_container.clear()
        patients = PatientService.get_all()
        with table_container:
            if not patients:
                ui.label("No patients yet.").classes("text-gray-400")
                return
            columns = [
                {"name": "id",        "label": "ID",            "field": "id",        "align": "left"},
                {"name": "last",      "label": "Last Name",     "field": "last",      "align": "left"},
                {"name": "first",     "label": "First Name",    "field": "first",     "align": "left"},
                {"name": "dob",       "label": "Date of Birth", "field": "dob",       "align": "left"},
                {"name": "insurance", "label": "Insurance No.", "field": "insurance", "align": "left"},
                {"name": "street",    "label": "Street",        "field": "street",    "align": "left"},
                {"name": "plz",       "label": "PLZ",           "field": "plz",       "align": "left"},
                {"name": "city",      "label": "City",          "field": "city",      "align": "left"},
                {"name": "actions",   "label": "Actions",       "field": "actions",   "align": "left"},
            ]
            rows = [
                {
                    "id": p.id,
                    "last": p.last_name,
                    "first": p.first_name,
                    "dob": p.date_of_birth or "—",
                    "insurance": p.insurance_number or "—",
                    "street": p.street or "—",
                    "plz": p.plz or "—",
                    "city": p.city or "—",
                }
                for p in patients
            ]
            tbl = ui.table(columns=columns, rows=rows, row_key="id").classes("w-full")
            tbl.add_slot("body-cell-actions", """
                <q-td :props="props">
                    <q-btn flat dense icon="edit" color="primary"
                        @click="$parent.$emit('edit', props.row)" />
                    <q-btn flat dense icon="receipt_long" color="secondary"
                        @click="$parent.$emit('invoice', props.row)" />
                    <q-btn flat dense icon="delete" color="negative"
                        @click="$parent.$emit('delete', props.row)" />
                </q-td>
            """)

            tbl.on("edit",    lambda e: open_edit(e.args))
            tbl.on("invoice", lambda e: ui.navigate.to(f"/invoices?patient_id={e.args['id']}"))
            tbl.on("delete",  lambda e: (
                PatientService.delete(e.args["id"]),
                notify_ok("Patient deleted."),
                refresh_table(),
            ))

    refresh_table()

