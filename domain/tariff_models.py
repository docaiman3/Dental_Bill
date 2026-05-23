"""
SQLAlchemy ORM models for the dental tariff catalogue (zahnarzttarif.db).
These are read-only reference data – never modified by the billing app.
"""

from pathlib import Path
from typing import Optional

from sqlalchemy import Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

# Always resolve DB path relative to THIS file – works regardless of CWD or sys.path
# domain/tariff_models.py → parent = domain/ → parent = Bills/ → db/zahnarzttarif.db
TARIFF_DB_PATH = Path(__file__).resolve().parent.parent / "db" / "zahnarzttarif.db"
TARIFF_DB_URL  = f"sqlite:///{TARIFF_DB_PATH}"

tariff_engine = create_engine(TARIFF_DB_URL, echo=False)


class TariffBase(DeclarativeBase):
    pass


class Tariff(TariffBase):
    """One line-item in the Swiss dental tariff (SSO/UVMV)."""

    __tablename__ = "tariff"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ziffer: Mapped[str] = mapped_column(String, nullable=False)
    uvmv_iv: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pp_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pp_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pp_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    leistung: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Tariff {self.ziffer} – {self.leistung!r}>"


class Section(TariffBase):
    """Top-level chapter grouping of tariff positions."""

    __tablename__ = "sections"

    prefix: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Section {self.prefix}: {self.name!r}>"


def create_tariff_tables() -> None:
    """Create tables if they don't exist yet (idempotent)."""
    TariffBase.metadata.create_all(tariff_engine)


def get_tariff_session() -> Session:
    return Session(tariff_engine)

