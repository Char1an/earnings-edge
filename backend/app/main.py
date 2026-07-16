from fastapi import FastAPI

app = FastAPI(title="earnings-edge", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
