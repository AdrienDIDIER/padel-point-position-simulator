import os
from fastapi import FastAPI
from .routers import ranking_router
from .database import data_manager
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

# Define a lifespan function
async def lifespan(app: FastAPI):
    # Code that runs before the application starts serving requests:
    data_manager.load_data()
    # yield separates startup and shutdown
    yield


app = FastAPI(
    title="Padel Ranking API",
    version="1.0.0",
    lifespan=lifespan
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # or ["*"] for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ranking_router.router, prefix="/api", tags=["Ranking"])

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "ok"}
