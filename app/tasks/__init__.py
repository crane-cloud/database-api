
import os
from celery import Celery, shared_task, states
from celery.schedules import crontab


from app.database import SessionLocal
from app.helpers.email import send_database_limit_email_async
from app.helpers.database_flavor import get_db_flavour, revoke_database

from app.models import Database
from app.helpers.database_session import db_dependency



redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
celery_app = Celery(__name__, broker=redis_url,
                    broker_connection_retry_on_startup = True,
                    backend=redis_url, include=['app.tasks'])


def update_celery(app):
    class ContextTask(celery_app.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = ContextTask
    celery_app.conf.worker_concurrency = 12
    return celery_app

@celery_app.on_after_configure.connect
def setup_periodic_tasks(**kwargs):
    celery_app.add_periodic_task(
        5.0, database_capping.s(), name='send email')

@celery_app.task(name = "send email")
async def database_capping():
    db = SessionLocal()
    
    databases = db.query(Database).all()

    for database in databases:

        database_service = get_db_flavour(database.database_flavour_name)['class']

        used_size = database_service.get_database_size(database.name , database.user , database.password)
        allocated_size = database.allocated_size_kb

        used_size = int(used_size.split()[0])

        await send_database_limit_email_async(
            "Database Revoked",
            ["lanternnassi@gmail.com"],
            database.__dict__
        )

        if used_size >= allocated_size:

            # Revoking database
            revoke_database(database)

            #Sending the satabase limit email
            send_database_limit_email_async(
                "Database Revoked",
                "lanternnassi@gmail.com",
                database
            )
            # send_email(database_name, "Database Revoked", "Your database has been revoked due to exceeding allocated storage.")
        elif used_size >= 0.7 * allocated_size:

            #Check if the user has not been notified 
            if not db.query(Database).filter_by(owner_id=database.owner_id, notified=True).first():

                #Send the email 
                send_database_limit_email_async(
                    "Warning: Database Storage Almost Full",
                    "lanternnassi@gmail.com",
                    database
                )

                # Updating the notification status of the database
                user_notification = Database(owner_id=database.owner_id, notified=True)
                db.add(user_notification)
                db.commit()

    db.close()



