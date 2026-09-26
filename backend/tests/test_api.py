from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
ASPIRIN = "CC(=O)Oc1ccccc1C(=O)O"
ERLOTINIB = "COCCOc1cc2ncnc(Nc3cccc(C#C)c3)c2cc1OCCOC"
BISPHENOL_A = "CC(C)(c1ccc(O)cc1)c1ccc(O)cc1"


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_bioactivity():
    r = client.post("/predict/bioactivity", json={"smiles": ERLOTINIB})
    assert r.status_code == 200
    body = r.json()
    assert len(body["predictions"]) == 6
    top = body["predictions"][0]
    assert top["endpoint"] == "EGFR" and top["prediction"] == "active"
    assert 0.5 <= top["confidence"] <= 1
    assert len(body["explanations"]) == 3 and body["explanations"][0]["contributions"]


def test_toxicity():
    r = client.post("/predict/toxicity", json={"smiles": BISPHENOL_A, "explain_top_n": 1})
    assert r.status_code == 200
    body = r.json()
    assert "NR-ER" in body["flagged_endpoints"] and len(body["explanations"]) == 1


def test_druglikeness():
    body = client.post("/predict/druglikeness", json={"smiles": ASPIRIN}).json()
    assert body["drug_like"] is True and 0 <= body["qed"] <= 1


def test_invalid_smiles_is_422():
    for path in ("bioactivity", "toxicity", "druglikeness"):
        r = client.post(f"/predict/{path}", json={"smiles": "not_a_smiles"})
        assert r.status_code == 422 and "Invalid SMILES" in r.json()["detail"]


def test_validation_errors():
    assert client.post("/predict/toxicity", json={}).status_code == 422
    assert client.post("/predict/toxicity", json={"smiles": ""}).status_code == 422
