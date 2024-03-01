from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schema import (DatabaseSchema, PasswordUpdate)
from app.models import Database
from app.core.config import get_db
from typing import List
from app.core.database_service import generate_db_credentials
from app.core.database_flavor import get_db_flavour

router = APIRouter()

@router.get("/admin/databases/")
def admin_get_all_databases(db: Session = Depends(get_db)):
    databases = db.query(Database).all()
    return databases

@router.get("/admin/mysql_databases/")
def admin_get_all_mysql_databases(db: Session = Depends(get_db)):
    mysql_databases = db.query(Database).filter(Database.database_flavour_name == "mysql").all()
    return mysql_databases

@router.get("/admin/postgresql_databases/")
def admin_get_all_postgresql_databases(db: Session = Depends(get_db)):
    postgresql_databases = db.query(Database).filter(Database.database_flavour_name == "postgres").all()
    return postgresql_databases

@router.get("/admin/user_databases/{user_id}")
def get_user_databases(user_id:str, db: Session = Depends(get_db)):
  user_databases = db.query(Database).filter(Database.owner_id == user_id).first()
  if not user_databases:
    raise HTTPException(status_code=404, detail="No databases found for this user")
  return user_databases

@router.get("/admin/databases/{database_id}")
def get_single_databases(database_id:str, db: Session = Depends(get_db)):
  user_databases = db.query(Database).filter(Database.id == database_id).first()
  if not user_databases:
    raise HTTPException(status_code=404, detail="Databases not found")
  return user_databases

@router.get("/admin/databases/{database_id}/password")
def admin_get_database_password(database_id:str, db: Session = Depends(get_db)):
  db_exists = db.query(Database).filter(Database.id == database_id).first()
  if not db_exists:
    raise HTTPException(status_code=404, detail="Database not found")
  return db_exists.password

@router.post("/admin/databases/{database_id}/enable")
def admin_enable_user_database(database_id:str, db: Session = Depends(get_db)):
  database = db.query(Database).filter(Database.id == database_id).first()
  if database is None:
    raise HTTPException(status_code=404, detail="Databases not found")
  
  if (database.admin_disabled == False):
    raise HTTPException(status_code=404, detail="Databases is already enabled.")
  
  database.admin_disabled = False
  db.commit()
  return {"message": "Database enabled successfully"}


@router.post("/admin/databases/{database_id}/disable")
def admin_disable_user_database(database_id:str, db: Session = Depends(get_db)):
  database = db.query(Database).filter(Database.id == database_id).first()
  if database is None:
    raise HTTPException(status_code=404, detail="Databases not found")
  
  if database.admin_disabled:
    raise HTTPException(status_code=404, detail="Databases is already disabled.")
  
  database.admin_disabled = True
  db.commit()
  return {"message": "Database disabled successfully"}

@router.delete("/admin/databases/{database_id}")
def delete_user_database(database_id:str, db: Session = Depends(get_db)):
  database = db.query(Database).filter(Database.id == database_id).first()
  if database is None:
    raise HTTPException(status_code=404, detail="Databases not found")
  db.delete(database)
  db.commit()
  return {"message": "Database deleted successfully"}

@router.post("/admin/databases/{database_id}/reset")
def reset_user_database(database_id:str, db: Session = Depends(get_db)):
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

@router.post("/admin/databases/{database_id}/reset_password")
def admin_password_reset_database(database_id:str, field_update:PasswordUpdate, db: Session = Depends(get_db)):
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