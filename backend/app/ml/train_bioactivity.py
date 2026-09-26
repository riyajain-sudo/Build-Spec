"""Train the kinase bioactivity classifier (active = pIC50 >= 6, i.e. IC50 <= 1 uM).

One XGBoost model is trained per kinase, so predictions are target-specific.

Run: python -m app.ml.train_bioactivity
"""
import json
from collections import defaultdict
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from rdkit.Chem.Scaffolds import MurckoScaffold
from sklearn.metrics import accuracy_score, roc_auc_score
from xgboost import XGBClassifier

from app.ml.featurize import FEATURE_NAMES, featurize_many, parse_smiles

BACKEND = Path(__file__).resolve().parents[2]
DATA = BACKEND / "data" / "chembl" / "kinase_activities.csv"
MODEL_PATH = BACKEND / "app" / "models" / "bioactivity.pkl"
ACTIVE_PCHEMBL = 6.0
TEST_FRACTION = 0.2
SEED = 42


def scaffold_of(smiles: str) -> str:
    try:
        return MurckoScaffold.MurckoScaffoldSmiles(mol=parse_smiles(smiles))
    except ValueError:
        return ""


def scaffold_split(smiles: pd.Series, test_fraction: float, seed: int):
    """Assign whole scaffold groups to train or test so analogs don't leak across the split."""
    groups = defaultdict(list)
    for i, s in enumerate(smiles):
        groups[scaffold_of(s)].append(i)
    keys = list(groups)
    np.random.default_rng(seed).shuffle(keys)
    test_idx, n_test = [], int(len(smiles) * test_fraction)
    for k in keys:
        if len(test_idx) >= n_test:
            break
        test_idx += groups[k]
    test_set = set(test_idx)
    train_idx = [i for i in range(len(smiles)) if i not in test_set]
    return np.array(train_idx), np.array(sorted(test_idx))


def make_model() -> XGBClassifier:
    return XGBClassifier(
        n_estimators=300, max_depth=5, learning_rate=0.05, subsample=0.8,
        colsample_bytree=0.5, eval_metric="auc", n_jobs=-1, random_state=SEED,
    )


def main():
    df = pd.read_csv(DATA)
    X, kept = featurize_many(df.smiles)
    df = df.iloc[kept].reset_index(drop=True)
    y = (df.pchembl_value >= ACTIVE_PCHEMBL).astype(int).to_numpy()
    targets = sorted(df.target_name.unique())

    # one global scaffold split so every kinase model is tested on the same held-out scaffolds
    tr, te = scaffold_split(df.smiles, TEST_FRACTION, SEED)
    print(f"rows: {len(df)} | train {len(tr)} | test {len(te)}\n")

    models, metrics = {}, {"per_target": {}}
    all_true, all_proba = [], []
    print(f"{'target':8s} {'n_test':>6s} {'active%':>8s} {'AUC':>6s} {'acc':>6s} {'baseline':>9s}")
    for t in targets:
        is_t = (df.target_name == t).to_numpy()
        tr_t, te_t = tr[is_t[tr]], te[is_t[te]]
        model = make_model().fit(X[tr_t], y[tr_t])
        proba = model.predict_proba(X[te_t])[:, 1]
        m = {
            "n_test": len(te_t),
            "active_rate": float(y[te_t].mean()),
            "roc_auc": roc_auc_score(y[te_t], proba) if len(set(y[te_t])) == 2 else None,
            "accuracy": accuracy_score(y[te_t], proba >= 0.5),
            "majority_baseline_accuracy": float(max(y[te_t].mean(), 1 - y[te_t].mean())),
        }
        metrics["per_target"][t] = m
        all_true.append(y[te_t]); all_proba.append(proba)
        auc = f"{m['roc_auc']:.3f}" if m["roc_auc"] is not None else "n/a"
        print(f"{t:8s} {m['n_test']:6d} {m['active_rate']:8.1%} {auc:>6s} {m['accuracy']:6.3f} {m['majority_baseline_accuracy']:9.3f}")
        # refit on all rows for this kinase for the shipped model
        models[t] = make_model().fit(X[is_t], y[is_t])

    yt, yp = np.concatenate(all_true), np.concatenate(all_proba)
    metrics["pooled_roc_auc"] = roc_auc_score(yt, yp)
    metrics["pooled_accuracy"] = accuracy_score(yt, yp >= 0.5)
    print(f"\nPooled test AUC {metrics['pooled_roc_auc']:.3f} | accuracy {metrics['pooled_accuracy']:.3f}")

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"models": models, "targets": targets, "feature_names": FEATURE_NAMES,
                 "active_pchembl": ACTIVE_PCHEMBL, "metrics": metrics}, MODEL_PATH)
    MODEL_PATH.with_suffix(".metrics.json").write_text(json.dumps(metrics, indent=2))
    print(f"saved -> {MODEL_PATH}")


if __name__ == "__main__":
    main()
