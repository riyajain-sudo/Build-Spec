from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_svg():
    r = client.get("/molecule/svg", params={"smiles": "CC(=O)Oc1ccccc1C(=O)O"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/svg+xml")
    assert "<svg" in r.text


def test_svg_invalid_smiles():
    assert client.get("/molecule/svg", params={"smiles": "xyz"}).status_code == 422
