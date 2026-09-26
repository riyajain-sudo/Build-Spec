from fastapi import FastAPI

app = FastAPI(title="Drug Discovery API")


@app.get("/health")
def health():
    return {"status": "ok"}
