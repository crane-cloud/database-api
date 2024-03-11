from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, database_exists
from config import settings
from sqlalchemy.ext.declarative import declarative_base


DATABASE_URI = settings.DATABASE_URI

if not database_exists(DATABASE_URI):
    create_database(DATABASE_URI)


engine = create_engine(DATABASE_URI, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Base.metadata.create_all(bind=engine)
