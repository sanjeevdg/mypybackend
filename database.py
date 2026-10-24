from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, MetaData
from dotenv import load_dotenv
import os

#engine = create_engine(os.environ["DATABASE_URL"])

load_dotenv()   # Loads variables from .env

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    raise RuntimeError("DATABASE_URL not found")

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg2://",
        1
    )

engine = create_engine(DATABASE_URL)
metadata = MetaData()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)




