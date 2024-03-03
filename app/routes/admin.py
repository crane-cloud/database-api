from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.schema import (DatabaseSchema)
from app.models import Database
from app.core.config import get_db
from typing import List
from app.core.database_service import generate_db_credentials
from app.core.database_flavor import get_db_flavour
from typing import Annotated

from app.helpers.decorators import admin_required , authenticate
from app.helpers.admin import get_current_user

router = APIRouter()

@router.get("/admin/databases/")
@admin_required
def get_all_databases(access_token:Annotated[str | None, Header()] = None , db: Session = Depends(get_db)):
    databases = db.query(Database).all()
    return databases

@router.get("/admin/mysql_databases/")
@admin_required
def get_all_mysql_databases(access_token:Annotated[str | None, Header()] = None  , db: Session = Depends(get_db)):
    mysql_databases = db.query(Database).filter(Database.database_flavour_name == "mysql").all()
    return mysql_databases

@router.get("/admin/postgresql_databases/")
@admin_required
def get_all_postgresql_databases(access_token:Annotated[str | None, Header()] = None , db: Session = Depends(get_db)):
    postgresql_databases = db.query(Database).filter(Database.database_flavour_name == "postgres").all()
    return postgresql_databases

@router.get("/admin/user_databases/")
@admin_required
def get_user_databases(access_token:Annotated[str | None, Header()] = None , db: Session = Depends(get_db)):
  current_user = get_current_user(access_token)
  user_databases = db.query(Database).filter(Database.owner_id == current_user['id']).first()
  if not user_databases:
    raise HTTPException(status_code=404, detail="No databases found for this user")
  return user_databases

@router.get("/admin/databases/{database_id}")
@admin_required
def get_single_databases(database_id:str, access_token:Annotated[str | None, Header()] = None , db: Session = Depends(get_db)):
  user_databases = db.query(Database).filter(Database.id == database_id).first()
  if not user_databases:
    raise HTTPException(status_code=404, detail="Databases not found")
  return user_databases

@router.delete("/admin/databases/{database_id}")
@admin_required
def delete_user_database(database_id:str,access_token:Annotated[str | None, Header()] = None , db: Session = Depends(get_db)):
  database = db.query(Database).filter(Database.id == database_id).first()
  if database is None:
    raise HTTPException(status_code=404, detail="Databases not found")
  db.delete(database)
  db.commit()
  return {"message": "Database deleted successfully"}

@router.post("/admin/databases/reset/{database_id}")
@admin_required
def reset_user_database(database_id:str, access_token:Annotated[str | None, Header()] = None , db: Session = Depends(get_db)):
  database = db.query(Database).filter(Database.id == database_id).first()
  if database is None:
    raise HTTPException(status_code=404, detail="Databases not found")

  db_flavour = get_db_flavour(database.database_flavour_name)

  if not db_flavour:
    return dict(
        status="fail",
        message=f"Database with flavour name {database.database_flavour_name} is not mysql or postgres."
    ), 409

  database_service = db_flavour['class']

  database_connection = database_service.check_db_connection()

  if not database_connection:
    return dict(
        status="fail",
        message=f"Failed to connect to the database service"
    ), 500

  reset_database = database_service.reset_database(
    db_name=database.name,
    user=database.user,
    password=database.password
  )

  if not reset_database:
    return dict(
        status="fail",
        message=f"Unable to reset database"
    ), 500

  return ({"status":'success', "message":"Database Reset Successfully"}), 200