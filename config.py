"""
Central configuration – single source of truth for all database paths.

Both domain models compute their own paths via __file__ so they work in ANY
context (reload, subprocess, tests, scripts).  This file re-exports those
values for convenience if other scripts need them.
"""
from pathlib import Path

# Project root = the directory this file lives in (Bills/)
PROJECT_ROOT: Path = Path(__file__).resolve().parent
DB_DIR:       Path = PROJECT_ROOT / "db"

# Re-export canonical paths – always consistent with what the ORM engines use
from domain.models import BILLING_DB_PATH, BILLING_DB_URL          # noqa: E402
from domain.tariff_models import TARIFF_DB_PATH, TARIFF_DB_URL     # noqa: E402

__all__ = [
    "PROJECT_ROOT", "DB_DIR",
    "BILLING_DB_PATH", "BILLING_DB_URL",
    "TARIFF_DB_PATH",  "TARIFF_DB_URL",
]
