import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

import redis.asyncio as redis

# Load environment variables from the root .env file
load_dotenv(dotenv_path="../../.env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Construct the URL from individual components if DATABASE_URL is not set
    db_user = os.getenv("DB_USER", "aimod_user")
    db_password = os.getenv("DB_PASSWORD", "")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "aimod_bot")
    DATABASE_URL = (
        f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    )

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)

Base = declarative_base()

redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost"))


# Dependency to get a DB session
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
