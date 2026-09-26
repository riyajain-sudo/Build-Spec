"""Identify a molecule: formula, weight, and a name when it is a known approved drug.

Names come from the local approved-drug table (no external service). A molecule is matched by the
connectivity block of its InChIKey after keeping only its largest fragment, so salts, hydrates and
stereoisomers of an approved drug still resolve to that drug.
"""
from functools import lru_cache

from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors
from rdkit.Chem.inchi import MolToInchiKey
from rdkit.Chem.MolStandardize import rdMolStandardize

from app.ml.featurize import parse_smiles

_chooser = rdMolStandardize.LargestFragmentChooser()


def _connectivity_key(mol: Chem.Mol) -> str:
    return MolToInchiKey(_chooser.choose(mol)).split("-")[0]


@lru_cache(maxsize=1)
def _drug_index() -> dict[str, str]:
    """connectivity key -> approved drug id. Empty if the repurposing database is not built."""
    from app.services.repurposing import load_index
    try:
        idx = load_index()
    except FileNotFoundError:
        return {}
    keys: dict[str, str] = {}
    for drug_id, smiles in idx.smiles.items():
        mol = Chem.MolFromSmiles(smiles)
        if mol is not None:
            keys.setdefault(_connectivity_key(mol), drug_id)
    return keys


def molecule_info(smiles: str) -> dict:
    """Raises ValueError for an invalid SMILES."""
    mol = parse_smiles(smiles)
    info = {
        "input_smiles": smiles.strip(),
        "canonical_smiles": Chem.MolToSmiles(mol),
        "formula": rdMolDescriptors.CalcMolFormula(mol),
        "molecular_weight": round(Descriptors.MolWt(mol), 2),
        "name": None, "chembl_id": None, "approved_for": [],
    }
    drug_id = _drug_index().get(_connectivity_key(mol))
    if drug_id:
        from app.services.repurposing import load_index
        idx = load_index()
        info["name"] = idx.names[drug_id]
        info["chembl_id"] = drug_id
        info["approved_for"] = sorted(set(idx.drug_diseases.get(drug_id, [])))[:5]
    return info
