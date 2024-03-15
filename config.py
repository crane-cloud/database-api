import os
from functools import lru_cache


class BaseConfig:
    DATABASE_URI: str = os.getenv("DATABASE_URI")
    DATABASE_USER: str = os.getenv("DATABASE_USER")
    JWT_SALT: str = os.getenv("JWT_SALT")
    
    # Admin databases
    ADMIN_MYSQL_HOST: str = os.getenv("ADMIN_MYSQL_HOST")
    ADMIN_MYSQL_PORT: int = os.getenv("ADMIN_MYSQL_PORT")
    ADMIN_PSQL_HOST: str = os.getenv("ADMIN_PSQL_HOST")
    ADMIN_PSQL_PORT: int = os.getenv("ADMIN_PSQL_PORT")


class DevelopmentConfig(BaseConfig):
    ADMIN_PSQL_USER : str = os.getenv("ADMIN_PSQL_USER")
    ADMIN_PSQL_PASSWORD : str = os.getenv("ADMIN_PSQL_PASSWORD")

    ADMIN_MYSQL_USER : str = os.getenv("ADMIN_MYSQL_USER")
    ADMIN_MYSQL_PASSWORD : str = os.getenv("ADMIN_MYSQL_PASSWORD")

class ProductionConfig(BaseConfig):
    pass


class TestingConfig(BaseConfig):
    TEST_DATABASE_URI = os.getenv("TEST_DATABASE_URI")


@lru_cache()
def get_settings():
    config_cls_dict = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "testing": TestingConfig
    }

    config_name = os.environ.get("FASTAPI_ENV", "development")
    config_cls = config_cls_dict[config_name]
    return config_cls()


settings = get_settings()
