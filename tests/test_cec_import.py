from datetime import date
from pathlib import Path

from sqlalchemy import func, select

from palantir_tw.ingest.cec import import_cec_election
from palantir_tw.models import Candidacy, Entity
from tests.conftest import FIXTURE_ROOT


def test_import_creates_ontology(seeded_session):
    session, stats = seeded_session
    assert stats.districts == 2
    assert stats.parties == 2  # KMT + DPP（999 無黨籍不建 party 实体）
    assert stats.persons == 6
    assert stats.candidacies == 6
    assert stats.elected == 2


def test_elected_flags_and_votes(seeded_session):
    session, _ = seeded_session
    elected = session.scalars(select(Candidacy).where(Candidacy.elected)).all()
    names = {c.person.name for c in elected}
    assert names == {"蔣萬安", "王忠銘"}
    wang = next(c for c in elected if c.person.name == "王忠銘")
    assert wang.votes == 4337
    assert wang.vote_share == 50.99
    assert wang.office == "縣市長"
    assert wang.party.name == "中國國民黨"


def test_party_and_district_entities(seeded_session):
    session, _ = seeded_session
    districts = session.scalars(select(Entity).where(Entity.type == "district")).all()
    assert {d.name for d in districts} == {"臺北市", "連江縣"}
    assert all(d.props["level"] == "county" for d in districts)


def test_simple_dir_import(db_session):
    from palantir_tw.ingest.cec import import_cec_simple_dir

    stats = import_cec_simple_dir(
        db_session,
        Path(__file__).parent / "fixtures" / "chiayi_rerun" / "2022年_嘉義市長重行選舉",
        "2022年嘉義市長重行選舉",
        date(2022, 12, 18),
        office="縣市長",
        district_name="嘉義市",
        district_external_id="cec:10-020",
    )
    db_session.commit()
    assert stats.candidacies == 3
    winner = db_session.scalar(select(Candidacy).where(Candidacy.elected))
    assert winner.person.name == "黃敏惠"
    assert winner.votes == 319 + 382 + 307
    assert winner.party.name == "中國國民黨"


def test_import_is_idempotent(seeded_session):
    session, _ = seeded_session
    stats2 = import_cec_election(
        session,
        FIXTURE_ROOT,
        "2022-111年地方公職人員選舉",
        "111年地方公職人員選舉",
        date(2022, 11, 26),
    )
    session.commit()
    assert stats2.candidacies == 0
    assert session.scalar(select(func.count(Candidacy.id))) == 6
