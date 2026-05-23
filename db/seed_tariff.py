"""
Seed zahnarzttarif.db from zahnarzttarif.json using SQLAlchemy.

Run once (or any time the JSON source changes):
    python db/seed_tariff.py

Existing tariff rows are deleted and re-inserted so the DB always
reflects the JSON exactly.  The `sections` table is left untouched.
"""

import json
import sys
from pathlib import Path

# Ensure project root (Bills/) is on sys.path
_root = Path(__file__).parent.parent   # Bills/
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from domain.tariff_models import Tariff, create_tariff_tables, get_tariff_session
from text_normalization import normalize_umlauts

_JSON_PATH = Path(__file__).parent / "zahnarzttarif.json"


def seed() -> None:
    # 1. Make sure the tables exist
    create_tariff_tables()

    # 2. Load source data
    data: list[dict] = json.loads(_JSON_PATH.read_text(encoding="utf-8"))
    print(f"  Loaded {len(data)} entries from {_JSON_PATH.name}")

    # 3. Replace tariff rows
    with get_tariff_session() as session:
        deleted = session.query(Tariff).delete()
        print(f"  Removed {deleted} old tariff rows")

        rows = [
            Tariff(
                ziffer=entry["ziffer"],
                uvmv_iv=entry.get("uvmv_iv"),
                pp_min=entry.get("pp_min"),
                pp_max=entry.get("pp_max"),
                pp_raw=entry.get("pp_raw") or None,
                leistung=normalize_umlauts(entry.get("leistung") or None),
            )
            for entry in data
        ]
        session.add_all(rows)
        session.commit()
        print(f"  Inserted {len(rows)} tariff rows")

    print(" zahnarzttarif.db seeded successfully.")


if __name__ == "__main__":
    seed()
