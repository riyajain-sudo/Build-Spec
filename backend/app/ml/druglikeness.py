"""Rule-based drug-likeness: Lipinski's rule of five, Veber's rules, and RDKit's QED score.

Run: python -m app.ml.druglikeness "<SMILES>"
"""
import sys

from rdkit.Chem import QED, Descriptors, Lipinski, rdMolDescriptors

from app.ml.featurize import parse_smiles

# (property, description, limit) - a rule passes when value <= limit
LIPINSKI = [("MolWt", "Molecular weight <= 500", 500), ("LogP", "LogP <= 5", 5),
            ("HBD", "H-bond donors <= 5", 5), ("HBA", "H-bond acceptors <= 10", 10)]
VEBER = [("TPSA", "Polar surface area <= 140", 140), ("RotatableBonds", "Rotatable bonds <= 10", 10)]


def assess_druglikeness(smiles: str) -> dict:
    mol = parse_smiles(smiles)
    values = {
        "MolWt": Descriptors.MolWt(mol), "LogP": Descriptors.MolLogP(mol),
        "HBD": Lipinski.NumHDonors(mol), "HBA": Lipinski.NumHAcceptors(mol),
        "TPSA": rdMolDescriptors.CalcTPSA(mol), "RotatableBonds": rdMolDescriptors.CalcNumRotatableBonds(mol),
    }

    def check(rules):
        return [{"rule": desc, "property": prop, "value": round(float(values[prop]), 2),
                 "limit": limit, "passed": bool(values[prop] <= limit)} for prop, desc, limit in rules]

    lipinski, veber = check(LIPINSKI), check(VEBER)
    lip_violations = sum(not r["passed"] for r in lipinski)
    veber_ok = all(r["passed"] for r in veber)
    drug_like = lip_violations <= 1 and veber_ok
    qed = float(QED.qed(mol))
    return {
        "lipinski": {"violations": lip_violations, "passes": lip_violations <= 1, "rules": lipinski},
        "veber": {"passes": veber_ok, "rules": veber},
        "qed": round(qed, 3),
        "drug_like": drug_like,
        "summary": ("Drug-like" if drug_like else "Fails drug-likeness rules")
                   + f" (QED {qed:.2f}, {lip_violations} Lipinski violation(s))",
    }


def main():
    smiles = sys.argv[1] if len(sys.argv) > 1 else "CC(=O)Oc1ccccc1C(=O)O"
    try:
        res = assess_druglikeness(smiles)
    except ValueError as e:
        sys.exit(str(e))
    print(res["summary"])
    for r in res["lipinski"]["rules"] + res["veber"]["rules"]:
        print(f"  {'PASS' if r['passed'] else 'FAIL'}  {r['rule']:30s} {r['value']}")


if __name__ == "__main__":
    main()
