from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = (
    "postgresql://sanjeev.dasgupta:npg_UbAvJimN3hE0@ep-solitary-meadow-593229-pooler.ap-southeast-1.aws.neon.tech/meddb?sslmode=require&channel_binding=require"
)

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)