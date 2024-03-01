from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schema import (DatabaseSchema, DatabaseFlavor, PasswordUpdate)
import os
import json
from app.core.config import get_db
from app.core.database_service import generate_db_credentials
from app.core.database_flavor import get_db_flavour
from app.models import Database

router = APIRouter()

@router.post("/database")
async def create_database(database: DatabaseFlavor, db: Session = Depends(get_db)):

  credentials = generate_db_credentials()
  db_flavor = get_db_flavour(database.database_flavour_name)

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
      owner_id='e2611d4c-51dd-463a-9d90-8f489623f46e'
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

  database = Database(**new_database_info)
  db.add(database)
  db.commit()
  db.refresh(database)
  return dict(
      status='success',
      data=database
  ), 201

# @router.get("/admin/postgresql_databases/")
# def get_all_postgresql_databases(db: Session = Depends(get_db)):
#     postgresql_databases = db.query(Database).filter(Database.database_flavour_name == "postgres").all()
#     return postgresql_databases

@router.get("/user/databases")
def get_user_databases(user_id:str, db: Session = Depends(get_db)):
  user_databases = db.query(Database).filter(Database.owner_id == user_id).all()
  if not user_databases:
    raise HTTPException(status_code=404, detail="No databases found for this user")
  return user_databases

@router.get("/user/databases/mysql")
def get_user_mysql_databases(user_id:str, db: Session = Depends(get_db)):
  user_databases = db.query(Database).filter(Database.owner_id == user_id, Database.database_flavour_name == "mysql").all()
  if not user_databases:
    raise HTTPException(status_code=404, detail="No mysql databases found for you")
  return user_databases

@router.get("/user/databases/postgres")
def get_user_postgres_databases(user_id:str, db: Session = Depends(get_db)):
  user_databases = db.query(Database).filter(Database.owner_id == user_id, Database.database_flavour_name == "postgres").all()
  if not user_databases:
    raise HTTPException(status_code=404, detail="No databases found for you")
  return user_databases

@router.get("/user/databases/{database_id}")
def get_one_databases(database_id:str, db: Session = Depends(get_db)):
  user_databases = db.query(Database).filter(Database.id == database_id).first()
  if not user_databases:
    raise HTTPException(status_code=404, detail="Databases not found")
  return user_databases

@router.get("/user/databases/{database_id}/password")
def get_database_password(database_id:str, db: Session = Depends(get_db)):
  db_exists = db.query(Database).filter(Database.id == database_id).first()
  if not db_exists:
    raise HTTPException(status_code=404, detail="Database not found")
  return db_exists.password

@router.delete("/user/databases/{database_id}")
def delete_user_database(database_id:str, db: Session = Depends(get_db)):
  database = db.query(Database).filter(Database.id == database_id).first()
  if database is None:
    raise HTTPException(status_code=404, detail="Databases not found")
  database.deleted = True
  db.commit()
  return {"message": "Database deleted successfully"}

@router.post("/user/databases/{database_id}/enable")
def enable_user_database(database_id:str, db: Session = Depends(get_db)):
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


@router.post("/user/databases/{database_id}/disable")
def disable_user_database(database_id:str, db: Session = Depends(get_db)):
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

@router.post("/user/databases/{database_id}/reset/")
def reset_database(database_id:str, db: Session = Depends(get_db)):
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

@router.post("/user/databases/{database_id}/reset_password")
def password_reset_database(database_id:str, field_update:PasswordUpdate, db: Session = Depends(get_db)):
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

@router.post("/user/databases")
async def create_database(database: DatabaseFlavor, db: Session = Depends(get_db)):

  credentials = generate_db_credentials()
  db_flavor = get_db_flavour(database.database_flavour_name)

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
      owner_id='e2611d4c-51dd-463a-9d90-8f489623f46e'
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


