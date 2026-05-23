"""
PDF Service – Modern Premium Swiss Dental Clinic Invoice.

Design system:
  • Accent:   #4A7C6F  (deep sage-teal — calm, medical, premium)
  • Warm bg:  #FAFAF8  (soft warm white)
  • Cards:    #F5F4F1  (warm light beige)
  • Dividers: #E8E6E1  (warm gray)
  • Text:     #2C2C2C / #5C5C5C / #9A9A9A
  • Status:   amber · emerald · rose
  • Fonts:    Helvetica family (built-in, print-safe)
  • Spacing:  4 / 6 / 8 / 10 / 12 / 16 / 20 / 24 / 32 pt rhythm
"""
from __future__ import annotations

import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

try:
    from .services import InvoiceService
except ImportError:
    from controllers.services import InvoiceService  # type: ignore[import]

try:
    from ..text_normalization import normalize_umlauts
except ImportError:
    from text_normalization import normalize_umlauts  # type: ignore[import]
ACCENT        = colors.HexColor("#4A7C6F")   # deep sage-teal
ACCENT_LIGHT  = colors.HexColor("#EAF2F0")   # very light teal tint
ACCENT_MID    = colors.HexColor("#D0E6E2")   # soft teal for totals box

CARD_BG       = colors.HexColor("#F5F4F1")   # warm beige card
DIVIDER       = colors.HexColor("#E8E6E1")   # warm gray separator

INK_DARK      = colors.HexColor("#2C2C2C")   # primary text
INK_MID       = colors.HexColor("#5C5C5C")   # secondary text
INK_SOFT      = colors.HexColor("#9A9A9A")   # labels / captions
WHITE         = colors.white

_STATUS_FG: dict = {
    "open":      colors.HexColor("#92400E"),
    "paid":      colors.HexColor("#065F46"),
    "cancelled": colors.HexColor("#991B1B"),
}
_STATUS_BG: dict = {
    "open":      colors.HexColor("#FEF3C7"),
    "paid":      colors.HexColor("#D1FAE5"),
    "cancelled": colors.HexColor("#FEE2E2"),
}

# Page geometry
PAGE_W, PAGE_H = A4
MARGIN         = 22 * mm
MARGIN_V       = 20 * mm
CONTENT_W      = PAGE_W - 2 * MARGIN

# Spacing ladder (points)
S4, S6, S8, S10, S12, S16, S20, S24, S32 = 4, 6, 8, 10, 12, 16, 20, 24, 32

CLINIC_NAME   = "Zahnarzt Praxis"
CLINIC_DOCTOR = "Dr. med. dent. El-Mohtaseb Aiman"
CLINIC_STREET = "Kronenstrasse 7"
CLINIC_CITY   = "9243 Jonschwil"
def _ps(name: str, font: str = "Helvetica", size: float = 9,
        color=None, align: int = TA_LEFT, leading: float = 0) -> ParagraphStyle:
    return ParagraphStyle(
        name,
        fontName=font,
        fontSize=size,
        textColor=color or INK_MID,
        alignment=align,
        leading=leading or round(size * 1.55),
    )


ST: dict = {
    "clinic_name":   _ps("clinic_name",   "Helvetica-Bold",  10,   ACCENT,   leading=14),
    "clinic_doctor": _ps("clinic_doctor", "Helvetica-Bold",   8.5, INK_DARK, leading=12),
    "clinic_line":   _ps("clinic_line",   "Helvetica",         8,   INK_SOFT, leading=12),

    "addr_name":     _ps("addr_name",     "Helvetica",       12,   INK_DARK, TA_LEFT,  leading=16),
    "addr_line":     _ps("addr_line",     "Helvetica",       12,   INK_MID,  TA_LEFT,  leading=16),
    "addr_name_r":   _ps("addr_name_r",   "Helvetica",       12,   INK_DARK, TA_RIGHT, leading=16),
    "addr_line_r":   _ps("addr_line_r",   "Helvetica",       12,   INK_MID,  TA_RIGHT, leading=16),

    "inv_title":     _ps("inv_title",     "Helvetica-Bold",  26,   INK_DARK, leading=30),
    "inv_number":    _ps("inv_number",    "Helvetica-Bold",  11,   ACCENT,   TA_RIGHT, leading=15),

    "meta_label":    _ps("meta_label",    "Helvetica",        7,   INK_SOFT, leading=10),
    "meta_value":    _ps("meta_value",    "Helvetica-Bold",   9.5, INK_DARK, leading=13),

    "card_label":    _ps("card_label",    "Helvetica",        6.5, INK_SOFT, leading=10),
    "card_value":    _ps("card_value",    "Helvetica-Bold",   9.5, INK_DARK, leading=13),
    "card_name":     _ps("card_name",     "Helvetica",       12,   INK_DARK, leading=16),

    "sec_heading":   _ps("sec_heading",   "Helvetica-Bold",   7.5, ACCENT,   leading=11),

    "th":            _ps("th",            "Helvetica-Bold",   8,   WHITE,    TA_LEFT,  leading=11),
    "th_r":          _ps("th_r",          "Helvetica-Bold",   8,   WHITE,    TA_RIGHT, leading=11),
    "td":            _ps("td",            "Helvetica",        9,   INK_DARK, TA_LEFT,  leading=13),
    "td_r":          _ps("td_r",          "Helvetica",        9,   INK_DARK, TA_RIGHT, leading=13),
    "td_empty":      _ps("td_empty",      "Helvetica-Oblique",9,   INK_SOFT, TA_LEFT,  leading=13),
    "tot_label":     _ps("tot_label",     "Helvetica-Bold",  10,   ACCENT,   TA_RIGHT, leading=14),
    "tot_value":     _ps("tot_value",     "Helvetica-Bold",  15,   ACCENT,   TA_RIGHT, leading=19),

    "notice_bold":   _ps("notice_bold",   "Helvetica-Bold",  10,   ACCENT,   leading=15),
    "notice_text":   _ps("notice_text",   "Helvetica",        9,   INK_MID,  leading=14),
    "footer_text":   _ps("footer_text",   "Helvetica",        7,   INK_SOFT, TA_CENTER, leading=10),
}
class _Badge(Flowable):
    """Pill-shaped status badge."""
    _HPAD = 10
    _HT   = 16
    _FS   = 7.0

    def __init__(self, status: str) -> None:
        super().__init__()
        self.label  = status.upper()
        self.fg     = _STATUS_FG.get(status, INK_SOFT)
        self.bg     = _STATUS_BG.get(status, CARD_BG)
        self._bw    = len(self.label) * 5.6 + self._HPAD * 2
        self.width  = self._bw
        self.height = self._HT

    def draw(self) -> None:
        c = self.canv
        c.saveState()
        r = self._HT / 2
        c.setFillColor(self.bg)
        c.setStrokeColor(self.fg)
        c.setLineWidth(0.6)
        c.roundRect(0, 0, self._bw, self._HT, r, stroke=1, fill=1)
        c.setFont("Helvetica-Bold", self._FS)
        c.setFillColor(self.fg)
        c.drawCentredString(self._bw / 2, (self._HT - self._FS) / 2 + 0.5, self.label)
        c.restoreState()
def _vcol(*items, w: float, row_pad_b: int = 2) -> Table:
    tbl = Table([[it] for it in items], colWidths=[w])
    tbl.setStyle(TableStyle([
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), row_pad_b),
    ]))
    return tbl


def _P(text: str, style_key: str) -> Paragraph:
    return Paragraph(normalize_umlauts(text), ST[style_key])


def _addr_lines(patient) -> list[str]:
    """Street + PLZ/city lines only – gender is handled separately."""
    lines = []
    if patient.street:
        lines.append(patient.street.strip())
    plz_city = " ".join(filter(None, [
        (patient.plz  or "").strip(),
        (patient.city or "").strip(),
    ]))
    if plz_city:
        lines.append(plz_city)
    return lines


def _date_chip(label: str, value: str) -> Table:
    """Small label + bold value stack used for dates."""
    tbl = Table(
        [[_P(label, "meta_label")],
         [_P(value, "meta_value")]],
        colWidths=[None],
    )
    tbl.setStyle(TableStyle([
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return tbl
def _build_header(inv) -> list:
    """
    Layout:
      1. RECHNUNG title + Nr.  (above the accent rule)
      2. Bold 3pt accent rule
      3. Two columns: LEFT clinic identity · RIGHT patient postal address
      4. Thin divider
    """
    lw = CONTENT_W * 0.48
    rw = CONTENT_W * 0.52

    rechnung_row = Table(
        [[_P("RECHNUNG", "inv_title"), _P(f"Nr. {inv.id:04d}", "inv_number")]],
        colWidths=[CONTENT_W * 0.70, CONTENT_W * 0.30],
    )
    rechnung_row.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "BOTTOM"),
        ("ALIGN",         (1, 0), (1, 0),   "RIGHT"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), S6),
    ]))

    clinic_col = _vcol(
        _P(CLINIC_NAME,   "clinic_name"),
        _P(CLINIC_DOCTOR, "clinic_doctor"),
        Spacer(1, S4),
        _P(CLINIC_STREET, "clinic_line"),
        _P(CLINIC_CITY,   "clinic_line"),
        w=lw, row_pad_b=1,
    )

    patient    = inv.patient
    pat_name   = f"{patient.first_name} {patient.last_name}" if patient else "\u2014"
    addr_lines = _addr_lines(patient) if patient else []

    right_items: list = []
    if patient and patient.gender:
        right_items.append(_P(patient.gender.strip(), "addr_name"))
    right_items.append(_P(pat_name, "addr_name"))
    for line in addr_lines:
        right_items.append(_P(line, "addr_line"))
    right_col = _vcol(*right_items, w=rw, row_pad_b=2)

    body_tbl = Table([[clinic_col, right_col]], colWidths=[lw, rw])
    body_tbl.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("ALIGN",         (1, 0), (1, 0),   "LEFT"),
        ("LEFTPADDING",   (0, 0), (0, 0),   0),
        ("LEFTPADDING",   (1, 0), (1, 0),   60),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    return [
        rechnung_row,
        HRFlowable(width="100%", thickness=3, color=ACCENT,
                   spaceBefore=0, spaceAfter=S16),
        body_tbl,
        Spacer(1, S16),
        HRFlowable(width="100%", thickness=0.5, color=DIVIDER,
                   spaceBefore=0, spaceAfter=0),
    ]


def _build_patient_and_dates(inv) -> list:
    """
    Two-column card row below header:
      LEFT  · Patient card  (name, address, Geburtsdatum, Versicherungsnr.)
      RIGHT · Date chips    (Rechnungsdatum, Fälligkeitsdatum)
    """
    patient = inv.patient
    patientenname       = f"{patient.first_name} {patient.last_name}" if patient else "\u2014"
    geburtsdatum        = (patient.date_of_birth    or "\u2014") if patient else "\u2014"
    versicherungsnummer = (patient.insurance_number or "\u2014") if patient else "\u2014"
    adresszeilen        = _addr_lines(patient) if patient else []

    lw  = CONTENT_W * 0.58
    rw  = CONTENT_W * 0.42
    pad = S16
    gap = S10

    inner_lw = lw - pad * 2
    pat_items: list = [_P("PATIENT", "card_label")]
    if patient and patient.gender:
        pat_items.append(_P(patient.gender.strip(), "card_name"))
    pat_items += [
        _P(patientenname, "card_name"),
        Spacer(1, S4),
        _P("GEBURTSDATUM",      "card_label"),
        _P(geburtsdatum,        "card_value"),
        Spacer(1, S4),
        _P("VERSICHERUNGSNR.",  "card_label"),
        _P(versicherungsnummer, "card_value"),
    ]
    patient_inner = _vcol(*pat_items, w=inner_lw, row_pad_b=1)
    patient_card  = Table([[patient_inner]], colWidths=[lw])
    patient_card.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), CARD_BG),
        ("LEFTPADDING",   (0, 0), (-1, -1), pad),
        ("RIGHTPADDING",  (0, 0), (-1, -1), pad),
        ("TOPPADDING",    (0, 0), (-1, -1), S12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), S12),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))

    inner_rw   = rw - pad * 2
    date_inner = _vcol(
        _date_chip("Rechnungsdatum",    inv.invoice_date or "\u2014"),
        Spacer(1, S10),
        _date_chip("F\u00e4lligkeitsdatum", inv.due_date     or "\u2014"),
        w=inner_rw, row_pad_b=0,
    )
    date_card = Table([[date_inner]], colWidths=[rw])
    date_card.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), ACCENT_LIGHT),
        ("LEFTPADDING",   (0, 0), (-1, -1), pad),
        ("RIGHTPADDING",  (0, 0), (-1, -1), pad),
        ("TOPPADDING",    (0, 0), (-1, -1), S12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), S12),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))

    outer = Table([[patient_card, Spacer(gap, 1), date_card]],
                  colWidths=[lw, gap, rw - gap])
    outer.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    return [Spacer(1, S16), outer]


def _build_items_table(inv) -> list:
    """
    Soft modern line-items table with warm alternating rows and accent total box.
    """
    active = [i for i in inv.items if i.is_active]
    cw = [CONTENT_W * p for p in (0.50, 0.10, 0.20, 0.20)]

    rows: list = [[
        _P("Leistungsbeschreibung", "th"),
        _P("Anz.",        "th_r"),
        _P("CHF/Einheit", "th_r"),
        _P("Betrag CHF",  "th_r"),
    ]]

    if not active:
        rows.append([_P("Keine Positionen auf dieser Rechnung.", "td_empty"), "", "", ""])
    else:
        for item in active:
            rows.append([
                _P(item.description,                           "td"),
                _P(f"{item.quantity:g}",                       "td_r"),
                _P(f"{item.unit_price:,.2f}",                  "td_r"),
                _P(f"{item.quantity * item.unit_price:,.2f}",  "td_r"),
            ])

    body_n = len(rows)

    rows.append([
        "", "",
        _P("TOTAL CHF",         "tot_label"),
        _P(f"{inv.total:,.2f}", "tot_value"),
    ])

    alt_styles = [
        ("BACKGROUND", (0, i), (-1, i), WHITE if i % 2 == 1 else CARD_BG)
        for i in range(1, body_n)
    ]

    tbl = Table(rows, colWidths=cw, repeatRows=1)
    tbl.setStyle(TableStyle([
        # Header
        ("BACKGROUND",    (0, 0), (-1, 0),             ACCENT),
        ("TOPPADDING",    (0, 0), (-1, 0),             S10),
        ("BOTTOMPADDING", (0, 0), (-1, 0),             S10),
        ("LEFTPADDING",   (0, 0), (-1, 0),             S12),
        ("RIGHTPADDING",  (0, 0), (-1, 0),             S12),
        # Body
        *alt_styles,
        ("TOPPADDING",    (0, 1), (-1, body_n - 1),    S10),
        ("BOTTOMPADDING", (0, 1), (-1, body_n - 1),    S10),
        ("LEFTPADDING",   (0, 1), (-1, body_n - 1),    S12),
        ("RIGHTPADDING",  (0, 1), (-1, body_n - 1),    S12),
        ("LINEBELOW",     (0, 1), (-1, body_n - 1),    0.4, DIVIDER),
        # Total
        ("BACKGROUND",    (0, body_n), (-1, body_n),   ACCENT_MID),
        ("LINEABOVE",     (0, body_n), (-1, body_n),   1.5, ACCENT),
        ("TOPPADDING",    (0, body_n), (-1, body_n),   S12),
        ("BOTTOMPADDING", (0, body_n), (-1, body_n),   S12),
        ("LEFTPADDING",   (0, body_n), (-1, body_n),   S12),
        ("RIGHTPADDING",  (0, body_n), (-1, body_n),   S12),
        # Global
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))

    return [
        Spacer(1, S20),
        _P("LEISTUNGEN", "sec_heading"),
        Spacer(1, S6),
        tbl,
    ]


def _build_footer() -> list:
    """Friendly patient-facing payment notice + slim footer stamp."""
    now = datetime.now(timezone.utc).strftime("%d.%m.%Y  %H:%M  UTC")

    notice_inner = _vcol(
        _P("\u2665  Vielen Dank f\u00fcr Ihr Vertrauen!", "notice_bold"),
        Spacer(1, S4),
        _P(
            "Bitte begleichen Sie den offenen Betrag bis zum angegebenen "
            "F\u00e4lligkeitsdatum. Bei Fragen stehen wir Ihnen jederzeit "
            "gerne zur Verf\u00fcgung.",
            "notice_text",
        ),
        w=CONTENT_W - S16 * 2,
        row_pad_b=0,
    )

    notice_card = Table([[notice_inner]], colWidths=[CONTENT_W])
    notice_card.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), ACCENT_LIGHT),
        ("LINEBEFORE",    (0, 0), (0, 0),   3, ACCENT),
        ("LEFTPADDING",   (0, 0), (-1, -1), S16),
        ("RIGHTPADDING",  (0, 0), (-1, -1), S16),
        ("TOPPADDING",    (0, 0), (-1, -1), S16),
        ("BOTTOMPADDING", (0, 0), (-1, -1), S16),
    ]))

    return [
        Spacer(1, S24),
        notice_card,
        Spacer(1, S20),
        HRFlowable(width="100%", thickness=0.5, color=DIVIDER,
                   spaceBefore=0, spaceAfter=S8),
        _P(
            f"{CLINIC_NAME}  \u00b7  {CLINIC_DOCTOR}  \u00b7  "
            f"{CLINIC_STREET}, {CLINIC_CITY}  \u00b7  Erstellt am {now}",
            "footer_text",
        ),
    ]
def generate_invoice_pdf(invoice_id: int) -> bytes:
    """
    Build and return a complete A4 invoice PDF as raw bytes.
    Raises ValueError if the invoice does not exist.
    """
    inv = InvoiceService.get_by_id(invoice_id)
    if inv is None:
        raise ValueError(f"Invoice #{invoice_id} not found.")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN_V,
        bottomMargin=MARGIN_V,
        title=f"Rechnung Nr. {inv.id:04d}",
        author=f"{CLINIC_NAME} \u2013 {CLINIC_DOCTOR}",
    )

    story: list = []
    story += _build_header(inv)
    story += _build_patient_and_dates(inv)
    story += _build_items_table(inv)
    story += _build_footer()

    doc.build(story)
    return buf.getvalue()
