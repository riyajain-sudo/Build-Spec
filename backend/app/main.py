from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import predict


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
    yield


app = FastAPI(title="Drug Discovery API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(predict.router)


@app.get("/health")
def health():
    return {"status": "ok"}
