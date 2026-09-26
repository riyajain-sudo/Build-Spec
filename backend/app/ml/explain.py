"""SHAP explanations for the bioactivity and toxicity models.

Contributions are in log-odds space (XGBoost's raw margin): positive values push the
prediction toward "active" / "toxic", negative values push away from it.

Morgan-bit features are translated to the substructure that set the bit, so an
explanation reads "contains fragment c1ccncc1" instead of "morgan_1057".

Run: python -m app.ml.explain "<SMILES>" [bioactivity|toxicity] [endpoint]
"""
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import shap
from rdkit import Chem
from rdkit.Chem import rdFingerprintGenerator

from app.ml.featurize import DESCRIPTOR_NAMES, FP_BITS, FP_RADIUS, featurize, parse_smiles
from app.ml.predict_bioactivity import load_bundle as load_bioactivity
from app.ml.predict_toxicity import load_bundle as load_toxicity

N_DESC = len(DESCRIPTOR_NAMES)
_fp_gen = rdFingerprintGenerator.GetMorganGenerator(radius=FP_RADIUS, fpSize=FP_BITS)


@lru_cache(maxsize=64)
def _explainer(kind: str, endpoint: str) -> shap.TreeExplainer:
    bundle = load_bioactivity() if kind == "bioactivity" else load_toxicity()
    return shap.TreeExplainer(bundle["models"][endpoint])


def bit_fragments(mol: Chem.Mol) -> dict[int, str]:
    """Map each set Morgan bit to a SMILES of one substructure that produced it."""
    ao = rdFingerprintGenerator.AdditionalOutput()
    ao.AllocateBitInfoMap()
    _fp_gen.GetFingerprint(mol, additionalOutput=ao)
    frags = {}
    for bit, envs in ao.GetBitInfoMap().items():
        atom_idx, radius = envs[0]
        if radius == 0:
            frags[bit] = f"atom {mol.GetAtomWithIdx(atom_idx).GetSymbol()}"
            continue
        bond_ids = Chem.FindAtomEnvironmentOfRadiusN(mol, radius, atom_idx)
        atoms = {atom_idx}
        for b in bond_ids:
            bond = mol.GetBondWithIdx(b)
            atoms |= {bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()}
        frags[bit] = Chem.MolFragmentToSmiles(mol, atomsToUse=sorted(atoms), bondsToUse=list(bond_ids))
    return frags


def explain(kind: str, endpoint: str, smiles: str, top_k: int = 8) -> dict:
    """Top SHAP contributions for one molecule and one endpoint/target.

    Only features that are present in the molecule are reported (descriptors, and
    fingerprint bits that are set) - absent bits carry no readable meaning.
    """
    bundle = load_bioactivity() if kind == "bioactivity" else load_toxicity()
    if endpoint not in bundle["models"]:
        raise KeyError(f"Unknown {kind} endpoint {endpoint!r}; choose from {list(bundle['models'])}")
    mol = parse_smiles(smiles)
    x = featurize(smiles).reshape(1, -1)
    explainer = _explainer(kind, endpoint)
    sv = explainer.shap_values(x)[0]
    base = float(np.ravel(explainer.expected_value)[0])
    prob = float(bundle["models"][endpoint].predict_proba(x)[0, 1])

    frags = bit_fragments(mol)
    rows = []
    for i, contrib in enumerate(sv):
        if i < N_DESC:
            name = DESCRIPTOR_NAMES[i]
            rows.append({"feature": name, "label": f"{name} = {x[0, i]:.2f}", "type": "descriptor",
                         "value": float(x[0, i]), "shap": float(contrib)})
        elif x[0, i] > 0:
            bit = i - N_DESC
            rows.append({"feature": f"morgan_{bit}", "label": f"contains substructure {frags.get(bit, '?')}",
                         "type": "substructure", "value": 1.0, "shap": float(contrib)})
    rows.sort(key=lambda r: -abs(r["shap"]))
    top = rows[:top_k]
    for r in top:
        r["direction"] = "increases" if r["shap"] > 0 else "decreases"
    return {"kind": kind, "endpoint": endpoint, "smiles": smiles, "probability": prob,
            "base_probability": float(1 / (1 + np.exp(-base))), "base_logit": base,
            "contributions": top}


def plot_explanation(result: dict, path: Path) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = result["contributions"][::-1]
    colors = ["#d1495b" if r["shap"] > 0 else "#2e86ab" for r in rows]
    fig, ax = plt.subplots(figsize=(9, 0.5 * len(rows) + 1.6))
    ax.barh([r["label"] for r in rows], [r["shap"] for r in rows], color=colors)
    ax.axvline(0, color="#444", lw=0.8)
    ax.set_xlabel("SHAP value (log-odds): red pushes toward active/toxic, blue pushes away")
    ax.set_title(f"{result['kind']} / {result['endpoint']}  -  P = {result['probability']:.2f} "
                 f"(baseline {result['base_probability']:.2f})")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def main():
    smiles = sys.argv[1] if len(sys.argv) > 1 else "COCCOc1cc2ncnc(Nc3cccc(C#C)c3)c2cc1OCCOC"
    kind = sys.argv[2] if len(sys.argv) > 2 else "bioactivity"
    endpoint = sys.argv[3] if len(sys.argv) > 3 else ("EGFR" if kind == "bioactivity" else "SR-MMP")
    try:
        res = explain(kind, endpoint, smiles)
    except (ValueError, KeyError) as e:
        sys.exit(str(e))
    print(f"{kind}/{endpoint} for {smiles}\nP = {res['probability']:.3f} (baseline {res['base_probability']:.3f})\n")
    for r in res["contributions"]:
        print(f"  {r['shap']:+.3f}  {r['direction']:9s}  {r['label']}")
    out = Path(__file__).resolve().parents[2] / "data" / f"shap_{kind}_{endpoint}.png"
    print(f"\nplot -> {plot_explanation(res, out)}")


if __name__ == "__main__":
    main()
