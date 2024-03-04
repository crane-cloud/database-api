from jose import JWTError, jwt
from functools import wraps
from app.helpers.admin import has_role
from fastapi import APIRouter, Depends, HTTPException
import os

def authenticate(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        payload = jwt.decode(kwargs['access_token'] , os.getenv("JWT_SALT") , algorithms= ['HS256'])
        
        if (not payload['fresh']):
            raise HTTPException(status_code=409, detail="The authentication session is currently expired.")

        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    @authenticate
    def wrapper(*args, **kwargs):
        payload = jwt.decode(kwargs['access_token'] , os.getenv("JWT_SALT") , algorithms= ['HS256'])
        if (has_role(payload['user_claims']['roles'] , "administrator")):
            return fn(*args, **kwargs)
        else :
            raise HTTPException(status_code=409, detail="Authentication failed . User is not admin")


    return wrapper
