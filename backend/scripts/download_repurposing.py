"""Download approved drugs, their targets (mechanisms) and approved indications from ChEMBL.

DrugBank's target/indication data needs a licensed account, so ChEMBL is used instead:
  molecule (max_phase=4)  -> approved drugs + structures
  mechanism               -> drug -> target protein links
  drug_indication         -> drug -> disease (MeSH / EFO), approved indications only
  target                  -> target names + UniProt accessions

Output CSVs in data/repurposing/. Run: python scripts/download_repurposing.py
"""
import time
from pathlib import Path

import pandas as pd
import requests

BASE = "https://www.ebi.ac.uk/chembl/api/data"
OUT = Path(__file__).resolve().parents[1] / "data" / "repurposing"
PAGE = 1000


def get(endpoint: str, params: dict) -> dict:
    for attempt in range(4):
        try:
            r = requests.get(f"{BASE}/{endpoint}.json", params=params, timeout=90)
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))


def fetch_all(endpoint: str, key: str, params: dict) -> list[dict]:
    rows, offset = [], 0
    while True:
        data = get(endpoint, {**params, "limit": PAGE, "offset": offset})
        rows += data[key]
        if not data["page_meta"]["next"]:
            return rows
        offset += PAGE
        time.sleep(0.3)


def fetch_by_ids(endpoint: str, key: str, id_field: str, ids: list[str], batch: int = 50) -> list[dict]:
    rows = []
    for i in range(0, len(ids), batch):
        chunk = ids[i:i + batch]
        rows += get(endpoint, {f"{id_field}__in": ",".join(chunk), "limit": batch})[key]
        time.sleep(0.2)
    return rows


def molecule_row(m: dict) -> dict | None:
    smiles = (m.get("molecule_structures") or {}).get("canonical_smiles")
    if not smiles or m.get("molecule_type") != "Small molecule":
        return None
    return {"chembl_id": m["molecule_chembl_id"], "name": m.get("pref_name"), "smiles": smiles,
            "first_approval": m.get("first_approval")}


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    print("approved molecules...")
    approved = fetch_all("molecule", "molecules", {"max_phase": 4})
    by_id = {m["molecule_chembl_id"]: m for m in approved}
    parent_of = {cid: (m.get("molecule_hierarchy") or {}).get("parent_chembl_id") or cid for cid, m in by_id.items()}
    parents = sorted(set(parent_of.values()))
    missing = [p for p in parents if p not in by_id]
    for m in fetch_by_ids("molecule", "molecules", "molecule_chembl_id", missing):
        by_id[m["molecule_chembl_id"]] = m
    drugs = {}
    for pid in parents:
        row = molecule_row(by_id[pid]) if pid in by_id else None
        if row:
            drugs[pid] = row
    drugs_df = pd.DataFrame(drugs.values())
    print(f"  {len(approved)} approved records -> {len(drugs_df)} unique small-molecule parent drugs")

    print("mechanisms...")
    mech = fetch_all("mechanism", "mechanisms", {})
    mech_df = pd.DataFrame([{
        "drug_id": m.get("parent_molecule_chembl_id") or m["molecule_chembl_id"],
        "target_id": m["target_chembl_id"], "action_type": m.get("action_type"),
        "mechanism": m.get("mechanism_of_action")} for m in mech if m.get("target_chembl_id")])
    mech_df = mech_df[mech_df.drug_id.isin(drugs)].drop_duplicates(["drug_id", "target_id"])
    print(f"  {len(mech_df)} drug-target links for {mech_df.drug_id.nunique()} drugs")

    print("indications...")
    ind = fetch_all("drug_indication", "drug_indications", {"max_phase_for_ind": 4})
    ind_df = pd.DataFrame([{
        "drug_id": i.get("parent_molecule_chembl_id") or i["molecule_chembl_id"],
        "disease": i.get("mesh_heading") or i.get("efo_term"), "mesh_id": i.get("mesh_id"),
        "efo_id": i.get("efo_id")} for i in ind])
    ind_df = ind_df.dropna(subset=["disease"])
    ind_df = ind_df[ind_df.drug_id.isin(drugs)].drop_duplicates(["drug_id", "disease"])
    print(f"  {len(ind_df)} approved indications, {ind_df.disease.nunique()} distinct diseases")

    print("targets...")
    tids = sorted(mech_df.target_id.unique())
    trows = []
    for t in fetch_by_ids("target", "targets", "target_chembl_id", tids):
        acc = [c.get("accession") for c in t.get("target_components", []) if c.get("accession")]
        trows.append({"target_id": t["target_chembl_id"], "name": t.get("pref_name"),
                      "target_type": t.get("target_type"), "uniprot": ";".join(acc)})
    targets_df = pd.DataFrame(trows)
    print(f"  {len(targets_df)} targets")

    drugs_df.to_csv(OUT / "drugs.csv", index=False)
    mech_df.to_csv(OUT / "drug_targets.csv", index=False)
    ind_df.to_csv(OUT / "indications.csv", index=False)
    targets_df.to_csv(OUT / "targets.csv", index=False)
    print(f"saved to {OUT}")


if __name__ == "__main__":
    main()
