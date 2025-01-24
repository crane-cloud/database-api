import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, database_exists
from config import settings
from sqlalchemy.ext.declarative import declarative_base

if os.environ.get("FASTAPI_ENV") == "testing":
    DATABASE_URI = "postgresql://postgres:postgres@localhost:4200/cranecloud_test"
else:
    DATABASE_URI = settings.DATABASE_URI

if not database_exists(DATABASE_URI):
    create_database(DATABASE_URI)


engine = create_engine(DATABASE_URI, pool_pre_ping=True,
                       pool_size=10, max_overflow=20)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Base.metadata.create_all(bind=engine)
