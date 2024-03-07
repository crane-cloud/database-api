from jose import JWTError, jwt
import os


def has_role(role_list, role_name) -> bool:
    for role in role_list:
        if role['name'] == role_name:
            return True
    return False


def get_current_user(access_token) -> object:
    payload = jwt.decode(access_token , os.getenv("JWT_SALT") , algorithms= ['HS256'])
    return payload['user_claims']['roles'][0]
