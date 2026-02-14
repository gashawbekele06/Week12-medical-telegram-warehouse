from fastapi import FastAPI
from api.routers import analytics

app = FastAPI(
    title="Medical Telegram Warehouse API",
    description="Analytical REST API for Ethiopian medical Telegram channels",
    version="1.0.0"
)

app.include_router(analytics.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Medical Telegram Warehouse API. Visit /docs"}