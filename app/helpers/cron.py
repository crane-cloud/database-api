from schedule import every, run_pending
import time
from app.database import SessionLocal
from app.email import send_email
from app.database import UserNotification
from app.main import get_database_sizes, revoke_database

def cron_job():
    db = SessionLocal()

    database_sizes = get_database_sizes()

    for database_name, (used_size, allocated_size) in database_sizes.items():
        if used_size >= allocated_size:
            revoke_database(database_name)
            send_email(database_name, "Database Revoked", "Your database has been revoked due to exceeding allocated storage.")
        elif used_size >= 0.7 * allocated_size:
            if not db.query(UserNotification).filter_by(user_id=database_name, notified=True).first():
                send_email(database_name, "Warning: Database Storage Almost Full", "Your database is nearly full.")
                user_notification = UserNotification(user_id=database_name, notified=True)
                db.add(user_notification)
                db.commit()

    db.close()

# Schedule the cron job to run every six hours
every(6).hours.do(cron_job)

# Run the scheduled jobs
while True:
    run_pending()
    time.sleep(1)
