import os
from fastapi import HTTPException
from types import SimpleNamespace
from app.helpers.database_service import MysqlDbService, PostgresqlDbService
from config import settings
from datetime import datetime
from app.models import Database
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.helpers.logger import send_log_message, send_async_log_message

graph_filter_datat = {
  'start': '2018-01-01',
  'end': datetime.now().strftime('%Y-%m-%d'),
  'set_by': 'month'
}

db_flavors = {
    'postgres': {
        'name': 'postgres',
        'image': 'postgres:10.8-alpine',
        'port': 5432
    },
    'mysql': {
        'name': 'mysql',
        'image': 'mysql:8.0',
        'port': 3306
    },
    'mariadb': {
        'name': 'mariadb',
        'image': 'mariadb:10.5',
        'port': 3306
    }
}

# Database flavours
database_flavours = [
    {
        'name': 'mysql',
        'host': settings.ADMIN_MYSQL_HOST,
        'port': settings.ADMIN_MYSQL_PORT,
        'class': MysqlDbService()
    },
    {
        'name': 'postgres',
        'host': settings.ADMIN_PSQL_HOST,
        'port': settings.ADMIN_PSQL_PORT,
        'class': PostgresqlDbService()
    }
]


def get_db_flavour(flavour_name=None):
    if flavour_name == 'mysql':
        return database_flavours[0]
    elif flavour_name == 'postgres':
        return database_flavours[1]
    else:
        return False


def get_all_db_flavours():
    return database_flavours

def disable_database(database: Database, db: Session, is_admin=False):
    if database.disabled:
        return SimpleNamespace(
            message="Database is already disabled",
            status_code=409
        )

    # get connection
    db_flavour = get_db_flavour(database.database_flavour_name)
    database_service = db_flavour['class']
    database_connection = database_service.check_db_connection()

    if not database_connection:
        return SimpleNamespace(
            message="Failed to connect to the database service",
            status_code=500
        )

    if (db_flavour['name'] == 'postgres'):

        disable_database = database_service.disable_user_log_in(
            database.user)
        
    else :
        disable_database = database_service.disable_user_log_in(
            database.user , database.password)

    if not disable_database:
        return SimpleNamespace(
            message="Unable to disable database",
            status_code=500
        )
    try:
        database.disabled = True
        if is_admin:
            database.admin_disabled = True
        db.commit()
        return True
    except Exception as err:
        return SimpleNamespace(
            message=str(err),
            status_code=500
        )


def enable_database(database: Database, db: Session):
    if not database.disabled:
        return SimpleNamespace(
            message="Database is not disabled",
            status_code=409
        )

    # get connection
    db_flavour = get_db_flavour(database.database_flavour_name)
    database_service = db_flavour['class']
    database_connection = database_service.check_db_connection()

    if not database_connection:
        return SimpleNamespace(
            message="Failed to connect to the database service",
            status_code=500
        )

    # Enable the postgres databases

    if (db_flavour['name'] == 'postgres'):
        enable_database = database_service.enable_user_log_in(
            database.user)
    else :
        enable_database = database_service.enable_user_log_in(
            database.user , database.password)

    if not enable_database:
        return SimpleNamespace(
            message="Unable to enable database",
            status_code=500
        )
    try:
        database.disabled = False
        database.admin_disabled = False
        db.commit()
        return True
    except Exception as err:
        return SimpleNamespace(
            message=str(err),
            status_code=500
        )

def revoke_database(database: Database):
    # get connection
    db_flavour = get_db_flavour(database.database_flavour_name)
    database_service = db_flavour['class']
    database_connection = database_service.check_db_connection()

    if not database_connection:
        return SimpleNamespace(
            message="Failed to connect to the database service",
            status_code=500
        )

    if (db_flavour['name'] == 'postgres'):
        revoke_database = database_service.disable_user_access(
            database.name, database.user)
    else :
        revoke_database = database_service.disable_user_access(
            database.name, database.user)

    if not revoke_database:
        return SimpleNamespace(
            message="Unable to revoke database",
            status_code=500
        )
    
    return True

def undo_database_revoke(database: Database):
    # get connection
    db_flavour = get_db_flavour(database.database_flavour_name)
    database_service = db_flavour['class']
    database_connection = database_service.check_db_connection()

    if not database_connection:
        return SimpleNamespace(
            message="Failed to connect to the database service",
            status_code=500
        )

    if (db_flavour['name'] == 'postgres'):
        revoke_database = database_service.enable_user_write_access(
            database.name, database.user)
    else :
        revoke_database = database_service.enable_user_write_access(
            database.name, database.user)

    if not revoke_database:
        return SimpleNamespace(
            message="Unable to revoke database",
            status_code=500
        )
    
    return True
    
def failed_database_connection(current_user, operation):
    log_data = {
        "operation": operation,
        "status": "Failed",
        "user_id": current_user["id"],
        "user_email": current_user["email"],
        "model": "Database",
        "description": "Failed to connect to this database"
    }
    send_async_log_message(log_data)
    return SimpleNamespace(
        status_code=500,
        message="Failed to connect to the database service"
    )

def database_not_found(current_user, operation, database_id):
    log_data = {
        "operation": operation,
        "status": "Failed",
        "user_id": current_user["id"],
        "model":"Database",
        "description":f"Failed to get Database with ID: {database_id}"
    }
    send_async_log_message(log_data)
    raise HTTPException(status_code=404, detail="Database not found")

def save_to_database(db):
    try:
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save to the database") from e
