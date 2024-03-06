from fastapi import APIRouter, Depends, HTTPException, Header
from app.schema import (DatabaseSchema, DatabaseFlavor, PasswordUpdate)
from app.models import Database
from sqlalchemy.orm import Session
from app.helpers.database_session import get_db
from typing import List
import os
import json
from app.helpers.database_service import generate_db_credentials
from app.helpers.database_flavor import get_db_flavour

from typing import Annotated
#from fastapi import FastAPI, Header
from app.helpers.decorators import admin_required , authenticate
from app.helpers.admin import get_current_user

router = APIRouter()

@router.post("/databases")
@authenticate
def create_database(database: DatabaseFlavor, access_token:Annotated[str | None, Header()] = None , db: Session = Depends(get_db)):

  credentials = generate_db_credentials()
  db_flavor = get_db_flavour(database.database_flavour_name)
  current_user = get_current_user(access_token)

  if not db_flavor:
    return dict(
      status="fail",
      message=f"Database flavour with name {database.database_flavour_name} is not mysql or postgres."
    ), 409
  

  
  existing_name = db.query(Database).filter(Database.name == credentials.name).first()
  if existing_name:
    raise HTTPException(status_code=400, detail="Database with this name already exists")
  
  existing_user = db.query(Database).filter(Database.user == credentials.user).first()
  if existing_user:
    raise HTTPException(status_code=400, detail="Database with this user already exists")

  
  new_database_info = dict(
      user=credentials.user,
      password=credentials.password,
      name=credentials.name,
      database_flavour_name=database.database_flavour_name,
      host=db_flavor['host'],
      port=db_flavor['port'],
      owner_id= current_user['id']
  )

  try:
    new_db = DatabaseSchema(**new_database_info)

  except ValueError as e:
    return {"error": f"Validation failed: {str(e)}", "status_code": 400}
  
  
  database_service = db_flavor['class']
  database_connection = database_service.check_db_connection()

  if not database_connection:
    return dict(
        status="fail",
        message=f"Failed to connect to the database service"
    ), 500
  
  database_name = credentials.name
  database_user = credentials.user
  database_password = credentials.password
  
  create_database = database_service.create_database(
    db_name=database_name,
    user=database_user,
    password=database_password
  )

  if not create_database:
    return dict(
        status="fail",
        message=f"Unable to create database"
    ), 500

  # try:
  database = Database(**new_database_info)
  db.add(database)
  db.commit()
  db.refresh(database)
  return dict(
      status='success',
      data=database
  ), 201

@router.get("/databases/")
@admin_required
def get_all_databases(access_token:Annotated[str | None, Header()] = None , db: Session = Depends(get_db)):
    databases = db.query(Database).all()
    return databases

@router.get("/mysql_databases")
@admin_required
def admin_get_all_mysql_databases(access_token:Annotated[str | None, Header()] = None ,db: Session = Depends(get_db)):
    mysql_databases = db.query(Database).filter(Database.database_flavour_name == "mysql").all()
    return mysql_databases

@router.get("/postgresql_databases")
@admin_required
def admin_get_all_postgresql_databases(access_token:Annotated[str | None, Header()] = None ,db: Session = Depends(get_db)):
    postgresql_databases = db.query(Database).filter(Database.database_flavour_name == "postgres").all()
    return postgresql_databases

@router.get("/databases/{database_id}")
@authenticate
def get_single_databases(database_id:str, access_token:Annotated[str | None, Header()] = None ,db: Session = Depends(get_db)):
  user_databases = db.query(Database).filter(Database.id == database_id).first()
  if not user_databases:
    raise HTTPException(status_code=404, detail="Databases not found")
  return user_databases

@router.get("/databases/{database_id}/password")
@admin_required
def admin_get_database_password(database_id:str, access_token:Annotated[str | None, Header()] = None ,db: Session = Depends(get_db)):
  db_exists = db.query(Database).filter(Database.id == database_id).first()
  if not db_exists:
    raise HTTPException(status_code=404, detail="Database not found")
  return db_exists.password

@router.post("/databases/{database_id}/admin_enable")
@admin_required
def admin_enable_user_database(database_id:str,access_token:Annotated[str | None, Header()] = None , db: Session = Depends(get_db)):
  database = db.query(Database).filter(Database.id == database_id).first()
  if database is None:
    raise HTTPException(status_code=404, detail="Databases not found")
  
  if (database.admin_disabled == False):
    raise HTTPException(status_code=404, detail="Databases is already enabled.")
  
  database.admin_disabled = False
  db.commit()
  return {"message": "Database enabled successfully"}


@router.post("/databases/{database_id}/admin_disable")
@admin_required
def admin_disable_user_database(database_id:str, access_token:Annotated[str | None, Header()] = None ,db: Session = Depends(get_db)):
  database = db.query(Database).filter(Database.id == database_id).first()
  if database is None:
    raise HTTPException(status_code=404, detail="Databases not found")
  
  if database.admin_disabled:
    raise HTTPException(status_code=404, detail="Databases is already disabled.")
  
  database.admin_disabled = True
  db.commit()
  return {"message": "Database disabled successfully"}

@router.delete("/databases/{database_id}")
@authenticate
def delete_user_database(database_id:str, access_token:Annotated[str | None, Header()] = None , db: Session = Depends(get_db)):
  database = db.query(Database).filter(Database.id == database_id).first()
  if database is None:
    raise HTTPException(status_code=404, detail="Databases not found")
  db.delete(database)
  db.commit()
  return {"message": "Database deleted successfully"}

@router.post("/databases/{database_id}/reset")
@authenticate
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

@router.post("/databases/{database_id}/reset_password")
@authenticate
def password_reset_database(database_id:str, field_update:PasswordUpdate, access_token:Annotated[str | None, Header()] = None , db: Session = Depends(get_db)):
  database = db.query(Database).filter(Database.id == database_id).first()
  if not database:
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

  password_reset_database = database_service.reset_password(
    
    user=database.user,
    password= field_update.password
  )

  if not password_reset_database:
    return dict(
        status="fail",
        message=f"Unable to reset database password"
    ), 500
  
  database.password = field_update.password

  db.commit()

  return ({"status":'success', "message":"Database Password Reset Successfully"}), 200

@router.get("/check_database_storage/{database_id}")
@authenticate
def check_database_storage(database_id: str, access_token:Annotated[str | None, Header()] = None , db: Session = Depends(get_db)):
    database = db.query(Database).filter(Database.id == database_id).first()
    if not database:
        raise HTTPException(status_code=404, detail="Database not found")
    
    if database.default_storage_kb > database.allocated_size_kb:
        database.admin_disabled = True
        db.commit()
        return {"message": "Admin disabled the database due to exceeding allocated storage"}
    return {"message": "Database storage is within allocated limits"}

@router.get("/check_database_storage_limit/{database_id}")
@authenticate
def check_database_storage_limit(database_id: str, access_token:Annotated[str | None, Header()] = None , db: Session = Depends(get_db)):
    database = db.query(Database).filter(Database.id == database_id).first()
    if not database:
        raise HTTPException(status_code=404, detail="Database not found")
    
    db_flavour = get_db_flavour(database.database_flavour_name)
    if not db_flavour:
        raise HTTPException(status_code=404, detail="Database flavor not found")
    
    database_service = db_flavour['class']

    database_connection = database_service.check_db_connection()

    if not database_connection:
        raise HTTPException(status_code=404, detail="Failed to connect to Database")
    # everty = database_service.get_database_size(
    #    user=database.user, password=database.password, db_name=database.name
    # )

    # db_size = None
    # if everty == "0.0 MB":
    #   db_size = 0
    #   database.default_storage_kb = 0
    #   db.commit()
    
    # if db_size > 0.7 * database.allocated_size_kb:
    return {f"Database limit is {database.allocated_size_kb} kbs."}

@router.post("/update_database_storage/{database_id}")
@authenticate
def update_database_storage(database_id: str, new_storage: int, access_token:Annotated[str | None, Header()] = None , db: Session = Depends(get_db)):
    database = db.query(Database).filter(Database.id == database_id).first()
    if not database:
        raise HTTPException(status_code=404, detail="Database not found")
    
    database.default_storage_kb = new_storage
    db.commit()
    return {"message": "Database storage updated successfully"}

@router.post("/allocate_more_storage/{database_id}")
@admin_required
def allocate_more_storage(database_id: str, additional_storage: int, access_token:Annotated[str | None, Header()] = None , db: Session = Depends(get_db)):
    database = db.query(Database).filter(Database.id == database_id).first()
    if not database:
        raise HTTPException(status_code=404, detail="Database not found")
    db_flavour = get_db_flavour(database.database_flavour_name)
    if not db_flavour:
        raise HTTPException(status_code=404, detail="Database flavor not found")
    
    database_service = db_flavour['class']

    database_connection = database_service.check_db_connection()

    if not database_connection:
        raise HTTPException(status_code=404, detail="Failed to connect to Database")
    
    database.allocated_size_kb += additional_storage
    db.commit()
    return {"message": f"Additional {additional_storage} bytes of storage allocated to the database"}

@router.get("/databases/")
@authenticate
def get_user_databases(access_token:Annotated[str | None, Header()] = None , db: Session = Depends(get_db)):

  current_user = get_current_user(access_token)

  user_databases = db.query(Database).filter(Database.owner_id == current_user['id']).all()
  if not user_databases:
    raise HTTPException(status_code=404, detail="No databases found for this user")
  return user_databases

@router.get("/databases/mysql")
@authenticate
def get_user_mysql_databases(access_token:Annotated[str | None, Header()] = None , db: Session = Depends(get_db)):
  
  current_user = get_current_user(access_token)

  user_databases = db.query(Database).filter(Database.owner_id == current_user["id"], Database.database_flavour_name == "mysql").all()
  if not user_databases:
    raise HTTPException(status_code=404, detail="No mysql databases found for you")
  return user_databases

@router.get("/databases/postgres")
@authenticate
def get_user_postgres_databases(access_token:Annotated[str | None, Header()] = None , db: Session = Depends(get_db)):
  
  current_user = get_current_user(access_token)

  user_databases = db.query(Database).filter(Database.owner_id == current_user['id'], Database.database_flavour_name == "postgres").all()
  if not user_databases:
    raise HTTPException(status_code=404, detail="No databases found for you")
  return user_databases

@router.post("/databases/{database_id}/user_enable")
@authenticate
def enable_user_database(database_id:str, access_token:Annotated[str | None, Header()] = None ,db: Session = Depends(get_db)):
  database = db.query(Database).filter(Database.id == database_id).first()
  if database is None:
    raise HTTPException(status_code=404, detail="Databases not found")
  
  if (database.disabled == False):
    raise HTTPException(status_code=404, detail="Databases is already enabled.")
  
  if database.admin_disabled:
    return {'You are not authorised to enable Database with id {database_id}, please contact an admin'}, 403
  
  database.disabled = False
  db.commit()
  return {"message": "Database enabled successfully"}


@router.post("/databases/{database_id}/user_disable")
@authenticate
def disable_user_database(database_id:str, access_token:Annotated[str | None, Header()] = None,  db: Session = Depends(get_db)):
  database = db.query(Database).filter(Database.id == database_id).first()
  if database is None:
    raise HTTPException(status_code=404, detail="Databases not found")
  
  if database.disabled:
    raise HTTPException(status_code=404, detail="Databases is already disabled.")
  
  if database.admin_disabled:
    return {'Database with id {database_id} is disabled, please contact an admin'}, 403
  
  database.disabled = True
  db.commit()
  return {"message": "Database disabled successfully"}
