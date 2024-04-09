from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app
from app.helpers.auth import has_role, get_current_user, check_authentication
from app.database import database_exists, create_database
from fastapi import HTTPException
from jose import jwt
from config import settings
import os
from functools import wraps
from app.helpers.decorators import authenticate, admin_or_user_required, JWT_SALT
from tests.conftest import DATABASE_URI

client = TestClient(app)

def test_has_role():
    roles = [{'name': 'admin'}, {'name': 'user'}]
    assert has_role(roles, 'admin') == True
    assert has_role(roles, 'guest') == False

def test_get_current_user():
    access_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    mock_jwt_decode = patch('jose.jwt.decode', return_value={
        'user_claims': {
            'roles': [{'name': 'admin'}],
            'email': 'test@example.com'
        },
        'identity': 'user_id'
    })
    with mock_jwt_decode:
        user = get_current_user(access_token)
    assert user.role == 'admin'
    assert user.id == 'user_id'
    assert user.email == 'test@example.com'

def test_check_authentication():
    current_user = None
    try:
        check_authentication(current_user)
    except HTTPException as e:
        assert e.status_code == 401
        assert e.detail == "Invalid token"
    else:
        assert False, "HTTPException not raised"

def test_invalid_access_token():
    access_token = "Bearer invalid_token"
    result = get_current_user(access_token)
    assert result.role is None
    assert result.id is None
    assert result.email is None

@patch('jwt.decode')
def test_jwt_decode_error(mock_jwt_decode):
    mock_jwt_decode.side_effect = Exception("JWT decode error")
    access_token = "Bearer valid_token"
    result = get_current_user(access_token)
    assert result.role is None
    assert result.id is None
    assert result.email is None


def admin_or_user_required(fn):
    @wraps(fn)
    @authenticate
    def wrapper(*args, **kwargs):
        token = kwargs['access_token'].split(' ')[1]
        payload = jwt.decode(token, JWT_SALT, algorithms=['HS256'])
        current_user = kwargs['current_user']

        kwargs['is_admin'] = has_role(current_user, "administrator")
        return fn(*args, **kwargs)

    return wrapper

def test_admin_required():
    def dummy_authenticate(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            kwargs['current_user'] = {'roles': ['administrator']}
            return fn(*args, **kwargs)
        return wrapper
    
    def dummy_has_role(user, role):
        return 'administrator' in user.get('roles', [])
    
    @admin_or_user_required
    def dummy_function(*args, **kwargs):
        return "Admin access granted" if kwargs.get('is_admin') else "Access denied"
    
    # Patching authenticate and has_role functions
    authenticate = dummy_authenticate
    has_role = dummy_has_role
    
    result = dummy_function(access_token="Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE3MTI1ODc4MTQsIm5iZiI6MTcxMjU4NzgxNCwianRpIjoiMjhkZmFiZmEtNjFiZS00OTE4LWJlMDMtNWE1ZGJlMTI4MzllIiwiZXhwIjoxNzEzNDUxODE0LCJpZGVudGl0eSI6IjRkYmJlNDhjLWU1NWYtNDQ2Mi05Nzk5LTBmOTFmOTJjY2NiNCIsImZyZXNoIjpmYWxzZSwidHlwZSI6ImFjY2VzcyIsInVzZXJfY2xhaW1zIjp7InJvbGVzIjpbeyJuYW1lIjoiY3VzdG9tZXIiLCJpZCI6IjdmN2ZiZGQ5LWMxMGQtNGRiMC1iOTQ3LWUyZDc0MmE2MTlhOSJ9XSwiZW1haWwiOiJoZW5yeUBjcmFuZWNsb3VkLmlvIn19.ej5-HNioEPrVT6oZ2mdKamTGVQiBt7LSAbALP1Jde0g", current_user={'user_claims': {
            'roles': [{'name': 'admin'}],
            'email': 'test@example.com'
        }})
    
    assert result == "Access denied"

def test_user_required():
    def dummy_authenticate(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            kwargs['current_user'] = {'roles': ['user']}
            return fn(*args, **kwargs)

        return wrapper

    def dummy_has_role(user, role):
        return 'administrator' in user.get('roles', [])

    @admin_or_user_required
    def dummy_function(*args, **kwargs):
        return "Admin access granted" if kwargs.get('is_admin') else "Access denied"

    # Patching authenticate and has_role functions
    authenticate = dummy_authenticate
    has_role = dummy_has_role

    # Testing user access
    result = dummy_function(access_token="Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE3MTI1ODU4NzEsIm5iZiI6MTcxMjU4NTg3MSwianRpIjoiZDFjODIzZGUtZGE4OC00MDI5LTg0NDktZWQ0ZmVlMWUyNjExIiwiZXhwIjoxNzEzNDQ5ODcxLCJpZGVudGl0eSI6IjMzMDIyMmFmLWJkYTktNDlhYy04MWMzLWQ3ZGQ0MDI1NjlhYSIsImZyZXNoIjpmYWxzZSwidHlwZSI6ImFjY2VzcyIsInVzZXJfY2xhaW1zIjp7InJvbGVzIjpbeyJuYW1lIjoiYWRtaW5pc3RyYXRvciIsImlkIjoiYWYyM2Y2ZDgtZWRlZi00NWY0LTg1ZWMtZGE2Y2Q3ZDUxOWJiIn1dLCJlbWFpbCI6ImFkbWluQGNyYW5lY2xvdWQuaW8ifX0.FXrs1icgXrPwGsH4m6EW9iNIV0uuXLykRNFLWthoyMM")
    assert result == "Access denied"







