from pytest import fixture
from starlette.config import environ
from starlette.testclient import TestClient
from jose import jwt
import datetime
from main import app
from config import settings


DATABASE_URI = "postgresql://postgres:postgres@localhost:4200/cranecloud_test"

ADMIN_MYSQL_HOST = "127.0.0.1"

ADMIN_MYSQL_PORT= 4200
ADMIN_PSQL_HOST = "127.0.0.1"
ADMIN_PSQL_PORT= 42034

@fixture(scope="module")
def test_client():
    client = TestClient(app)
    with client:
        yield client


@fixture(scope="session")
def test_client():
    with TestClient(app) as test_client:
        yield test_client


environ['TESTING'] = 'TRUE'
