from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

ADMINISTRATOR = "Administrator"
MANAGER = "Manager"
SALESPERSON = "Salesperson"


def has_role(user, *roles):
    """True if the user's role name matches any of the given names (case-insensitive)."""
    name = (getattr(user, "role_name", None) or "").strip().lower()
    return name in {r.lower() for r in roles}


def roles_required(*roles):
    """Login required + user must have one of the given roles, otherwise 403."""

    def decorator(view):
        @login_required
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not has_role(request.user, *roles):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapper

    return decorator