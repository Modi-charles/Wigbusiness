from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)

from django.contrib import messages

from django.contrib.auth import (
    authenticate,
    login,
    logout,
    update_session_auth_hash,
)

from django.contrib.auth.decorators import (
    login_required,
)

from django.contrib.auth.forms import (
    PasswordChangeForm,
)

from django.core.paginator import Paginator

from .models import User, Role
from .decorators import role_required


def login_view(request):

    if request.user.is_authenticated:
        return redirect_user_by_role(request.user)

    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None:

            if not user.is_active:

                messages.error(
                    request,
                    "Your account has been deactivated."
                )

                return redirect(
                    "accounts:login"
                )

            login(
                request,
                user
            )

            return redirect_user_by_role(user)

        messages.error(
            request,
            "Invalid username or password."
        )

    return render(
        request,
        "accounts/login.html"
    )


def redirect_user_by_role(user):

    if user.role is None:

        return redirect(
            "accounts:no_role"
        )

    role = user.role.name.strip().lower()

    if role == "administrator":

        return redirect(
            "dashboard:dashboard"
        )

    elif role == "manager":

        return redirect(
            "dashboard:dashboard"
        )

    elif role == "salesperson":

        return redirect(
            "sales:create_sale"
        )

    elif role == "inventory staff":

        return redirect(
            "inventory:view_inventory"
        )

    elif role == "accountant":

        return redirect(
            "reports:dashboard"
        )

    return redirect(
        "accounts:no_role"
    )


def logout_view(request):

    logout(request)

    messages.success(
        request,
        "You have been logged out successfully."
    )

    return redirect(
        "accounts:login"
    )


def no_role(request):

    return render(
        request,
        "accounts/no_role.html"
    )
@login_required
@role_required("Administrator")
def user_list(request):

    users = User.objects.select_related(
        "role"
    ).order_by(
        "username"
    )

    query = request.GET.get(
        "q",
        ""
    ).strip()

    if query:

        users = users.filter(
            username__icontains=query
        ) | users.filter(
            first_name__icontains=query
        ) | users.filter(
            last_name__icontains=query
        )

    paginator = Paginator(
        users,
        20
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )

    return render(
        request,
        "accounts/user_list.html",
        {
            "page_obj": page_obj,
            "query": query,
        }
    )
@login_required
@role_required("Administrator")
def user_create(request):

    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        first_name = request.POST.get(
            "first_name",
            ""
        ).strip()

        last_name = request.POST.get(
            "last_name",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        phone = request.POST.get(
            "phone",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        role_id = request.POST.get(
            "role"
        )

        if not username or not password:

            messages.error(
                request,
                "Username and password are required."
            )

            return redirect(
                "accounts:user_create"
            )

        if User.objects.filter(
            username=username
        ).exists():

            messages.error(
                request,
                "That username already exists."
            )

            return redirect(
                "accounts:user_create"
            )

        role = Role.objects.filter(
            id=role_id
        ).first()

        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            email=email,
        )

        user.phone = phone
        user.role = role
        user.save()

        messages.success(
            request,
            f"User {username} created successfully."
        )

        return redirect(
            "accounts:user_list"
        )

    roles = Role.objects.all().order_by(
        "name"
    )

    return render(
        request,
        "accounts/user_form.html",
        {
            "roles": roles,
        }
    )
@login_required
@role_required("Administrator")
def user_update(request, pk):

    user = get_object_or_404(
        User,
        pk=pk
    )

    if request.method == "POST":

        user.first_name = request.POST.get(
            "first_name",
            ""
        ).strip()

        user.last_name = request.POST.get(
            "last_name",
            ""
        ).strip()

        user.email = request.POST.get(
            "email",
            ""
        ).strip()

        user.phone = request.POST.get(
            "phone",
            ""
        ).strip()

        role_id = request.POST.get(
            "role"
        )

        user.role = Role.objects.filter(
            id=role_id
        ).first()

        user.save()

        messages.success(
            request,
            "User updated successfully."
        )

        return redirect(
            "accounts:user_list"
        )

    roles = Role.objects.all().order_by(
        "name"
    )

    return render(
        request,
        "accounts/user_form.html",
        {
            "user_account": user,
            "roles": roles,
        }
    )
@login_required
@role_required("Administrator")
def user_deactivate(request, pk):

    user = get_object_or_404(
        User,
        pk=pk
    )

    if user == request.user:

        messages.error(
            request,
            "You cannot deactivate your own account."
        )

        return redirect(
            "accounts:user_list"
        )

    user.is_active = False

    user.save(
        update_fields=[
            "is_active"
        ]
    )

    messages.success(
        request,
        f"User {user.username} has been deactivated."
    )

    return redirect(
        "accounts:user_list"
    )
@login_required
def change_password(request):

    if request.method == "POST":

        form = PasswordChangeForm(
            request.user,
            request.POST
        )

        if form.is_valid():

            user = form.save()

            update_session_auth_hash(
                request,
                user
            )

            messages.success(
                request,
                "Your password has been changed successfully."
            )

            return redirect(
                "dashboard:dashboard"
            )

    else:

        form = PasswordChangeForm(
            request.user
        )

    return render(
        request,
        "accounts/change_password.html",
        {
            "form": form
        }
    )
