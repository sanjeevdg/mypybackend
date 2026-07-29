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

engine = create_engine(DATABASE_URL)
metadata = MetaData()


'''DATABASE_URL = (
    "postgresql://sanjeev.dasgupta:npg_oKIZNsEe0Oy4@ep-solitary-meadow-593229-pooler.ap-southeast-1.aws.neon.tech/meddb?sslmode=require&channel_binding=require"
)
engine = create_engine(DATABASE_URL)

'''


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)




