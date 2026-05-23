"""
Entry point – wires up the app and starts the NiceGUI server.

MVC layout
----------
Model      : models.py  /  tariff_models.py
Controller : controllers/  (services.py, dao.py)
View       : views/  (patients.py, invoices.py, shared.py)
DB         : db/  (billing.db, zahnarzttarif.db)
"""
import sys
from pathlib import Path

# Ensure project root is on sys.path so all layers can resolve each other
_here = Path(__file__).parent
_parent = _here.parent
for _p in (str(_here), str(_parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from nicegui import ui

from domain.models import create_db_and_tables
import views  # noqa: F401 – registers all @ui.page routes as a side-effect

create_db_and_tables()




def main():
    ui.run(title="Patient Billing", port=8790, reload=True)


if __name__ in {"__main__", "__mp_main__"}:
    main()

