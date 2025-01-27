from app.helpers.database_session import get_db
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from contextlib import closing
import logging
import typer
from fastapi import FastAPI

from app.models import Database

# Initialize FastAPI and Typer CLI
app = FastAPI()
cli = typer.Typer()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_session(db_url: str) -> Session:
    """Creates a new SQLAlchemy session for the provided database URL."""
    engine = create_engine(db_url, pool_pre_ping=True,
                           pool_size=10, max_overflow=20)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def get_project_by_id(session: Session, project_id: int):
    """Fetch a project by its ID."""
    return session.execute(
        text('SELECT * FROM project WHERE id = :id'),
        {'id': project_id}
    ).fetchone()


def get_user_by_id(session: Session, user_id: str):
    """Fetch a user by their ID."""
    return session.execute(
        text('SELECT * FROM "user" WHERE id = :id'),
        {'id': user_id}
    ).fetchone()


@cli.command()
def update_users(db_url: str = typer.Option(None, help="Backend Database URL")):
    """Update users in the database by assigning owner_id to databases."""
    logger.info("Starting user update process...")
    if not db_url:
        logger.error("No database URL provided. Exiting.")
        return

    db: Session = next(get_db())
    updated_count = 0
    try:
        # Fetch databases without owners
        databases = db.query(Database).filter(
            Database.owner_id.is_(None)).all()
        logger.info(f"Found {len(databases)} databases without owner.")

        if not databases:
            logger.info("No databases to update. Exiting.")
            return

        # Create a new session for the provided db_url
        with closing(create_session(db_url)) as new_db:
            for database in databases:
                project = get_project_by_id(new_db, database.project_id)
                if not project:
                    logger.warning(f"""No project found for database ID {
                                   database.id}. Skipping.""")
                    continue

                user = get_user_by_id(new_db, str(project.owner_id))
                if not user:
                    logger.warning(f"""No user found for project ID {
                                   project.id}. Skipping.""")
                    continue

                # Update database with owner details
                database.owner_id = user.id
                database.email = user.email
                updated_count += 1
                logger.info(f"""Updated database ID {
                            database.id} with owner ID {user.id}.""")
                db.commit()

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
    finally:
        db.close()
        logger.info(f"""Database session closed. Total successful updates: {
                    updated_count}""")


if __name__ == "__main__":
    typer.run(cli)
