"""Structure images: SMILES -> SVG drawn with RDKit."""
from fastapi import APIRouter, HTTPException, Query, Response
from rdkit.Chem import rdDepictor
from rdkit.Chem.Draw import rdMolDraw2D

from app.ml.featurize import parse_smiles
from app.services.molecule_info import molecule_info

router = APIRouter(prefix="/molecule", tags=["molecule"])


@router.get("/svg")
def molecule_svg(smiles: str = Query(..., min_length=1, max_length=500),
                 width: int = Query(320, ge=100, le=800), height: int = Query(240, ge=100, le=800)):
    try:
        mol = parse_smiles(smiles)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    rdDepictor.Compute2DCoords(mol)
    drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
    drawer.drawOptions().clearBackground = False  # transparent, so it works in light and dark cards
    drawer.DrawMolecule(mol)
    drawer.FinishDrawing()
    return Response(drawer.GetDrawingText(), media_type="image/svg+xml",
                    headers={"Cache-Control": "public, max-age=86400"})


@router.get("/info")
def molecule_details(smiles: str = Query(..., min_length=1, max_length=500)):
    """Formula, weight, canonical SMILES, and the drug name when the molecule is an approved drug."""
    try:
        return molecule_info(smiles)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
