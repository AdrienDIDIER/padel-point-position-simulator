from fastapi import FastAPI
from .routers import ranking_router
from .database import data_manager
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Padel Ranking API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # or ["*"] for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    data_manager.load_data()

app.include_router(ranking_router.router, prefix="/api", tags=["Ranking"])

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "ok"}
