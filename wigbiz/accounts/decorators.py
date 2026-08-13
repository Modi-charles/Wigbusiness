from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def role_required(*allowed_roles):

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            if not request.user.is_authenticated:
                return redirect("accounts:login")

            if request.user.role is None:

                messages.error(
                    request,
                    "Your account does not have a role assigned."
                )

                return redirect("accounts:no_role")

            user_role = request.user.role.name.strip().lower()

            allowed = [
                role.strip().lower()
                for role in allowed_roles
            ]

            if user_role not in allowed:

                messages.error(
                    request,
                    "You do not have permission to access this page."
                )

                return redirect("dashboard:dashboard")

            return view_func(
                request,
                *args,
                **kwargs
            )

        return wrapper

    return decorator
