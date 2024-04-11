import requests
from functools import wraps
import datetime
from config import settings
from threading import Thread

DEFAULT_DATA = {
    "creation_date": str(datetime.datetime.now()),
    "model": "DATABASE",
}


def send_log_message(data):
    temp_data = {
        **DEFAULT_DATA, **data}

    logger_url = settings.ACTIVITY_LOGGER_URL
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(
            f'{logger_url}/api/activities', headers=headers, json=temp_data)
        response.raise_for_status()
    except Exception as e:
        print(f"Error occurred while sending log message: {str(e)}")


def log_response(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)

        log_data = {
            "route": func.__name__,
            "status_code": response.status_code,
        }

        send_log_message(log_data)
        return response
    return wrapper


def send_async_log_message(data):
    
    thread = Thread(target=send_log_message, args=(data,))
    thread.start()
