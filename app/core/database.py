from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, database_exists
from app.models import Base
import os
import settings


DATABASE_URL = os.getenv('DATABASE_URI')

if not database_exists(DATABASE_URL):
  create_database(DATABASE_URL)


engine =  create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

