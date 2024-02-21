from sqlalchemy import create_engine
from fastapi import Depends, HTTPException
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Annotated
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_utils import create_database, database_exists
from app.models import Base, Database
import os
import settings

service_database = os.getenv('DATABASE_URL')
if not database_exists(service_database):
  create_database(service_database)

engine =  create_engine(service_database, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

