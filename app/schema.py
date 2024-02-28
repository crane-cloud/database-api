from datetime import date, datetime
from pydantic import BaseModel, Field
from typing import List, Optional
from pydantic import BaseModel, UUID4, constr
from typing import Optional
from datetime import datetime

class DatabaseSchema(BaseModel):
    host: str
    name: str
    user: str
    password: str
    owner_id: str
    port: Optional[int]
    database_flavour_name: str 
    deleted: bool = False
    disabled: bool = False
    admin_disabled: bool = False

class DatabaseFlavor(BaseModel):
    
    database_flavour_name: Optional[str]