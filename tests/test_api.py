from fastapi.testclient import TestClient

from palantir_tw.app import create_app
from palantir_tw.db import get_db


def _client(session):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: session
    return TestClient(app)


def test_elections_list(seeded_session):
    session, _ = seeded_session
    client = _client(session)
    resp = client.get("/api/elections")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "111年地方公職人員選舉"


def test_election_results_sorted(seeded_session):
    session, _ = seeded_session
    client = _client(session)
    election_id = client.get("/api/elections").json()["items"][0]["id"]
    resp = client.get(f"/api/elections/{election_id}/results")
    assert resp.status_code == 200
    districts = {d["district"]["name"]: d["candidates"] for d in resp.json()["districts"]}
    taipei = districts["臺北市"]
    assert taipei[0]["person"]["name"] == "陳時中"  # 票数降序
    assert taipei[0]["votes"] == 583689
    elected = [c for c in taipei if c["elected"]]
    assert [c["person"]["name"] for c in elected] == ["蔣萬安"]


def test_entity_search_and_detail(seeded_session):
    session, _ = seeded_session
    client = _client(session)
    resp = client.get("/api/entities", params={"q": "蔣萬安"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    detail = client.get(f"/api/entities/{items[0]['id']}").json()
    assert detail["candidacies"][0]["elected"] is True


def test_html_pages_render(seeded_session):
    session, _ = seeded_session
    client = _client(session)
    assert client.get("/").status_code == 200
    election_id = client.get("/api/elections").json()["items"][0]["id"]
    resp = client.get(f"/elections/{election_id}")
    assert resp.status_code == 200
    assert "蔣萬安" in resp.text
