"""SMILES -> feature vector (Morgan fingerprint + basic physchem descriptors).

Run as a script to print the feature vector for one molecule:
    python -m app.ml.featurize "CC(=O)Oc1ccccc1C(=O)O"
"""
import sys

import numpy as np
from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors, Lipinski, rdFingerprintGenerator, rdMolDescriptors

RDLogger.DisableLog("rdApp.*")

FP_RADIUS = 2
FP_BITS = 2048

DESCRIPTOR_FUNCS = {
    "MolWt": Descriptors.MolWt,
    "LogP": Descriptors.MolLogP,
    "HBD": Lipinski.NumHDonors,
    "HBA": Lipinski.NumHAcceptors,
    "RingCount": rdMolDescriptors.CalcNumRings,
    "TPSA": rdMolDescriptors.CalcTPSA,
    "RotatableBonds": rdMolDescriptors.CalcNumRotatableBonds,
}
DESCRIPTOR_NAMES = list(DESCRIPTOR_FUNCS)
FP_NAMES = [f"morgan_{i}" for i in range(FP_BITS)]
FEATURE_NAMES = DESCRIPTOR_NAMES + FP_NAMES  # descriptors first, then fingerprint bits

_fp_gen = rdFingerprintGenerator.GetMorganGenerator(radius=FP_RADIUS, fpSize=FP_BITS)


def parse_smiles(smiles: str) -> Chem.Mol:
    """Parse a SMILES string; raises ValueError if it is not a valid molecule."""
    mol = Chem.MolFromSmiles(smiles.strip()) if isinstance(smiles, str) else None
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles!r}")
    return mol


def descriptors(mol: Chem.Mol) -> dict[str, float]:
    return {name: float(fn(mol)) for name, fn in DESCRIPTOR_FUNCS.items()}


def morgan_fingerprint(mol: Chem.Mol) -> np.ndarray:
    return _fp_gen.GetFingerprintAsNumPy(mol).astype(np.uint8)


def featurize(smiles: str) -> np.ndarray:
    """Return a 1-D float32 vector aligned with FEATURE_NAMES."""
    mol = parse_smiles(smiles)
    desc = np.array(list(descriptors(mol).values()), dtype=np.float32)
    return np.concatenate([desc, morgan_fingerprint(mol).astype(np.float32)])


def featurize_many(smiles_list) -> tuple[np.ndarray, list[int]]:
    """Featurize a list, skipping invalid SMILES. Returns (matrix, indices of valid inputs)."""
    rows, kept = [], []
    for i, s in enumerate(smiles_list):
        try:
            rows.append(featurize(s))
            kept.append(i)
        except ValueError:
            pass
    return np.vstack(rows), kept


def main():
    smiles = sys.argv[1] if len(sys.argv) > 1 else "CC(=O)Oc1ccccc1C(=O)O"  # aspirin
    try:
        mol = parse_smiles(smiles)
    except ValueError as e:
        sys.exit(str(e))
    vec = featurize(smiles)
    print(f"SMILES: {smiles}")
    print(f"Feature vector length: {len(vec)} ({len(DESCRIPTOR_NAMES)} descriptors + {FP_BITS}-bit Morgan r={FP_RADIUS})")
    print("\nDescriptors:")
    for name, val in descriptors(mol).items():
        print(f"  {name:15s} {val:.3f}")
    on = np.flatnonzero(vec[len(DESCRIPTOR_NAMES):])
    print(f"\nMorgan bits set: {len(on)} -> {on.tolist()}")


if __name__ == "__main__":
    main()
