from fastapi import APIRouter

from . import routes
router = APIRouter()
router.include_router(routes.router)
# router.include_router(logging.router, tags=["Logging"])