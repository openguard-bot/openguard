import sys
import os

# Add project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .app import api, admin  # Import the admin router
from database.connection import initialize_database
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dashboard.backend.app.crud")
logger.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database schema on startup."""
    await initialize_database()
    # Set uvicorn logger level to INFO as well, to see all requests
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.setLevel(logging.INFO)
    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    uvicorn_error_logger.setLevel(logging.INFO)
    yield


app = FastAPI(lifespan=lifespan)

# CORS configuration
origins = [
    os.getenv("FRONTEND_URL", "http://localhost"),
    "http://localhost:4321",  # Astro website
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api.router, prefix="/api")
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])


@app.get("/")
async def root():
    return {"message": "Welcome to the backend!"}
