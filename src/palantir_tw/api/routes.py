from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Assertion, Candidacy, Entity

router = APIRouter(prefix="/api")


def _entity_out(e: Entity) -> dict:
    return {
        "id": e.id,
        "type": e.type,
        "name": e.name,
        "aliases": e.aliases,
        "external_id": e.external_id,
        "props": e.props,
    }


@router.get("/entities")
def list_entities(
    type: str | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    stmt = select(Entity)
    if type:
        stmt = stmt.where(Entity.type == type)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Entity.name.like(like), Entity.external_id.like(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(Entity.id).offset(offset).limit(limit)).all()
    return {"total": total, "items": [_entity_out(e) for e in rows]}


@router.get("/entities/{entity_id}")
def get_entity(entity_id: int, db: Session = Depends(get_db)):
    e = db.get(Entity, entity_id)
    if e is None:
        raise HTTPException(404, "entity not found")
    out = _entity_out(e)
    out["candidacies"] = [
        _candidacy_out(c)
        for c in db.scalars(select(Candidacy).where(Candidacy.person_id == entity_id)).all()
    ]
    out["assertions"] = [
        _assertion_out(a)
        for a in db.scalars(
            select(Assertion).where(
                or_(Assertion.subject_id == entity_id, Assertion.object_id == entity_id)
            )
        ).all()
    ]
    return out


@router.get("/elections")
def list_elections(db: Session = Depends(get_db)):
    rows = db.scalars(select(Entity).where(Entity.type == "election").order_by(Entity.id)).all()
    return {"items": [_entity_out(e) for e in rows]}


@router.get("/elections/{election_id}/results")
def election_results(election_id: int, db: Session = Depends(get_db)):
    election = db.get(Entity, election_id)
    if election is None or election.type != "election":
        raise HTTPException(404, "election not found")
    rows = db.scalars(select(Candidacy).where(Candidacy.election_id == election_id)).all()
    by_district: dict[int, dict] = {}
    for c in rows:
        d = by_district.setdefault(
            c.district_id, {"district": _entity_out(c.district), "candidates": []}
        )
        d["candidates"].append(_candidacy_out(c))
    for d in by_district.values():
        d["candidates"].sort(key=lambda x: -(x["votes"] or 0))
    return {"election": _entity_out(election), "districts": list(by_district.values())}


@router.get("/parties")
def list_parties(db: Session = Depends(get_db)):
    rows = db.scalars(select(Entity).where(Entity.type == "party").order_by(Entity.name)).all()
    return {"items": [_entity_out(e) for e in rows]}


@router.get("/districts/{district_id}/candidacies")
def district_candidacies(district_id: int, db: Session = Depends(get_db)):
    d = db.get(Entity, district_id)
    if d is None or d.type != "district":
        raise HTTPException(404, "district not found")
    rows = db.scalars(select(Candidacy).where(Candidacy.district_id == district_id)).all()
    return {"district": _entity_out(d), "candidacies": [_candidacy_out(c) for c in rows]}


def _candidacy_out(c: Candidacy) -> dict:
    return {
        "id": c.id,
        "person": _entity_out(c.person),
        "election_id": c.election_id,
        "district_id": c.district_id,
        "party": _entity_out(c.party) if c.party else None,
        "office": c.office,
        "ballot_no": c.ballot_no,
        "votes": c.votes,
        "vote_share": c.vote_share,
        "elected": c.elected,
        "incumbent": c.incumbent,
        "sex": c.sex,
        "education": c.education,
    }


def _assertion_out(a: Assertion) -> dict:
    return {
        "id": a.id,
        "subject": _entity_out(a.subject),
        "predicate": a.predicate,
        "object": _entity_out(a.object) if a.object else a.object_text,
        "grade": a.grade,
        "status": a.status,
        "document_id": a.document_id,
        "valid_from": a.valid_from.isoformat() if a.valid_from else None,
        "valid_to": a.valid_to.isoformat() if a.valid_to else None,
    }
