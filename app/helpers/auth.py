from jose import jwt
from config import settings
from types import SimpleNamespace


def has_role(role_list, role_name) -> bool:
    for role in role_list:
        if role['name'] == role_name:
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
        print(e)
        return None
