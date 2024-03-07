from jose import JWTError, jwt
import os


def has_role(role_list, role_name) -> bool:
    for role in role_list:
        if role['name'] == role_name:
            return True
    return False


def get_current_user(access_token) -> object:
    token = access_token.split(' ')[1]
    payload = jwt.decode(token , os.getenv("JWT_SALT") , algorithms= ['HS256'])
    return payload['user_claims']['roles'][0]
