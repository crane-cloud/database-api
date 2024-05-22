from fastapi import APIRouter, Depends, HTTPException, Header, Query, security
from app.schema import (DatabaseSchema, DatabaseFlavor, PasswordUpdate)
from app.models import Database
from sqlalchemy.orm import Session
from sqlalchemy import func, column, cast, Date
from app.helpers.database_session import get_db
from typing import Optional
from fastapi.responses import JSONResponse
from app.helpers.database_service import generate_db_credentials, MysqlDbService
from app.helpers.database_flavor import disable_database_flavour, enable_database_flavour, get_db_flavour, database_flavours, graph_filter_datat, undo_database_revoke, revoke_database, failed_database_connection, database_not_found, save_to_database
from app.helpers.logger import send_async_log_message
from typing import Annotated
from datetime import datetime
from types import SimpleNamespace
from app.helpers.decorators import authenticate
from app.helpers.auth import get_current_user, check_authentication
from fastapi.security import HTTPBearer

router = APIRouter()
security = HTTPBearer()


@router.get("/databases/stats")
def fetch_database_stats(access_token: str = Depends(security), db: Session = Depends(get_db)):
    current_user = get_current_user(access_token.credentials)
    check_authentication(current_user)

    dbs_per_flavour = {}
    total = 0

    for flavour in database_flavours:
        databases = db.query(Database).filter_by(
            database_flavour_name=flavour['name']).all()

        database_count = len(databases)
        dbs_per_flavour[f"{flavour['name']}_db_count"] = database_count

        total = total + database_count

    data = dict(total_database_count=total,
                dbs_stats_per_flavour=dbs_per_flavour)

    return SimpleNamespace(status_code=200,
                           data=dict(databases=data))


@router.get("/databases")
def get_all_databases(access_token: str = Depends(security), db: Session = Depends(get_db)):
    current_user = get_current_user(access_token.credentials)
    check_authentication(current_user)

    if current_user.role == "administrator":
        databases = db.query(Database).all()
    else:
        databases = db.query(Database).filter(
            Database.owner_id == current_user.id).all()

    database_list = []

    for user_database in databases:
        try:
            flavour_name = user_database.database_flavour_name
            if not flavour_name:
                flavour_name = "mysql"

            db_flavour = get_db_flavour(flavour_name)

            if not db_flavour:
                return dict(
                    status_code=404,
                    message=f"""Database flavour with name
                        {user_database.database_flavour_name} is not mysql or postgres."""
                )

            database_service = db_flavour['class']

            # Get db status
            database_connection = database_service.create_db_connection(
                user=user_database.user, password=user_database.password, db_name=user_database.name)
            db_status = database_connection is not None

        except Exception as e:
            print(f"Error connecting to database {user_database.name}: {e}")
            db_status = False
        finally:
            if database_connection:
                if database_service == MysqlDbService():
                    if database_connection.is_connected():
                        database_connection.close()
                    else:
                        database_connection.close()

        database_dict = {
            **user_database.__dict__,
            "db_status": db_status,
            "default_storage_kb": database_service.get_database_size(
                user=user_database.user, password=user_database.password, db_name=user_database.name)
        }

        database_list.append(database_dict)

    return {"status_code": 200, "data": {"databases": database_list}}


@router.post("/databases")
def create_database(database: DatabaseFlavor, access_token: str = Depends(security), db: Session = Depends(get_db)):
    credentials = generate_db_credentials()
    db_flavor = get_db_flavour(database.database_flavour_name)

    current_user = get_current_user(access_token.credentials)
    check_authentication(current_user)

    existing_name = db.query(Database).filter(
        Database.name == credentials.name).first()
    if existing_name:
        log_data = {
            "operation": "Create",
            "status": "Failed",
            "user_id": current_user.id,
            "model": "Database",
            "description": "Database with this name already exists"
        }
        send_async_log_message(log_data)
        raise HTTPException(
            status_code=400, message="Database with this name already exists")

    new_database_info = dict(
        user=credentials.user,
        password=credentials.password,
        name=credentials.name,
        database_flavour_name=database.database_flavour_name,
        host=db_flavor['host'],
        port=db_flavor['port'],
        owner_id=current_user.id,
        email=current_user.email
    )

    try:
        new_db = DatabaseSchema(**new_database_info)
    except ValueError as e:
        return {"error": f"Validation failed: {str(e)}", "status_code": 409}

    database_service = db_flavor['class']
    database_connection = database_service.check_db_connection()

    if not database_connection:
        return failed_database_connection(current_user, "CREATE")

    create_database = database_service.create_database(
        db_name=credentials.name,
        user=credentials.user,
        password=credentials.password
    )

    if not create_database:
        log_data = {
            "operation": "Create",
            "status": "Failed",
            "user_id": current_user.id,
            "user_email": current_user.email,
            "model": "Database",
            "description": "Failed to create database"
        }
        send_async_log_message(log_data)
        return dict(
            status_code=500,
            message=f"Unable to create database"
        )

    database = Database(**new_database_info)
    db.add(database)
    save_to_database(db)
    db.refresh(database)
    log_data = {
        "operation": "Create",
        "status": "Success",
        "user_id": current_user.id,
        "user_email": current_user.email,
        "model": "Database",
        "description": "Database successfully created."
    }
    send_async_log_message(log_data)

    return SimpleNamespace(status_code=201, data={"database": database})


@router.get("/databases/{database_id}")
def single_database(database_id: str, access_token: str = Depends(security), db: Session = Depends(get_db)):
    current_user = get_current_user(access_token.credentials)
    check_authentication(current_user)

    user_database = db.query(Database).filter(
        Database.id == database_id).first()
    if not user_database:
        raise HTTPException(status_code=404, detail="Database not found")

    flavour_name = user_database.database_flavour_name
    if not flavour_name:
        flavour_name = "mysql"

    db_flavour = get_db_flavour(flavour_name)

    if not db_flavour:
        return dict(
            status_code=404,
            message=f"""Database flavour with name
                {user_database.database_flavour_name} is not mysql or postgres."""
        )

    database_service = db_flavour['class']

    # Get db status
    try:
        database_connection = database_service.create_db_connection(
            user=user_database.user, password=user_database.password, db_name=user_database.name)
        if not database_connection:
            db_status = False
        else:
            db_status = True
    except:
        db_status = False
    finally:
        if database_connection:
            if database_service == MysqlDbService():
                if database_connection.is_connected():
                    database_connection.close()
                else:
                    database_connection.close()

    database_dict = {
        **user_database.__dict__,
        "db_status": db_status,
        "default_storage_kb": database_service.get_database_size(
            user=user_database.user, password=user_database.password, db_name=user_database.name)
    }

    return SimpleNamespace(status_code=200, data={"database": database_dict})


@router.get("/databases/{database_id}/password")
def get_database_password(database_id: str, access_token: str = Depends(security), db: Session = Depends(get_db)):
    current_user = get_current_user(access_token.credentials)
    check_authentication(current_user)

    db_exists = db.query(Database).filter(Database.id == database_id).first()
    if not db_exists:
        raise HTTPException(
            status_code=404, detail=f"Database with ID {database_id} not found")
    return SimpleNamespace(status_code=200, data={"database": {"password": db_exists.password}})


@router.post("/databases/{database_id}/enable")
def enable_database(database_id: str, access_token: str = Depends(security), db: Session = Depends(get_db)):
    current_user = get_current_user(access_token.credentials)
    check_authentication(current_user)

    database = db.query(Database).filter(Database.id == database_id).first()
    if not database:
        database_not_found(current_user, "Enable", database.id)
    if current_user.role == "administrator":
        if not database.admin_disabled:
            raise HTTPException(
                status_code=409, detail="Database is already enabled.")

        enabled_database = enable_database_flavour(database, db)
        if type(enabled_database) == SimpleNamespace:
            status_code = enabled_database.status_code if enabled_database.status_code else 500
            log_data = {
                "operation": "DATABASE ENABLE",
                "status": "Failed",
                "user_id": current_user.id,
                "user_email": current_user.email,
                "model": "Database",
                "description": f"Database: {database.id} is {enabled_database.message}."
            }
            send_async_log_message(log_data)
            return dict(status_code=status_code, message=enabled_database.message)
        log_data = {
            "operation": "DATABASE ENABLE",
            "status": "Success",
            "user_id": current_user.id,
            "user_email": current_user.email,
            "model": "Database",
            "description": f"Database: {database.id} is successfully enabled."
        }
        send_async_log_message(log_data)
        return {"status_code": 200, "message": "Database enabled successfully"}
    else:
        if not database.disabled:
            raise HTTPException(
                status_code=404, detail="Databases is already enabled.")

        if database.admin_disabled:
            log_data = {
                "operation": "DATABASE ENABLE",
                "status": "Failed",
                "user_id": current_user.id,
                "user_email": current_user.email,
                "model": "Database",
                "description": f"You are not authorised to enable Database: {database.id}"
            }
            send_async_log_message(log_data)
            return {"message": f"You are not authorised to enable Database with id {database_id}, please contact an admin", "status_code": 403}

        enabled_database = enable_database_flavour(database, db)
        if type(enabled_database) == SimpleNamespace:
            status_code = enabled_database.status_code if enabled_database.status_code else 500
            log_data = {
                "operation": "DATABASE ENABLE",
                "status": "Failed",
                "user_id": current_user.id,
                "user_email": current_user.email,
                "model": "Database",
                "description": f"Database: {database.id} is {enabled_database.message}."
            }
            send_async_log_message(log_data)
            return dict(status_code=status_code, message=enabled_database.message)

        log_data = {
            "operation": "DATABASE ENABLE",
            "status": "Success",
            "user_id": current_user.id,
            "user_email": current_user.email,
            "model": "Database",
            "description": f"Database: {database.id} is successfully enabled."
        }
        send_async_log_message(log_data)
        return {"status_code": 200, "message": "Database enabled successfully"}


@router.post("/databases/{database_id}/disable")
def disable_database(database_id: str, access_token: str = Depends(security), db: Session = Depends(get_db)):
    current_user = get_current_user(access_token.credentials)
    check_authentication(current_user)

    database = db.query(Database).filter(Database.id == database_id).first()

    if not database:
        database_not_found(current_user, "Disable", database.id)

    if current_user.role == "administrator":

        if database.admin_disabled:
            raise HTTPException(
                status_code=404, detail="Databases is already disabled.")

        disbled_database = disable_database_flavour(database, db, True)
        if type(disbled_database) == SimpleNamespace:
            status_code = disbled_database.status_code if disbled_database.status_code else 500
            log_data = {
                "operation": "DATABASE ENABLE",
                "status": "Failed",
                "user_id": current_user.id,
                "user_email": current_user.email,
                "model": "Database",
                "description": f"Database: {database.id} is {disbled_database.message}."
            }
            send_async_log_message(log_data)
            return dict(status_code=status_code, message=disbled_database.message)
        log_data = {
            "operation": "DATABASE DISABLE",
            "status": "Success",
            "user_id": current_user.id,
            "user_email": current_user.email,
            "model": "Database",
            "description": f"Database: {database.id} is successfully disabled."
        }
        send_async_log_message(log_data)
        return {"message": "Database disabled successfully", "status_code": 200}
    else:
        if database.disabled:
            raise HTTPException(
                status_code=404, message="Databases is already disabled.")

        if database.admin_disabled:
            log_data = {
                "operation": "DATABASE DISABLE",
                "status": "Failed",
                "user_id": current_user.id,
                "user_email": current_user.email,
                "model": "Database",
                "description": f"You are not authorised to disable Database: {database_id}"
            }
            send_async_log_message(log_data)
            return {"message": 'Database with id {database_id} is disabled, please contact an admin', "status_code": 403}

        disbled_database = disable_database_flavour(database, db, False)
        if type(disbled_database) == SimpleNamespace:
            status_code = disbled_database.status_code if disbled_database.status_code else 500
            log_data = {
                "operation": "DATABASE ENABLE",
                "status": "Failed",
                "user_id": current_user.id,
                "user_email": current_user.email,
                "model": "Database",
                "description": f"Database: {database_id} is {disbled_database.message}."
            }
            send_async_log_message(log_data)
            return dict(status_code=status_code, message=disbled_database.message)
        log_data = {
            "operation": "DATABASE DISABLE",
            "status": "Success",
            "user_id": current_user.id,
            "user_email": current_user.email,
            "model": "Database",
            "description": f"Database: {database_id} is successfully disabled."
        }
        send_async_log_message(log_data)
        return {"status_code": 200, "message": "Database disabled successfully"}


@router.delete("/databases/{database_id}")
def delete_database(database_id: str, access_token: str = Depends(security), db: Session = Depends(get_db)):
    current_user = get_current_user(access_token.credentials)
    check_authentication(current_user)

    database = db.query(Database).filter(Database.id == database_id).first()
    if database is None:
        log_data = {
            "operation": "DATABASE DELETE",
            "status": "Failed",
            "user_id": current_user.id,
            "description": f"Failed to get Database with ID: {database_id}"
        }
        send_async_log_message(log_data)
        return {"status_code": 404, "message": "Database Not Found"}

    db.delete(database)
    save_to_database(db)
    log_data = {
        "operation": "DATABASE DELETE",
        "status": "Success",
        "user_id": current_user.id,
        "description": f"Database: {database.id} is successfully deleted."
    }
    send_async_log_message(log_data)
    return {"status_code": 200, "message": "Database deleted successfully"}


@router.post("/databases/{database_id}/reset")
def reset_database(database_id: str, access_token: str = Depends(security), db: Session = Depends(get_db)):
    current_user = get_current_user(access_token.credentials)
    check_authentication(current_user)

    database = db.query(Database).filter(Database.id == database_id).first()
    if not database:
        database_not_found(current_user, "Enable", database.id)

    db_flavour = get_db_flavour(database.database_flavour_name)

    if not db_flavour:
        return dict(
            status_code=403,
            message=f"""Database with flavour name
                {database.database_flavour_name} is not mysql or postgres."""
        )

    database_service = db_flavour['class']

    database_connection = database_service.check_db_connection()

    if not database_connection:
        return failed_database_connection(current_user, "RESET")

    reset_database = database_service.reset_database(
        db_name=database.name,
        user=database.user,
        password=database.password
    )

    if not reset_database:
        log_data = {
            "operation": "RESET",
            "status": "Failed",
            "user_id": current_user.id,
            "user_email": current_user.email,
            "model": "Database",
            "description": f"Failed to reset database: {database.id}"
        }
        send_async_log_message(log_data)
        return dict(
            status=500,
            message=f"Unable to reset database"
        )

    log_data = {
        "operation": "DATABASE RESET",
        "status": "Success",
        "user_id": current_user.id,
        "user_email": current_user.email,
        "model": "Database",
        "description": f"Database: {database.id} is successfully reset."
    }
    send_async_log_message(log_data)
    return ({"status_code": 200, "message": "Database Reset Successfully"})


@router.post("/databases/{database_id}/reset_password")
def password_reset_database(database_id: str, field_update: PasswordUpdate, access_token: str = Depends(security), db: Session = Depends(get_db)):
    current_user = get_current_user(access_token.credentials)
    check_authentication(current_user)

    database = db.query(Database).filter(Database.id == database_id).first()
    if not database:
        database_not_found(current_user, "RESET PASSWORD", database.id)

    db_flavour = get_db_flavour(database.database_flavour_name)

    if not db_flavour:
        log_data = {
            "operation": "RESET PASSWORD",
            "status": "Failed",
            "user_id": current_user.id,
            "user_email": current_user.email,
            "model": "Database",
            "description": "Wrong database flavour name"
        }
        send_async_log_message(log_data)
        return dict(
            status_code=409,
            message=f"""Database with flavour name
                {database.database_flavour_name} is not mysql or postgres."""
        )

    database_service = db_flavour['class']

    database_connection = database_service.check_db_connection()

    if not database_connection:
        return failed_database_connection(current_user, "RESET PASSWORD")

    password_reset_database = database_service.reset_password(
        user=database.user,
        password=field_update.password
    )

    if not password_reset_database:
        log_data = {
            "operation": "RESET PASSWORD",
            "status": "Failed",
            "user_id": current_user.id,
            "user_email": current_user.email,
            "model": "Database",
            "description": f"Failed to reset database passsword for: {database.id}"
        }
        send_async_log_message(log_data)
        return dict(
            status_code=500,
            message=f"Unable to reset database password"
        )

    database.password = field_update.password

    save_to_database(db)
    log_data = {
        "operation": "DATABASE PASSWORD RESET",
        "status": "Success",
        "user_id": current_user.id,
        "user_email": current_user.email,
        "model": "Database",
        "description": f"Database: {database.id} password is successfully reset."
    }
    send_async_log_message(log_data)
    return ({"status_code": 200, "message": "Database Password Reset Successfully"})


@router.patch("/databases/{database_id}/storage")
def allocate_storage(database_id: str, additional_storage: int, access_token: str = Depends(security), db: Session = Depends(get_db)):
    current_user = get_current_user(access_token.credentials)
    check_authentication(current_user)

    database = db.query(Database).filter(Database.id == database_id).first()
    if not database:
        database_not_found(current_user, "Enable", database.id)
    db_flavour = get_db_flavour(database.database_flavour_name)
    if not db_flavour:
        raise HTTPException(
            status_code=404, detail="Database flavor not found")

    database_service = db_flavour['class']

    database_connection = database_service.check_db_connection()

    if not database_connection:
        return failed_database_connection(current_user, "ADD STORAGE")

    database.allocated_size_kb += additional_storage
    save_to_database(db)
    return {"message": f"Additional {additional_storage} bytes of storage allocated to the database", "status_code": 200}


@router.get("/databases/graph")
def database_graph_data(start: Optional[str] = Query(description="Start date format(YYYY-MM-DD)", default=graph_filter_datat['start']), access_token: str = Depends(security), end: Optional[str] = Query(description="End date format(YYYY-MM-DD)", default=graph_filter_datat['end']), set_by: Optional[str] = Query(description="Either month or year", default=graph_filter_datat['set_by']), db_flavour: Optional[str] = Query(None, description="Database flavour either mysql or postgres"), db: Session = Depends(get_db)):
    """ Shows databases graph data """
    current_user = get_current_user(access_token.credentials)
    check_authentication(current_user)

    graph_filter_data = {}
    try:
        start_date = datetime.strptime(start, '%Y-%m-%d').date()
        end_date = datetime.strptime(end, '%Y-%m-%d').date()

        if start is not None:
            graph_filter_data['start'] = start_date
        if end is not None:
            graph_filter_data['end'] = end_date
        if set_by is not None:
            if set_by not in ["year", "month"]:
                raise ValueError('set_by should be year or month')
            graph_filter_data['set_by'] = set_by
    except ValueError as e:
        log_data = {
            "operation": "Graph data",
            "status": "Failed",
            "user_id": current_user.id,
            "user_email": current_user.email,
            "model": "Database",
            "description": f"Failed due to: {e}"
        }
        send_async_log_message(log_data)
        return JSONResponse(data={'message': str(e)}, status_code=400)

    valid_flavour = None

    if db_flavour:
        valid_flavour = get_db_flavour(db_flavour)
        if not valid_flavour:
            log_data = {
                "operation": "Graph Data",
                "status": "Failed",
                "user_id": current_user.id,
                "user_email": current_user.email,
                "model": "Database",
                "description": "Wrong database flavour name"
            }
            send_async_log_message(log_data)
            return JSONResponse(data={'message': 'Not a valid database flavour use mysql or postgres'}, status_code=401)

    if set_by == 'month':
        date_list = func.generate_series(cast(start_date, Date), cast(
            end_date, Date), '1 month').alias('month')
        month = column('month')
        query = db.query(month, func.count(Database.id)).\
            select_from(date_list).\
            outerjoin(Database, func.date_trunc(
                'month', Database.date_created) == month)

        if db_flavour:
            query = query.filter(Database.database_flavour_name == db_flavour)
        db_data = query.group_by(month).order_by(month).all()

    else:
        date_list = func.generate_series(cast(start_date, Date), cast(
            end_date, Date), '1 year').alias('year')
        year = column('year')
        query = db.query(year, func.count(Database.id)).\
            select_from(date_list).\
            outerjoin(Database, func.date_trunc(
                'year', Database.date_created) == year)

        if db_flavour:
            query = query.filter(Database.database_flavour_name == db_flavour)

        db_data = query.group_by(year).order_by(year).all()

    db_info = []

    for item in db_data:
        item_dict = {
            'year': item[0].year, 'month': item[0].month, 'value': item[1]
        }
        db_info.append(item_dict)

    metadata = dict()
    query = db.query(Database)

    metadata['total'] = query.count()
    metadata['postgres_total'] = query.filter_by(
        database_flavour_name='postgres').count()
    metadata['mysql_total'] = query.filter_by(
        database_flavour_name='mysql').count()
    db_user = Database.user
    metadata['users_number'] = query.with_entities(
        db_user, func.count(db_user)).group_by(db_user).distinct().count()

    return {"status_code": 200,  'data': {'metadata': metadata, 'graph_data': db_info}}


@router.post("/databases/{database_id}/revoke_write_access")
def revoke_write_access(database_id: str, access_token: str = Depends(security), db: Session = Depends(get_db)):
    current_user = get_current_user(access_token.credentials)
    check_authentication(current_user)

    database = db.query(Database).filter(Database.id == database_id).first()
    if database is None:
        # log_data = {
        #   "operation": "DATABASE REVOKE",
        #   "status": "Failed",
        #   # "user_id": current_user.user_id,
        #   # "user_email": user_email,
        #   "model":"Database",
        #   "description":f"Failed to get Database with ID: {database.id}"
        # }
        # send_async_log_message(log_data)
        raise HTTPException(status_code=404, detail="Databases not found")

    revoked_db = revoke_database(database)
    if type(revoked_db) == SimpleNamespace:
        status_code = revoked_db.status_code if revoked_db.status_code else 500
        # log_data = {
        #   "operation": "DATABASE ENABLE",
        #   "status": "Failed",
        #   "user_id": current_user.user_id,
        #   "user_email": user_email,
        #   "model":"Database",
        #   "description":f"Database: {database.id} is {disbled_database.message}."
        # }
        # send_async_log_message(log_data)
        return dict(status_code=status_code, message=revoked_db.message)
    # log_data = {
    #   "operation": "DATABASE REVOKE",
    #   "status": "Success",
    #   "user_id": user_id,
    #   "user_email": user_email,
    #   "model":"Database",
    #   "description":f"Database: {database.id} is successfully revoked."
    # }
    # send_async_log_message(log_data)
    return {"message": "Database revoked successfully"}


@router.post("/databases/{database_id}/undo_database_revoke")
def undo_database_access_revoke(database_id: str, access_token: str = Depends(security), db: Session = Depends(get_db)):
    current_user = get_current_user(access_token.credentials)
    check_authentication(current_user)

    database = db.query(Database).filter(Database.id == database_id).first()
    if database is None:
        # log_data = {
        #   "operation": "DATABASE UNREVOKE",
        #   "status": "Failed",
        #   "user_id": current_user.user_id,
        #   "user_email": user_email,
        #   "model":"Database",
        #   "description":f"Failed to get Database with ID: {database.id}"
        # }
        # send_async_log_message(log_data)
        raise HTTPException(status_code=404, detail="Databases not found")

    revoked_db = undo_database_revoke(database)
    if type(revoked_db) == SimpleNamespace:
        status_code = revoked_db.status_code if revoked_db.status_code else 500
        # log_data = {
        #   "operation": "DATABASE UNREVOKE",
        #   "status": "Failed",
        #   "user_id": current_user.user_id,
        #   "user_email": user_email,
        #   "model":"Database",
        #   "description":f"Database: {database.id} is {revoked_db.message}."
        # }
        # send_async_log_message(log_data)
        return dict(status_code=status_code, message=revoked_db.message)
    # log_data = {
    #   "operation": "DATABASE UNREVOKE",
    #   "status": "Success",
    #   "user_id": current_user.user_id,
    #   "user_email": user_email,
    #   "model":"Database",
    #   "description":f"Database: {database.id} is unrevoked successfully."
    # }
    # send_async_log_message(log_data)
    return {"message": "Database unrevoked successfully"}
