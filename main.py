from fastapi import FastAPI
from .api import router

app = FastAPI(title="Sched_AI (SRP Refactor)")
app.include_router(router)

@app.get("/")
def home():
    return {"message": "Sched_AI API running (SRP applied)"}
