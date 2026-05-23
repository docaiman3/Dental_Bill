"""
conftest.py – shared pytest fixtures.

The `billing_db` fixture spins up a fresh in-memory SQLite DB for every
test that requests it, and patches both `models.get_session` and the
imported reference inside `controllers.dao` so that DAOs transparently
use the isolated test database instead of the real billing.db file.
"""
import sys
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

_root = Path(__file__).parent.parent   # Bills/
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))


@pytest.fixture
def billing_db(monkeypatch):
    """
    In-memory SQLite engine for billing tables.

    Patches both `models.get_session` and `controllers.dao.get_session`
    so every DAO call goes to the test DB, not billing.db.
    Rolls back / drops after each test automatically.
    """
    import domain.models as models
    import controllers.dao as dao_module

    test_engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(test_engine)

    def _session():
        return Session(test_engine)

    monkeypatch.setattr(models, "engine", test_engine)
    monkeypatch.setattr(models, "get_session", _session)
    monkeypatch.setattr(dao_module, "get_session", _session)

    yield test_engine

    SQLModel.metadata.drop_all(test_engine)
    test_engine.dispose()


