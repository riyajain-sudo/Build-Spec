"""Drug repurposing endpoint: disease name -> ranked candidate approved drugs with reasons."""
from fastapi import APIRouter, HTTPException, Query

from app.services.repurposing import _stems, load_index, repurpose

router = APIRouter(prefix="/repurpose", tags=["repurpose"])
diseases_router = APIRouter(prefix="/diseases", tags=["repurpose"])


@diseases_router.get("")
def search_diseases(q: str = Query("", max_length=100), limit: int = Query(15, ge=1, le=50)):
    """Disease names (with number of approved drugs) for the search dropdown, most-treated first."""
    try:
        idx = load_index()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    needle = q.strip().lower()
    q_stems = set(_stems(q)) if needle else set()
    hits = []
    for name, drugs in idx.diseases.items():
        low = name.lower()
        if not needle or needle in low or (q_stems and q_stems <= set(idx.disease_stems[name])):
            hits.append({"name": name, "n_drugs": len(drugs), "starts": low.startswith(needle)})
    hits.sort(key=lambda h: (not h["starts"], -h["n_drugs"], h["name"]))
    return [{"name": h["name"], "n_drugs": h["n_drugs"]} for h in hits[:limit]]


@router.get("/{disease}")
def repurpose_disease(disease: str, top_n: int = Query(10, ge=1, le=50, description="Number of candidates to return")):
    if not disease.strip() or len(disease) > 200:
        raise HTTPException(status_code=422, detail="Disease name must be 1-200 characters")
    try:
        result = repurpose(disease, top_n)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    if not result["matched_diseases"]:
        hint = f" Did you mean: {', '.join(result['suggestions'])}?" if result["suggestions"] else ""
        raise HTTPException(status_code=404, detail=f"No disease matching {disease!r} in the approved-indications data.{hint}")
    return result
