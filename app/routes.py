from fastapi import APIRouter, Depends, HTTPException, Header, Request, Query
from app.schema import (DatabaseSchema, DatabaseFlavor, PasswordUpdate)
from app.models import Database
from sqlalchemy.orm import Session
from app.helpers.database_session import get_db
from typing import List, Optional
from fastapi.responses import JSONResponse
import requests
import os
import json
from app.helpers.database_service import generate_db_credentials
from app.helpers.database_flavor import get_db_flavour
from app.helpers.logger import send_log_message, log_response, send_async_log_message
from typing import Annotated

from functools import wraps
#from fastapi import FastAPI, Header
from app.helpers.decorators import admin_or_user_required , authenticate
from app.helpers.auth import get_current_user




router = APIRouter()

@router.get("/databases")
# @authenticate
# @admin_or_user_required
def get_all_databases(access_token:Annotated[str | None, Header()] = None , db: Session = Depends(get_db)):
    user_role, user_id = get_current_user(access_token)
    if user_role == "administrator":
        databases = db.query(Database).all()
    else:
        databases = db.query(Database).filter(Database.owner_id == user_id).all()

    log_data = {
      "operation": "GET",
      "status": "Success",
      "user_id": user_id,
      "model":"Database",
      "description":"Databases successfully fetched."
    }
    send_async_log_message(log_data)
    return databases

@router.post("/databases")
def create_database(database: DatabaseFlavor, access_token:Annotated[str | None, Header()] = None , db: Session = Depends(get_db)):

  credentials = generate_db_credentials()
  db_flavor = get_db_flavour(database.database_flavour_name)
  user_role, user_id = get_current_user(access_token)

  if not db_flavor:
    log_data = {
      "operation": "Create",
      "status": "Failed",
      "user_id": user_id,
      "url": "/databases",
      "model":"Database",
      "description":"Wrong database flavour name"
    }
    send_async_log_message(log_data)
    return dict(
      status="fail",
      message=f"Database flavour with name {database.database_flavour_name} is not mysql or postgres."
    ), 404
  
  existing_name = db.query(Database).filter(Database.name == credentials.name).first()
  if existing_name:
    log_data = {
      "operation": "Create",
      "status": "Failed",
      "user_id": user_id,
      "model":"Database",
      "description":"Database with this name already exists"
    }
    send_async_log_message(log_data)
    raise HTTPException(status_code=400, detail="Database with this name already exists")
  
  existing_user = db.query(Database).filter(Database.user == credentials.user).first()
  if existing_user:
    log_data = {
      "operation": "Create",
      "status": "Failed",
      "user_id": user_id,
      "model":"Database",
      "description":"Database with this user already exists"
    }
    send_async_log_message(log_data)
    raise HTTPException(status_code=400, detail="Database with this user already exists")

  
  new_database_info = dict(
      user=credentials.user,
      password=credentials.password,
      name=credentials.name,
      database_flavour_name=database.database_flavour_name,
      host=db_flavor['host'],
      port=db_flavor['port'],
      owner_id= user_id
  )

  try:
    new_db = DatabaseSchema(**new_database_info)

  except ValueError as e:
    return {"error": f"Validation failed: {str(e)}", "status_code": 400}
  
  
  database_service = db_flavor['class']
  database_connection = database_service.check_db_connection()

  if not database_connection:
    log_data = {
      "operation": "Create",
      "status": "Failed",
      "user_id": user_id,
      "model":"Database",
      "description":"Failed to connect to this database"
    }
    send_async_log_message(log_data)
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
    log_data = {
      "operation": "Create",
      "status": "Failed",
      "user_id": user_id,
      "model":"Database",
      "description":"Failed to create database"
    }
    send_async_log_message(log_data)
    return dict(
        status="fail",
        message=f"Unable to create database"
    ), 500

  database = Database(**new_database_info)
  db.add(database)
  db.commit()
  db.refresh(database)
  log_data = {
    "operation": "Create",
    "status": "Success",
    "user_id": user_id,
    "model":"Database",
    "description":"Database successfully created."
  }
  send_async_log_message(log_data)
  return {
      "status":'success',
      "data":database
  }


@router.get("/databases/mysql")
def get_mysql_databases(access_token:Annotated[str | None, Header()] = None ,db: Session = Depends(get_db)):
    user_role, user_id = get_current_user(access_token)
    if user_role == "administrator":
        databases = db.query(Database).filter(Database.database_flavour_name == "mysql").all()
    else:
        databases = db.query(Database).filter(Database.owner_id == user_id, Database.database_flavour_name == "mysql").all()

    log_data = {
      "operation": "GET",
      "status": "Success",
      "user_id": user_id,
      "model":"Database",
      "description":"MYSQL Databases successfully fetched."
    }
    send_async_log_message(log_data)
    return databases

@router.get("/databases/postgresql")
def get_postgresql_databases(access_token:Annotated[str | None, Header()] = None ,db: Session = Depends(get_db)):
    user_role, user_id = get_current_user(access_token)
    if user_role == "administrator":
        databases = db.query(Database).filter(Database.database_flavour_name == "postgres").all()
    else:
        databases = db.query(Database).filter(Database.owner_id == user_id, Database.database_flavour_name == "postgres").all()
    log_data = {
      "operation": "GET",
      "status": "Success",
      "user_id": user_id,
      "model":"Database",
      "description":"Postgresql Databases successfully fetched."
    }
    send_async_log_message(log_data)
    return databases

@router.get("/databases/{database_id}")
def single_database(database_id:str, access_token:Annotated[str | None, Header()] = None ,db: Session = Depends(get_db)):
  user_role, user_id = get_current_user(access_token)
  user_database = db.query(Database).filter(Database.id == database_id).first()
  if not user_database:
    log_data = {
      "operation": "GET",
      "status": "Failed",
      "user_id": user_id,
      "model":"Database",
      "description":f"Failed to get Database with ID: {user_database.id}"
    }
    send_async_log_message(log_data)
    raise HTTPException(status_code=404, detail="Databases not found")
  log_data = {
    "operation": "Get",
    "status": "Success",
    "user_id": user_id,
    "model":"Database",
    "description":f"Fetch single Database {user_database.id}"
  }
  send_async_log_message(log_data)
  return user_database

@router.get("/databases/{database_id}/password")
def get_database_password(database_id:str, access_token:Annotated[str | None, Header()] = None ,db: Session = Depends(get_db)):
  user_role, user_id = get_current_user(access_token)
  db_exists = db.query(Database).filter(Database.id == database_id).first()
  if not db_exists:
    log_data = {
      "operation": "GET PASSWORD",
      "status": "Failed",
      "user_id": user_id,
      "model":"Database",
      "description":f"Failed to get Database with ID: {db_exists.id}"
    }
    send_async_log_message(log_data)
    raise HTTPException(status_code=404, detail="Database not found")
  log_data = {
    "operation": "Get",
    "status": "Success",
    "user_id": user_id,
    "model":"Database",
    "description":f"Get Database password for database: {db_exists.id}"
  }
  send_async_log_message(log_data)
  return db_exists.password

@router.post("/databases/{database_id}/enable")
def enable_database(database_id:str,access_token:Annotated[str | None, Header()] = None , db: Session = Depends(get_db)):
  user_role, user_id = get_current_user(access_token)
  database = db.query(Database).filter(Database.id == database_id).first()
  if database is None:
    log_data = {
      "operation": "DATABASE ENABLE",
      "status": "Failed",
      "user_id": user_id,
      "model":"Database",
      "description":f"Failed to get Database with ID: {database.id}"
    }
    send_async_log_message(log_data)
    raise HTTPException(status_code=404, detail="Databases not found")
  if user_role == "administrator":
    if (database.admin_disabled == False):
      log_data = {
        "operation": "DATABASE ENABLE",
        "status": "Failed",
        "user_id": user_id,
        "model":"Database",
        "description":f"Database: {database.id} is already enabled."
      }
      send_async_log_message(log_data)
      raise HTTPException(status_code=404, detail="Databases is already enabled.")
    
    database.admin_disabled = False
    db.commit()
    log_data = {
      "operation": "DATABASE ENABLE",
      "status": "Success",
      "user_id": user_id,
      "model":"Database",
      "description":f"Database: {database.id} is successfully enabled."
    }
    send_async_log_message(log_data)
    return {"message": "Database enabled successfully"}
  else:
    if (database.disabled == False):
      log_data = {
        "operation": "DATABASE ENABLE",
        "status": "Failed",
        "user_id": user_id,
        "model":"Database",
        "description":f"Database: {database.id} is already enabled."
      }
      send_async_log_message(log_data)
      raise HTTPException(status_code=404, detail="Databases is already enabled.")
    
    if database.admin_disabled:
      log_data = {
        "operation": "DATABASE ENABLE",
        "status": "Failed",
        "user_id": user_id,
        "model":"Database",
        "description":f"You are not authorised to enable Database: {database.id}"
      }
      send_async_log_message(log_data)
      return {"message": f"You are not authorised to enable Database with id {database_id}, please contact an admin"}
    
    database.disabled = False
    db.commit()
    log_data = {
      "operation": "DATABASE ENABLE",
      "status": "Success",
      "user_id": user_id,
      "model":"Database",
      "description":f"Database: {database.id} is successfully enabled."
    }
    send_async_log_message(log_data)
    return {"message": "Database enabled successfully"}


@router.post("/databases/{database_id}/disable")
def disable_database(database_id:str, access_token:Annotated[str | None, Header()] = None ,db: Session = Depends(get_db)):
  user_role, user_id = get_current_user(access_token)
  database = db.query(Database).filter(Database.id == database_id).first()
  if database is None:
    log_data = {
      "operation": "DATABASE DISABLE",
      "status": "Failed",
      "user_id": user_id,
      "model":"Database",
      "description":f"Failed to get Database with ID: {database.id}"
    }
    send_async_log_message(log_data)
    raise HTTPException(status_code=404, detail="Databases not found")
  if user_role == "administrator":
    if database.admin_disabled:
      log_data = {
        "operation": "DATABASE DISABLE",
        "status": "Failed",
        "user_id": user_id,
        "model":"Database",
        "description":f"Database: {database.id} is already disabled."
      }
      send_async_log_message(log_data)
      raise HTTPException(status_code=404, detail="Databases is already disabled.")
    
    database.admin_disabled = True
    db.commit()
    log_data = {
      "operation": "DATABASE DISABLE",
      "status": "Success",
      "user_id": user_id,
      "model":"Database",
      "description":f"Database: {database.id} is successfully disabled."
    }
    send_async_log_message(log_data)
    return {"message": "Database disabled successfully"}
  else:
    if database.disabled:
      log_data = {
        "operation": "DATABASE DISABLE",
        "status": "Failed",
        "user_id": user_id,
        "model":"Database",
        "description":f"Database: {database.id} is already disabled."
      }
      send_async_log_message(log_data)
      raise HTTPException(status_code=404, detail="Databases is already disabled.")
    
    if database.admin_disabled:
      log_data = {
        "operation": "DATABASE DISABLE",
        "status": "Failed",
        "user_id": user_id,
        "model":"Database",
        "description":f"You are not authorised to disable Database: {database.id}"
      }
      send_async_log_message(log_data)
      return {'Database with id {database_id} is disabled, please contact an admin'}, 403
    
    database.disabled = True
    db.commit()
    log_data = {
      "operation": "DATABASE DISABLE",
      "status": "Success",
      "user_id": user_id,
      "model":"Database",
      "description":f"Database: {database.id} is successfully disabled."
    }
    send_async_log_message(log_data)
    return {"message": "Database disabled successfully"}

@router.delete("/databases/{database_id}")
def delete_database(database_id:str, access_token:Annotated[str | None, Header()] = None , db: Session = Depends(get_db)):
  user_role, user_id = get_current_user(access_token)
  database = db.query(Database).filter(Database.id == database_id).first()
  if database is None:
    log_data = {
      "operation": "DATABASE DELETE",
      "status": "Failed",
      "user_id": user_id,
      "model":"Database",
      "description":f"Failed to get Database with ID: {database.id}"
    }
    send_async_log_message(log_data)
    raise HTTPException(status_code=404, detail="Databases not found")
  db.delete(database)
  db.commit()
  log_data = {
    "operation": "DATABASE DELETE",
    "status": "Success",
    "user_id": user_id,
    "model":"Database",
    "description":f"Database: {database.id} is successfully deleted."
  }
  send_async_log_message(log_data)
  return {"message": "Database deleted successfully"}

@router.post("/databases/{database_id}/reset")
@authenticate
def reset_database(database_id:str, access_token:Annotated[str | None, Header()] = None , db: Session = Depends(get_db)):
  user_role, user_id = get_current_user(access_token)
  database = db.query(Database).filter(Database.id == database_id).first()
  if database is None:
    log_data = {
      "operation": "DATABASE RESET",
      "status": "Failed",
      "user_id": user_id,
      "model":"Database",
      "description":f"Failed to get Database with ID: {database.id}"
    }
    send_async_log_message(log_data)
    raise HTTPException(status_code=404, detail="Database not found")

  db_flavour = get_db_flavour(database.database_flavour_name)

  if not db_flavour:
    log_data = {
      "operation": "RESET",
      "status": "Failed",
      "user_id": user_id,
      "url": "/databases",
      "model":"Database",
      "description":"Wrong database flavour name"
    }
    send_async_log_message(log_data)
    return dict(
        status="fail",
        message=f"Database with flavour name {database.database_flavour_name} is not mysql or postgres."
    ), 409

  database_service = db_flavour['class']

  database_connection = database_service.check_db_connection()

  if not database_connection:
    log_data = {
      "operation": "RESET",
      "status": "Failed",
      "user_id": user_id,
      "model":"Database",
      "description":"Failed to connect to this database"
    }
    send_async_log_message(log_data)
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
    log_data = {
      "operation": "RESET",
      "status": "Failed",
      "user_id": user_id,
      "model":"Database",
      "description":f"Failed to reset database: {database.id}"
    }
    send_async_log_message(log_data)
    return dict(
        status="fail",
        message=f"Unable to reset database"
    ), 500
  log_data = {
    "operation": "DATABASE RESET",
    "status": "Success",
    "user_id": user_id,
    "model":"Database",
    "description":f"Database: {database.id} is successfully reset."
  }
  send_async_log_message(log_data)
  return ({"status":'success', "message":"Database Reset Successfully"}), 200

@router.post("/databases/{database_id}/reset_password")
@authenticate
def password_reset_database(database_id:str, field_update:PasswordUpdate, access_token:Annotated[str | None, Header()] = None , db: Session = Depends(get_db)):
  user_role, user_id = get_current_user(access_token)
  database = db.query(Database).filter(Database.id == database_id).first()
  if not database:
    log_data = {
      "operation": "RESET PASSWORD",
      "status": "Failed",
      "user_id": user_id,
      "model":"Database",
      "description":f"Failed to get Database with ID: {database.id}"
    }
    send_async_log_message(log_data)
    raise HTTPException(status_code=404, detail="Databases not found")

  db_flavour = get_db_flavour(database.database_flavour_name)

  if not db_flavour:
    log_data = {
      "operation": "RESET PASSWORD",
      "status": "Failed",
      "user_id": user_id,
      "model":"Database",
      "description":"Wrong database flavour name"
    }
    send_async_log_message(log_data)
    return dict(
        status="fail",
        message=f"Database with flavour name {database.database_flavour_name} is not mysql or postgres."
    ), 409

  database_service = db_flavour['class']

  database_connection = database_service.check_db_connection()

  if not database_connection:
    log_data = {
      "operation": "RESET PASSWORD",
      "status": "Failed",
      "user_id": user_id,
      "model":"Database",
      "description":"Failed to connect to this database"
    }
    send_async_log_message(log_data)
    return dict(
        status="fail",
        message=f"Failed to connect to the database service"
    ), 500

  password_reset_database = database_service.reset_password(
    
    user=database.user,
    password= field_update.password
  )

  if not password_reset_database:
    log_data = {
      "operation": "RESET PASSWORD",
      "status": "Failed",
      "user_id": user_id,
      "model":"Database",
      "description":f"Failed to reset database passsword for: {database.id}"
    }
    send_async_log_message(log_data)
    return dict(
        status="fail",
        message=f"Unable to reset database password"
    ), 500
  
  database.password = field_update.password

  db.commit()
  log_data = {
    "operation": "DATABASE PASSWORD RESET",
    "status": "Success",
    "user_id": user_id,
    "model":"Database",
    "description":f"Database: {database.id} password is successfully reset."
  }
  send_async_log_message(log_data)
  return ({"status":'success', "message":"Database Password Reset Successfully"}), 200


@router.patch("/database/{database_id}/storage")
def allocate_storage(database_id: str, additional_storage: int, access_token:Annotated[str | None, Header()] = None , db: Session = Depends(get_db)):
    user_role, user_id = get_current_user(access_token)
    database = db.query(Database).filter(Database.id == database_id).first()
    if not database:
        log_data = {
          "operation": "ADD STORAGE",
          "status": "Failed",
          "user_id": user_id,
          "model":"Database",
          "description":f"Failed to get Database with ID: {database.id}"
        }
        send_async_log_message(log_data)
        raise HTTPException(status_code=404, detail="Database not found")
    db_flavour = get_db_flavour(database.database_flavour_name)
    if not db_flavour:
        raise HTTPException(status_code=404, detail="Database flavor not found")
    
    database_service = db_flavour['class']

    database_connection = database_service.check_db_connection()

    if not database_connection:
        log_data = {
          "operation": "RESET",
          "status": "Failed",
          "user_id": user_id,
          "model":"Database",
          "description":"Failed to connect to this database"
        }
        send_async_log_message(log_data)
        raise HTTPException(status_code=404, detail="Failed to connect to Database")
    
    database.allocated_size_kb += additional_storage
    db.commit()
    return {"message": f"Additional {additional_storage} bytes of storage allocated to the database"}
