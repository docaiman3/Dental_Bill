"""
Persistence Layer – SQLModel ORM models (maps to SQLite tables).
No business logic here; only data structure and DB structure management.
"""
from datetime import date, datetime, timezone
from pathlib import Path
from typing import List, Optional
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine  # type: ignore[import-not-found]

# Always resolve DB path relative to THIS file – works regardless of CWD or sys.path
# domain/models.py → parent = domain/ → parent = Bills/ → db/billing.db
BILLING_DB_PATH = Path(__file__).resolve().parent.parent / "db" / "billing.db"
BILLING_DB_URL  = f"sqlite:///{BILLING_DB_PATH}"

engine = create_engine(BILLING_DB_URL, echo=False)



class Patient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    gender: Optional[str] = None                 # "Herr" | "Frau" | "Divers"
    first_name: str
    last_name: str
    date_of_birth: Optional[str] = None          # ISO string "YYYY-MM-DD"
    insurance_number: Optional[str] = None
    address: Optional[str] = None                # legacy – kept for DB compat
    street: Optional[str] = None                 # e.g. "Bahnhofstrasse 5"
    plz: Optional[str] = None                    # Swiss postal code, e.g. "8001"
    city: Optional[str] = None                   # e.g. "Zürich"

    invoices: List["Invoice"] = Relationship(back_populates="patient")


class Invoice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    invoice_date: str = Field(default_factory=lambda: date.today().isoformat())
    due_date: Optional[str] = None
    status: str = "open"                          # open | paid | cancelled

    patient_id: Optional[int] = Field(default=None, foreign_key="patient.id")
    patient: Optional[Patient] = Relationship(back_populates="invoices")

    items: List["InvoiceItem"] = Relationship(back_populates="invoice")
    changes: List["InvoiceChangeEntry"] = Relationship(back_populates="invoice")

    @property
    def total(self) -> float:
        return sum(i.quantity * i.unit_price for i in self.items if i.is_active)


class InvoiceItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    description: str
    quantity: float = 1.0
    unit_price: float = 0.0
    is_active: bool = True                        # False = soft-deleted

    invoice_id: Optional[int] = Field(default=None, foreign_key="invoice.id")
    invoice: Optional["Invoice"] = Relationship(back_populates="items")


class InvoiceChangeEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    invoice_id: Optional[int] = Field(default=None, foreign_key="invoice.id")
    changed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    change_type: str                              # status_change | item_added | item_removed
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    item_description: Optional[str] = None
    item_quantity: Optional[float] = None
    item_unit_price: Optional[float] = None

    invoice: Optional["Invoice"] = Relationship(back_populates="changes")



def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    _run_migrations()


def _run_migrations():
    """Apply additive schema changes that create_all won't handle (ALTER TABLE)."""
    import sqlite3
    conn = sqlite3.connect(str(BILLING_DB_PATH))
    cur = conn.cursor()

    # invoiceitem.is_active
    cols = [row[1] for row in cur.execute("PRAGMA table_info(invoiceitem)").fetchall()]
    if "is_active" not in cols:
        cur.execute(
            "ALTER TABLE invoiceitem ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1"
        )
        conn.commit()

    # patient.address (legacy)
    p_cols = [row[1] for row in cur.execute("PRAGMA table_info(patient)").fetchall()]
    if "address" not in p_cols:
        cur.execute("ALTER TABLE patient ADD COLUMN address TEXT")
        conn.commit()
    # patient.street / plz / city
    for col in ("street", "plz", "city"):
        if col not in p_cols:
            cur.execute(f"ALTER TABLE patient ADD COLUMN {col} TEXT")
    # patient.gender
    if "gender" not in p_cols:
        cur.execute("ALTER TABLE patient ADD COLUMN gender TEXT")
    conn.commit()

    conn.close()


def get_session() -> Session:
    return Session(engine)
