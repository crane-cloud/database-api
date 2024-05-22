import uuid
from fastapi.testclient import TestClient
from main import app
import pytest
from pydantic import ValidationError
from app.schema import UserGraphSchema
import unittest
from unittest.mock import patch, Mock, MagicMock
from fastapi import Header
from sqlalchemy.orm import Session
from types import SimpleNamespace
from app.models import Database
from app.routes import fetch_database_stats, get_all_databases
from app.helpers.auth import get_current_user, check_authentication


client = TestClient(app)


def test_validate_set_by():
    valid_value = 'year'
    user_graph_schema = UserGraphSchema(
        start='2022-01-01', end='2022-12-31', set_by=valid_value)
    assert user_graph_schema.set_by == valid_value

    # Test with an invalid value
    invalid_value = 'week'
    with pytest.raises(ValueError):
        UserGraphSchema(start='2022-01-01', end='2022-12-31',
                        set_by=invalid_value)


def test_index():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == ['Welcome to the Database Service']


@patch('app.routes.get_current_user')
@patch('app.routes.check_authentication')
@patch('app.helpers.database_session.get_db')
def test_get_all_databases(
    mock_get_db,
    mock_check_authentication,
    mock_get_current_user
):
    # Mock current user
    current_user = Mock()
    current_user.id = 1
    current_user.role = "administrator"
    mock_get_current_user.return_value = current_user

    # Mock authentication check
    mock_check_authentication.return_value = None

    # Mock database session and data
    db = Mock(spec=Session)
    databases = [
        Database(id=1, name="Test Database 1", user="user1",
                 password="password1", database_flavour_name="mysql"),
        Database(id=2, name="Test Database 2", user="user2",
                 password="password2", database_flavour_name="mysql")
    ]
    db.query(Database).all.return_value = databases
    mock_get_db.return_value = db

    # Perform the request
    response = client.get(
        "/databases", headers={"Authorization": "Bearer dummy_access_token"})

    # Validate the response
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "databases" in data["data"]


@patch('app.routes.get_current_user')
@patch('app.routes.check_authentication')
@patch('app.helpers.database_session.get_db')
def test_fetch_database_stats(
    mock_get_db,
    mock_check_authentication,
    mock_get_current_user
):
    # Mock current user
    current_user = Mock()
    current_user.id = 1
    current_user.role = "administrator"
    mock_get_current_user.return_value = current_user

    # Mock authentication check
    mock_check_authentication.return_value = None

    # Mock database session and data
    db = Mock(spec=Session)
    databases = [
        Database(id=1, name="Test Database 1", database_flavour_name="mysql"),
        Database(id=2, name="Test Database 2", database_flavour_name="mysql"),
        Database(id=3, name="Test Database 3",
                 database_flavour_name="postgres")
    ]
    db.query(Database).filter_by.return_value.all.return_value = databases
    mock_get_db.return_value = db

    # Perform the request
    response = client.get(
        "/databases/stats", headers={"Authorization": "Bearer dummy_access_token"})

    # Validate the response
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "databases" in data["data"]
    assert "total_database_count" in data["data"]["databases"]
    assert "dbs_stats_per_flavour" in data["data"]["databases"]
    # Assuming 2 database flavours
    assert len(data["data"]["databases"]["dbs_stats_per_flavour"]) == 2
    assert "mysql_db_count" in data["data"]["databases"]["dbs_stats_per_flavour"]
    assert "postgres_db_count" in data["data"]["databases"]["dbs_stats_per_flavour"]
    assert data["data"]["databases"]["dbs_stats_per_flavour"]["mysql_db_count"] == 2


@patch('app.routes.get_current_user')
@patch('app.routes.check_authentication')
@patch('app.helpers.database_session.get_db')
def test_create_database(
    mock_get_db,
    mock_check_authentication,
    mock_get_current_user
):
    # Mock current user
    current_user = Mock()
    current_user.id = 1
    current_user.role = "administrator"
    mock_get_current_user.return_value = current_user

    # Mock authentication check
    mock_check_authentication.return_value = None

    # Mock database session
    db = Mock(spec=Session)
    mock_get_db.return_value = db

    # Perform the request
    response = client.post(
        "/databases",
        headers={"Authorization": "Bearer dummy_access_token"},
        json={"database_flavour_name": "mysql"}
    )

    # Validate the response
    assert response.status_code == 200


@patch('app.routes.get_current_user')
@patch('app.routes.check_authentication')
@patch('app.helpers.database_session.get_db')
def test_single_database_not_found(
    mock_get_db,
    mock_check_authentication,
    mock_get_current_user
):
    # Mock current user
    current_user = Mock()
    current_user.id = 1
    current_user.role = "administrator"
    mock_get_current_user.return_value = current_user

    # Mock authentication check
    mock_check_authentication.return_value = None

    # Mock database session
    db = Mock(spec=Session)
    mock_get_db.return_value = db

    # Create a mock database
    # Mock database query result
    mock_database = Mock(spec=Database)
    mock_database.id = uuid.uuid4()
    mock_database.name = "Test Database"
    mock_database.user = "test_user"
    mock_database.password = "test_password"
    mock_database.database_flavour_name = "mysql"
    db.query(Database).filter.return_value.first.return_value = mock_database

    # Perform the request
    response = client.get(
        f"/databases/{mock_database.id}",
        headers={"Authorization": "Bearer dummy_access_token"}
    )

    # Validate the response
    assert response.status_code == 404
