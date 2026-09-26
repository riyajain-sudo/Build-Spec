import pytest
from fastapi.testclient import TestClient

from app.db.models import DB_PATH
from app.main import app
from app.services.repurposing import _stems, load_index, match_disease, tanimoto_to

pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="run app.db.seed_data first")
client = TestClient(app)


def test_disease_name_normalisation():
    assert _stems("Breast Cancer") == _stems("breast neoplasms")
    assert _stems("high blood pressure") == _stems("hypertension")


def test_match_and_suggestions():
    idx = load_index()
    assert match_disease("chronic myeloid leukemia", idx)[0] == ["Leukemia, Myelogenous, Chronic, BCR-ABL Positive"]
    assert match_disease("xyzzy", idx) == ([], [])
    assert "Leukemia" in match_disease("leukimia", idx)[1]


def test_tanimoto_of_drug_with_itself_is_one():
    idx = load_index()
    rows = idx.row["CHEMBL941"]  # imatinib
    import numpy as np
    assert tanimoto_to(idx, np.array([rows]), np.array([rows]))[0, 0] == pytest.approx(1.0)


def test_cml_repurposing_is_grounded_in_shared_target():
    r = client.get("/repurpose/chronic myeloid leukemia", params={"top_n": 5})
    assert r.status_code == 200
    body = r.json()
    assert "IMATINIB" in body["known_treatments"]
    known = set(body["known_treatments"])
    assert 0 < len(body["candidates"]) <= 5
    scores = [c["score"] for c in body["candidates"]]
    assert scores == sorted(scores, reverse=True)
    for c in body["candidates"]:
        assert c["drug"] not in known and c["reasons"] and 0 <= c["score"] <= 1
    top = body["candidates"][0]
    assert top["shared_targets"] and "Shares target" in top["reasons"][0]
    assert any("ABL1" in t["name"] for t in body["known_treatment_targets"])


def test_reasons_cite_tanimoto():
    body = client.get("/repurpose/type 2 diabetes").json()
    assert any("Tanimoto" in reason for c in body["candidates"] for reason in c["reasons"])


def test_unknown_disease_404_with_suggestion():
    r = client.get("/repurpose/leukimia")
    assert r.status_code == 404 and "Leukemia" in r.json()["detail"]
    assert client.get("/repurpose/xyzzy").status_code == 404


def test_top_n_validation():
    assert client.get("/repurpose/hypertension", params={"top_n": 0}).status_code == 422
    assert client.get("/repurpose/hypertension", params={"top_n": 500}).status_code == 422


def test_disease_search():
    hits = client.get("/diseases", params={"q": "leuk"}).json()
    assert hits and all("leuk" in h["name"].lower() for h in hits)
    assert hits == sorted(hits, key=lambda h: (not h["name"].lower().startswith("leuk"), -h["n_drugs"], h["name"]))
    top = client.get("/diseases").json()
    assert len(top) == 15 and top[0]["n_drugs"] >= top[-1]["n_drugs"]


def test_similar_known_drug_has_structure():
    c = client.get("/repurpose/type 2 diabetes").json()["candidates"][0]
    assert c["most_similar_known_drug"]["smiles"]
