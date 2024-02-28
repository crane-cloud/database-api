from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
# from api.deps import get_current_active_superuser, get_db
from app.schema import (DatabaseSchema)

router = APIRouter()
