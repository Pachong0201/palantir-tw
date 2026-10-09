from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .api.routes import router as api_router
from .db import engine, get_db, init_db
from .models import Candidacy, Entity

PKG = Path(__file__).parent
_jinja = Environment(
    loader=FileSystemLoader(PKG / "templates"),
    autoescape=select_autoescape(["html"]),
)


def render(name: str, status_code: int = 200, **ctx) -> HTMLResponse:
    return HTMLResponse(_jinja.get_template(name).render(**ctx), status_code=status_code)


def create_app() -> FastAPI:
    app = FastAPI(title="palantir-tw · 台湾开源情报平台")
    app.include_router(api_router)
    app.mount("/static", StaticFiles(directory=PKG / "static"), name="static")

    @app.on_event("startup")
    def _startup() -> None:
        init_db(engine)

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request, db: Session = Depends(get_db)):
        counts = {
            t: db.scalar(select(func.count(Entity.id)).where(Entity.type == t))
            for t in ("person", "party", "district", "election", "document")
        }
        return render("index.html", request=request, counts=counts)

    @app.get("/entities/{entity_id}", response_class=HTMLResponse)
    def entity_page(entity_id: int, request: Request, db: Session = Depends(get_db)):
        e = db.get(Entity, entity_id)
        if e is None:
            return render("404.html", status_code=404, request=request, id=entity_id)
        candidacies = db.scalars(
            select(Candidacy).where(Candidacy.person_id == entity_id)
        ).all()
        return render("entity.html", request=request, e=e, candidacies=candidacies)

    @app.get("/elections/{election_id}", response_class=HTMLResponse)
    def election_page(election_id: int, request: Request, db: Session = Depends(get_db)):
        e = db.get(Entity, election_id)
        if e is None:
            return render("404.html", status_code=404, request=request, id=election_id)
        rows = db.scalars(select(Candidacy).where(Candidacy.election_id == election_id)).all()
        by_district: dict[int, list[Candidacy]] = {}
        for c in rows:
            by_district.setdefault(c.district_id, []).append(c)
        districts = sorted(
            by_district.items(),
            key=lambda kv: kv[1][0].district.name if kv[1] else "",
        )
        return render("election.html", request=request, e=e, districts=districts)

    @app.get("/search", response_class=HTMLResponse)
    def search(request: Request, q: str = "", db: Session = Depends(get_db)):
        results = []
        if q:
            results = db.scalars(
                select(Entity).where(Entity.name.like(f"%{q}%")).limit(100)
            ).all()
        return render("search.html", request=request, q=q, results=results)

    return app


app = create_app()
