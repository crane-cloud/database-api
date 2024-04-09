from jose import jwt
from config import settings
from types import SimpleNamespace
from fastapi import HTTPException


def has_role(role_list, role_name) -> bool:
    for role in role_list:
        if isinstance(role, dict) and 'name' in role and role['name'] == role_name:
            return True
    return False

def get_current_user(access_token):
    try:
        token = access_token.split(' ')[1]
        payload = jwt.decode(token, settings.JWT_SALT, algorithms=['HS256'])

        user_claims = payload['user_claims']
        role = user_claims['roles'][0]['name']
        user_id = payload['identity']
        email = user_claims['email']
        return SimpleNamespace(
            role=role, id=user_id, email=email
        )
    except Exception as e:
        return SimpleNamespace(role=None, id=None, email=None)

def check_authentication(current_user):
    if not current_user:
        # although our return format is of status_code and message for this exception class it has to be detail instead of message
        raise HTTPException(status_code=401, detail="Invalid token")
