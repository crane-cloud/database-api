from fastapi import APIRouter

from . import admin, logging, userdb
router = APIRouter()
router.include_router(admin.router, tags=["Admin"])
router.include_router(userdb.router, tags=["Userdb"])
router.include_router(logging.router, tags=["Logging"])