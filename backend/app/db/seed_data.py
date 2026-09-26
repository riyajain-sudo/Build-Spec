"""Load the downloaded ChEMBL repurposing CSVs into SQLite (data/drugs.db).

Run: python -m app.db.seed_data   (after scripts/download_repurposing.py)
"""
from pathlib import Path

import numpy as np
import pandas as pd

from app.db.models import DB_PATH, Base, Drug, DrugTarget, Indication, Target, engine, get_session
from app.ml.featurize import morgan_fingerprint, parse_smiles

CSV_DIR = Path(__file__).resolve().parents[2] / "data" / "repurposing"


def none_if_nan(v):
    return None if pd.isna(v) else v


def main():
    drugs = pd.read_csv(CSV_DIR / "drugs.csv")
    links = pd.read_csv(CSV_DIR / "drug_targets.csv")
    inds = pd.read_csv(CSV_DIR / "indications.csv")
    targets = pd.read_csv(CSV_DIR / "targets.csv")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with get_session() as s:
        kept = set()
        for r in drugs.itertuples():
            try:
                fp = np.packbits(morgan_fingerprint(parse_smiles(r.smiles))).tobytes()
            except ValueError:
                continue  # unparseable structure
            s.add(Drug(id=r.chembl_id, name=none_if_nan(r.name), smiles=r.smiles, fingerprint=fp,
                       first_approval=None if pd.isna(r.first_approval) else int(r.first_approval)))
            kept.add(r.chembl_id)
        for r in targets.itertuples():
            s.add(Target(id=r.target_id, name=none_if_nan(r.name), target_type=none_if_nan(r.target_type),
                         uniprot=none_if_nan(r.uniprot)))
        s.flush()
        target_ids = set(targets.target_id)
        for r in links.itertuples():
            if r.drug_id in kept and r.target_id in target_ids:
                s.add(DrugTarget(drug_id=r.drug_id, target_id=r.target_id,
                                 action_type=none_if_nan(r.action_type), mechanism=none_if_nan(r.mechanism)))
        for r in inds.itertuples():
            if r.drug_id in kept:
                s.add(Indication(drug_id=r.drug_id, disease=r.disease, disease_norm=r.disease.strip().lower(),
                                 mesh_id=none_if_nan(r.mesh_id)))
        s.commit()
        print(f"seeded {DB_PATH}: {s.query(Drug).count()} drugs, {s.query(Target).count()} targets, "
              f"{s.query(DrugTarget).count()} drug-target links, {s.query(Indication).count()} indications")


if __name__ == "__main__":
    main()
