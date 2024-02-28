from sqlalchemy import create_engine
import os
from fastapi import Depends, HTTPException
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Annotated
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_utils import create_database, database_exists
from app.models import Base, Database
import settings

DATABASE_URL = os.getenv('DATABASE_URI')

if not database_exists(DATABASE_URL):
  create_database(DATABASE_URL)

engine =  create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

