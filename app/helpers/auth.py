from jose import jwt
from jwt import DecodeError, ExpiredSignatureError, InvalidTokenError
from config import settings
from types import SimpleNamespace
from fastapi import HTTPException


def has_role(role_list, role_name) -> bool:
    for role in role_list:
        if isinstance(role, dict) and 'name' in role and role['name'] == role_name:
            return True
    return False


def get_current_user(access_token: str):
    try:
        payload = jwt.decode(
            access_token, settings.JWT_SALT, algorithms=['HS256'])

        user_claims = payload.get('user_claims', {})
        roles = user_claims.get('roles', [])

        role = roles[0].get('name') if roles and isinstance(
            roles, list) else None
        user_id = payload.get('identity')
        email = user_claims.get('email')

        return SimpleNamespace(role=role, id=user_id, email=email)

    except (InvalidTokenError, DecodeError, ExpiredSignatureError) as e:
        print(f"Token error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=401, detail="Unauthorized")


def check_authentication(current_user):
    if not current_user:
        # although our return format is of status_code and message for this exception class it has to be detail instead of message
        raise HTTPException(status_code=401, detail="Invalid token")
