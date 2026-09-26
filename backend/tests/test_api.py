from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
ASPIRIN = "CC(=O)Oc1ccccc1C(=O)O"
ERLOTINIB = "COCCOc1cc2ncnc(Nc3cccc(C#C)c3)c2cc1OCCOC"
BISPHENOL_A = "CC(C)(c1ccc(O)cc1)c1ccc(O)cc1"


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_bioactivity():
    r = client.post("/predict/bioactivity", json={"smiles": ERLOTINIB, "include_llm_explanation": False})
    assert r.status_code == 200
    body = r.json()
    assert len(body["predictions"]) == 6
    top = body["predictions"][0]
    assert top["endpoint"] == "EGFR" and top["prediction"] == "active"
    assert 0.5 <= top["confidence"] <= 1
    assert len(body["explanations"]) == 3 and body["explanations"][0]["contributions"]


def test_toxicity():
    r = client.post("/predict/toxicity", json={"smiles": BISPHENOL_A, "explain_top_n": 1, "include_llm_explanation": False})
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


def test_llm_explanation_is_grounded_and_included(monkeypatch):
    seen = {}

    def fake_generate(ctx):
        seen["ctx"] = ctx
        return {"text": "stub explanation", "source": "gemini", "model": "stub"}

    monkeypatch.setattr("app.routers.predict.generate_explanation", fake_generate)
    body = client.post("/predict/bioactivity", json={"smiles": ERLOTINIB, "explain_top_n": 0}).json()
    assert body["plain_english_explanation"]["text"] == "stub explanation"
    ctx = seen["ctx"]  # the LLM is given only structured model output
    assert ctx["endpoint"] == "EGFR" and ctx["model_test_auc"] is not None
    assert ctx["top_shap_features"] and set(ctx["top_shap_features"][0]) == {"feature", "effect", "shap_log_odds"}


def test_llm_can_be_disabled():
    body = client.post("/predict/toxicity", json={"smiles": ASPIRIN, "include_llm_explanation": False}).json()
    assert "plain_english_explanation" not in body


def test_falls_back_to_template_when_llm_fails(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    body = client.post("/predict/toxicity", json={"smiles": BISPHENOL_A}).json()
    expl = body["plain_english_explanation"]
    assert expl["source"] == "template" and "computational prediction" in expl["text"]
