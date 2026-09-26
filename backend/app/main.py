from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import molecule, predict, repurpose


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm the model caches so the first request is fast. A missing model file is
    # reported per request as a 503 rather than stopping the server from starting.
    from app.ml.predict_bioactivity import load_bundle as load_bio
    from app.ml.predict_toxicity import load_bundle as load_tox
    for loader in (load_bio, load_tox):
        try:
            loader()
        except FileNotFoundError:
            pass
    try:
        from app.services.repurposing import load_index
        load_index()
    except Exception:  # repurposing DB not seeded yet: /repurpose returns 503 until it is
        pass
    yield


app = FastAPI(title="Drug Discovery API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(predict.router)
app.include_router(repurpose.router)
app.include_router(repurpose.diseases_router)
app.include_router(molecule.router)


@app.get("/health")
def health():
    return {"status": "ok"}
