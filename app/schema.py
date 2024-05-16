from datetime import date, datetime
from pydantic import BaseModel, Field, validator, UUID4, constr
from typing import List, Optional


class DatabaseSchema(BaseModel):
    host: str
    name: str
    user: str
    password: str
    owner_id: str
    email: str
    port: Optional[int]
    database_flavour_name: str
    deleted: bool = False
    disabled: bool = False
    admin_disabled: bool = False


class DatabaseFlavor(BaseModel):

    database_flavour_name: Optional[str]


class PasswordUpdate(BaseModel):

    password: str


class UserGraphSchema(BaseModel):
    start: date
    end: date
    set_by: str

    @validator('set_by')
    def validate_set_by(cls, value):
        if value not in ['year', 'month']:
            raise ValueError('set_by should be year or month')
        return value
