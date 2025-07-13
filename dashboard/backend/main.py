import sys
import os

# Add project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import api
from database.connection import initialize_database

app = FastAPI()

# CORS configuration
origins = [
    "http://localhost:3000",  # React frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api.router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Welcome to the backend!"}


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize the database schema on startup."""
    await initialize_database()
