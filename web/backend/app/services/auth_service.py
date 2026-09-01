from ..security.auth import verify_password, authenticate_user as _authenticate_user


def authenticate_user(username, password, tenant_slug=None, device_id=None):
    return _authenticate_user(username, password, tenant_slug=tenant_slug, device_id=device_id)
