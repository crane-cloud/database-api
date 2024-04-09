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
from app.routes import fetch_database_stats
from app.helpers.auth import get_current_user, check_authentication



client = TestClient(app)

def test_validate_set_by():
    valid_value = 'year'
    user_graph_schema = UserGraphSchema(start='2022-01-01', end='2022-12-31', set_by=valid_value)
    assert user_graph_schema.set_by == valid_value

    # Test with an invalid value
    invalid_value = 'week'
    with pytest.raises(ValueError):
        UserGraphSchema(start='2022-01-01', end='2022-12-31', set_by=invalid_value)




def test_index():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == ['Welcome to the Database Service']


@patch('app.helpers.auth.get_current_user')
@patch('app.routes.check_authentication')
def test_get_all_databases(mock_check_authentication, mock_get_current_user):
    from app.routes import get_all_databases
    from app.models import Database

    access_token = "dummy_access_token"
    current_user = Mock()
    current_user.id = 1
    current_user.role = "administrator"

    db = Mock(spec=Session)
    databases = [Database(id=1, name="Test Database 1"), Database(id=2, name="Test Database 2")]
    db.query(Database).all.return_value = databases

    mock_get_current_user.return_value = current_user

    result = get_all_databases(access_token=access_token, db=db)

    expected_response = SimpleNamespace(status_code=200, data={"databases": databases})

    mock_check_authentication.assert_called_once()

    assert result.status_code == expected_response.status_code
    assert type(result.data) == type(expected_response.data)


@patch('app.routes.get_current_user')
@patch('app.routes.check_authentication')
def test_fetch_database_stats( mock_check_authentication, mock_get_current_user):
    access_token = "dummy_access_token"
    current_user = Mock()
    current_user.id = 1
    current_user.role = "administrator"

    db = Mock(spec=Session)
    database_flavours = [{'name': 'flavour1'}, {'name': 'flavour2'}]
    databases = [Database(id=1, name="Test Database 1", database_flavour_name='flavour1'),
                    Database(id=2, name="Test Database 2", database_flavour_name='flavour2'),
                    Database(id=3, name="Test Database 3", database_flavour_name='flavour1')]

    db.query.return_value.filter_by.side_effect = lambda **kwargs: Mock(all=Mock(return_value=[db for db in databases if db.database_flavour_name == kwargs['database_flavour_name']]))
    
    mock_get_current_user.return_value = current_user

    result = fetch_database_stats(access_token=access_token, db=db)

    expected_total_count = len(databases)
    expected_db_stats_per_flavour = {'flavour1_db_count': 2, 'flavour2_db_count': 1}
    expected_data = {'total_database_count': expected_total_count, 'dbs_stats_per_flavour': expected_db_stats_per_flavour}
    expected_response = SimpleNamespace(status_code=200, data={'databases': expected_data})

    mock_get_current_user.assert_called_once_with(access_token)
    mock_check_authentication.assert_called_once()

    assert result.status_code == expected_response.status_code
    assert type(result.data) == type(expected_response.data)

# def test_index(test_client):
#     response = test_client.get("/api/")
#     assert response.status_code == 200
#     assert response.json() == {"message": "Hello, world"}
