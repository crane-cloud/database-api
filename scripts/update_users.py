from app.helpers.database_session import get_db
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import typer
from fastapi import FastAPI

from app.models import Database

app = FastAPI()
cli = typer.Typer()


@cli.command()
def update_users(db_url: str = typer.Option(None, help="Backend Database URL")):
    print(f"Updating users")
    db: Session = next(get_db())
    try:
        databases = db.query(Database).filter(
            Database.owner_id == None).all()
        print(f"Found {len(databases)} databases without owner")

        if not db_url:
            print("No database URL provided")
            return
        engine = create_engine(db_url, pool_pre_ping=True,
                               pool_size=10, max_overflow=20)
        NewSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=engine)
        new_db = NewSessionLocal()
        try:
            for database in databases:
                project = new_db.execute(text('SELECT * FROM project WHERE id = :id'), {
                    'id': database.project_id}).fetchone()
                if not project:
                    continue

                user = new_db.execute(text('SELECT * FROM "user" WHERE id = :id'), {
                    'id': str(project.owner_id)}).fetchone()
                if not user:
                    continue

                database.owner_id = user.id
                database.email = user.email
                db.commit()

        finally:
            new_db.close()

    finally:
        db.close()


if __name__ == "__main__":
    typer.run(cli)
