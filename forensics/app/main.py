from fastapi import FastAPI

app = FastAPI(title="Forensics Service")

@app.get("/health")
def health():
    return {"status": "ok"}
