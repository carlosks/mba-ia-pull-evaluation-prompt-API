from fastapi import FastAPI

app = FastAPI(title="API Profissional")

@app.get("/")
def health_check():
    return {"status": "ok"}
