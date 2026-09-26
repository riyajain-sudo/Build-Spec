from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_svg():
    r = client.get("/molecule/svg", params={"smiles": "CC(=O)Oc1ccccc1C(=O)O"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/svg+xml")
    assert "<svg" in r.text


def test_svg_invalid_smiles():
    assert client.get("/molecule/svg", params={"smiles": "xyz"}).status_code == 422


IMATINIB = "Cc1ccc(NC(=O)c2ccc(CN3CCN(C)CC3)cc2)cc1Nc1nccc(-c2cccnc2)n1"


def test_info_names_an_approved_drug():
    body = client.get("/molecule/info", params={"smiles": IMATINIB}).json()
    assert body["name"] == "IMATINIB" and body["chembl_id"] == "CHEMBL941"
    assert body["formula"] == "C29H31N7O" and body["approved_for"]


def test_info_matches_salt_form_and_stereo_variants():
    mesylate = IMATINIB + ".CS(=O)(=O)O"
    assert client.get("/molecule/info", params={"smiles": mesylate}).json()["name"] == "IMATINIB"


def test_info_unknown_molecule_has_no_name_but_has_formula():
    body = client.get("/molecule/info", params={"smiles": "CC(C)(c1ccc(O)cc1)c1ccc(O)cc1"}).json()  # bisphenol A
    assert body["name"] is None and body["formula"] == "C15H16O2" and body["molecular_weight"] == 228.29


def test_info_invalid_smiles():
    assert client.get("/molecule/info", params={"smiles": "xyz"}).status_code == 422
