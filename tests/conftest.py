import os
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker

from palantir_tw.db import Base, make_engine
from palantir_tw.ingest.cec import import_cec_election

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "cec_111"


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("PALANTIR_TW_DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    engine = make_engine(f"sqlite:///{tmp_path}/test.db")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def seeded_session(db_session):
    stats = import_cec_election(
        db_session,
        FIXTURE_ROOT,
        "2022-111年地方公職人員選舉",
        "111年地方公職人員選舉",
        date(2022, 11, 26),
    )
    db_session.commit()
    db_session.expire_all()
    return db_session, stats
