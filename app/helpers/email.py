from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from config import settings
import os
from pathlib import Path


conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM = settings.MAIL_USERNAME,
    MAIL_PORT = 587,
    MAIL_SERVER = "smtp.gmail.com",
    MAIL_STARTTLS = True,
    MAIL_SSL_TLS = False,
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = False,
    TEMPLATE_FOLDER= Path(__file__).parent.parent / 'templates',

)

async def send_database_limit_email_async(subject: str, email_to: str, body: dict):
    message = MessageSchema(
        subject=subject,
        recipients=email_to,
        template_body=body,
        subtype='html',
    )

    fm = FastMail(conf)
    await fm.send_message(message, template_name='database_limit.html')
