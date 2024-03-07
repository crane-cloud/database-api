from jose import JWTError, jwt
from functools import wraps
from app.helpers.admin import has_role
from fastapi import APIRouter, Depends, HTTPException
from jose.exceptions import JWKError , JWTError
import os

def authenticate(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):

        payload : object = {}

        if kwargs['access_token'] is None :
            raise HTTPException(status_code=401 , detail="Access token was not supplied")

        try :

            token = kwargs['access_token'].split(' ')[1]
            if (kwargs['access_token'].split(' ')[0] != "Bearer"):
                raise HTTPException(status_code=401, detail="The access token supplied is not a bearer token")
            
            payload = jwt.decode(token, os.getenv("JWT_SALT") , algorithms= ['HS256'])

        except JWTError:
            raise HTTPException(status_code=401, detail="Access token is not valid")
        
        except JWKError:
            raise HTTPException(status_code=401, detail="There is an error with the JWT verification salt.")

        except IndexError:
            raise HTTPException(status_code=401, detail="The access token supplied is not a bearer token")

        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    @authenticate
    def wrapper(*args, **kwargs):
        token = kwargs['access_token'].split(' ')[1]
        payload = jwt.decode(token , os.getenv("JWT_SALT") , algorithms= ['HS256'])
        if (has_role(payload['user_claims']['roles'] , "administrator")):
            return fn(*args, **kwargs)
        else :
            raise HTTPException(status_code=409, detail="Authentication failed . User is not admin")


    return wrapper
