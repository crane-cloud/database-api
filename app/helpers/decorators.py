from jose import JWTError, jwt
from functools import wraps
from app.helpers.auth import has_role
from fastapi import HTTPException
from jose.exceptions import JWKError , JWTError
from config import settings

JWT_SALT = settings.JWT_SALT

def authenticate(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):

        payload : object = {}

        if kwargs['access_token'] is None :
            raise HTTPException(status_code=401 , detail="Access token was not supplied")

        try :
            token = kwargs['access_token'].split(' ')[1]
            if (kwargs['access_token'].split(' ')[0] != "Bearer"):
                raise HTTPException(status_code=422, detail="Bad Authorization header. Expected value 'Bearer <JWT>'")
            
            payload = jwt.decode(token, JWT_SALT, algorithms= ['HS256'])
            
            kwargs['current_user'] = payload
            
        except JWTError:
            raise HTTPException(status_code=401, detail="Access token is not valid")
        
        except JWKError:
            raise HTTPException(status_code=401, detail="There is an error with the JWT verification salt.")

        except IndexError:
            raise HTTPException(status_code=401, detail="The access token supplied is not a bearer token")

        return fn(*args, **kwargs)
    return wrapper


def admin_or_user_required(fn):
    @wraps(fn)
    @authenticate
    def wrapper(*args, **kwargs):
        token = kwargs['access_token'].split(' ')[1]
        payload = jwt.decode(token ,  JWT_SALT, algorithms= ['HS256'])
        current_user = kwargs['current_user']

        kwargs['is_admin'] = has_role(current_user, "administrator")
        return fn(*args, **kwargs)

    return wrapper

