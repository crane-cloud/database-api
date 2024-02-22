from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, database_exists
from app.models import Base
import os
import settings

service_database = os.getenv('DATABASE_URL')
if not database_exists(service_database):
  create_database(service_database)

engine =  create_engine(service_database, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

