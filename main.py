from typing import Union
from fastapi.responses import JSONResponse
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.routes import router
import settings

app = FastAPI(
  title="Database Service"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get('/', tags=['Test'])
def index():
  return {"Healthcheck": "The database service is up and running ...."}

@app.exception_handler(ValidationError)
async def handle_validation_error(request, exc: ValidationError):
    errors = [str(err) for err in exc.errors()]
    return JSONResponse({"error": "Validation failed", "errors": errors}, status_code=400)


app.include_router(router)
