"""Download a kinase bioactivity subset from the ChEMBL REST API.

Output: data/chembl/kinase_activities.csv with one row per (compound, target)
measurement: smiles, molecule_chembl_id, target_chembl_id, target_name, pchembl_value.
"""
import time
from pathlib import Path

import pandas as pd
import requests

API = "https://www.ebi.ac.uk/chembl/api/data/activity.json"
OUT = Path(__file__).resolve().parents[1] / "data" / "chembl" / "kinase_activities.csv"

TARGETS = {
    "CHEMBL203": "EGFR",
    "CHEMBL1862": "ABL1",
    "CHEMBL301": "CDK2",
    "CHEMBL267": "SRC",
    "CHEMBL279": "VEGFR2",
    "CHEMBL5145": "BRAF",
}
MAX_PER_TARGET = 2000
PAGE = 1000


def fetch_target(chembl_id: str) -> list[dict]:
    params = {
        "target_chembl_id": chembl_id,
        "standard_type": "IC50",
        "standard_relation": "=",
        "pchembl_value__isnull": "false",
        "limit": PAGE,
        "offset": 0,
    }
    rows = []
    while len(rows) < MAX_PER_TARGET:
        r = requests.get(API, params=params, timeout=60)
        r.raise_for_status()
        data = r.json()
        for a in data["activities"]:
            if a.get("canonical_smiles"):
                rows.append({
                    "molecule_chembl_id": a["molecule_chembl_id"],
                    "smiles": a["canonical_smiles"],
                    "target_chembl_id": chembl_id,
                    "target_name": TARGETS[chembl_id],
                    "pchembl_value": float(a["pchembl_value"]),
                })
        if not data["page_meta"]["next"]:
            break
        params["offset"] += PAGE
        time.sleep(0.5)
    return rows[:MAX_PER_TARGET]


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for cid, name in TARGETS.items():
        got = fetch_target(cid)
        print(f"{name:7s} {cid}: {len(got)} activities")
        rows += got
    df = pd.DataFrame(rows)
    # a compound measured several times on one target -> median pChEMBL
    df = (df.groupby(["molecule_chembl_id", "smiles", "target_chembl_id", "target_name"], as_index=False)
            ["pchembl_value"].median())
    df.to_csv(OUT, index=False)
    print(f"saved {len(df)} rows ({df.molecule_chembl_id.nunique()} unique compounds) -> {OUT}")


if __name__ == "__main__":
    main()
