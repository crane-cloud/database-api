import os
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
from fastapi import FastAPI
from pydantic import ValidationError
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router


def create_app() -> FastAPI:
	# load the environment variables
    current_dir = os.path.dirname(__file__)
    dotenv_path = os.path.join(current_dir, '.env')
    load_dotenv(dotenv_path)

	# create the FastAPI app
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

    @app.get('/', tags=['Index'])
    def index():
        return {"Welcome to the Database Service"}

    @app.exception_handler(ValidationError)
    async def handle_validation_error(request, exc: ValidationError):
        errors = [str(err) for err in exc.errors()]
        return JSONResponse({"error": "Validation failed", "errors": errors}, status_code=400)

    app.include_router(router)

    return app


app = create_app()
