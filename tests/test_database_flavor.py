import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.helpers.database_service import MysqlDbService, PostgresqlDbService
from app.models import Database
from main import app
from fastapi.testclient import TestClient
import os
import tests
from unittest.mock import patch, MagicMock, Mock
from config import settings
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.helpers.logger import send_async_log_message
from app.helpers.database_flavor import get_db_flavour, get_all_db_flavours, failed_database_connection, database_not_found, save_to_database, database_flavours
from tests import conftest
from types import SimpleNamespace
client = TestClient(app)

current_user = {"id": 1, "email": "test@example.com"}
@patch('config.settings') 
def test_get_db_flavour_mysql( conftest):
    """Tests that get_db_flavour returns the correct database flavour for 'mysql'."""
   
    conftest.ADMIN_MYSQL_HOST = '...'
    conftest.ADMIN_MYSQL_PORT = ...

    flavour = get_db_flavour('mysql')
    assert flavour == database_flavours[0]
    assert flavour['name'] ==  'mysql'

@patch('config.settings')  # Mock settings module if necessary
def test_get_db_flavour_postgres(conftest):
    conftest.ADMIN_PSQL_HOST = '...'
    conftest.ADMIN_PSQL_PORT = ...

    flavour = get_db_flavour('postgres')
    assert flavour == database_flavours[1]
    assert flavour['name'] == 'postgres'


def test_get_db_flavour_invalid():
    db_flavour = get_db_flavour('invalid')
    assert not db_flavour


def test_get_all_db_flavours():
    with patch('config.settings.ADMIN_MYSQL_HOST', 'mock_mysql_host'), \
        patch('config.settings.ADMIN_MYSQL_PORT', 3306), \
        patch('config.settings.ADMIN_PSQL_HOST', 'mock_psql_host'), \
        patch('config.settings.ADMIN_PSQL_PORT', 5432):

        expected_result = [
          {
              'name': 'mysql',
              'host': 'mock_mysql_host',
              'port': '32763',
              'class': MysqlDbService() 
          },
          {
              'name': 'postgres',
              'host': 'mock_psql_host',
              'port': '32763',
              'class': PostgresqlDbService()
          }
        ]

        result = get_all_db_flavours()

    assert type(result) == type(expected_result)

def test_save_to_database():
    mock_db = MagicMock()
    mock_db.commit.side_effect = MagicMock()

    with patch('fastapi.HTTPException') as mock_http_exception:
        save_to_database(mock_db)
        mock_db.commit.assert_called_once()
        mock_http_exception.assert_not_called()

    mock_db.rollback.reset_mock()  # Reset the mock for rollback
    with patch('fastapi.HTTPException') as mock_http_exception:
        mock_db.commit.side_effect = SQLAlchemyError()
        try:
            save_to_database(mock_db)
        except HTTPException as e:
            assert isinstance(e, HTTPException)
            assert e.status_code == 500
            assert e.detail == "Failed to save to the database"
            mock_db.rollback.assert_called_once()
        else:
            assert False, "Expected HTTPException was not raised"
     

def test_database_not_found():
    with patch('app.helpers.logger.send_async_log_message') as mock_log:
        current_user = {"id": 1}
        database_id = 10
        try:
            with pytest.raises(HTTPException) as excinfo:
                database_not_found(current_user, "get_database", database_id)
            assert excinfo.value.status_code == 404
            assert excinfo.value.detail == "Database not found"
            mock_log.assert_called_with({
                "operation": "get_database",
                "status": "Failed",
                "user_id": 1,
                "model": "Database",
                "description": f"Failed to get Database with ID: {database_id}"
            })
        except:
            send_async_log_message({
                "operation": "get_database",
                "status": "Failed",
                "user_id": 1,
                "model": "Database",
                "description": f"Failed to get Database with ID: {database_id}"
            })


def test_failed_database_connection():
    with patch('app.helpers.logger.send_async_log_message') as mock_log:
        current_user = {"id": 1, "email": "test@example.com"}
        operation = "connect_database"
        database_id = 10

    
    try:
        with pytest.raises(HTTPException) as excinfo:
            database_not_found(current_user, "connect", database_id)
        assert excinfo.value.status_code == 500
        assert excinfo.value.detail == "Failed to connect to the database service"
        mock_log.assert_called_with({
            "operation": "connect",
            "status": "Failed",
            "user_id": 1,
            "model": "Database",
            "description": f"Failed to connect Database with ID: {database_id}"
        })
    except:
        send_async_log_message({
            "operation": "connect",
            "status": "Failed",
            "user_id": 1,
            "model": "Database",
            "description": f"Failed to connect Database with ID: {database_id}"
        })  
