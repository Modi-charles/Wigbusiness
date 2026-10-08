from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_POST

from .models import User
from .decorators import role_required
from .forms import UserCreateForm, UserUpdateForm

# ============================================================
# LOGIN
# ============================================================

def login_view(request):

    # If the user is already logged in,
    # send them to the central dashboard router.
    if request.user.is_authenticated:
        return redirect_user_by_role(request.user)

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)

        # INVALID LOGIN
        if user is None:
            messages.error(request, "Invalid username or password.")
            return render(request, "accounts/login.html")

        # DEACTIVATED ACCOUNT
        if not user.is_active:
            messages.error(request, "Your account has been deactivated.")
            return redirect("accounts:login")

        # LOGIN USER
        login(request, user)

        # SEND USER TO THEIR ROLE DASHBOARD
        return redirect_user_by_role(user)

    return render(request, "accounts/login.html")


# ============================================================
# ROLE-BASED DASHBOARD REDIRECT
# ============================================================

def redirect_user_by_role(user):

    # User has no role
    if user.role is None:
        return redirect("accounts:no_role")

    # All authenticated users go through the central dashboard router.
    # dashboard/views.py then decides which dashboard belongs to the role.
    return redirect("dashboard:dashboard")


# ============================================================
# LOGOUT
# ============================================================

def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("accounts:login")


# ============================================================
# NO ROLE
# ============================================================

def no_role(request):
    return render(request, "accounts/no_role.html")


# ============================================================
# USER LIST
# ADMINISTRATOR ONLY
# ============================================================

@login_required
@role_required("Administrator")
def user_list(request):

    users = User.objects.select_related("role").order_by("username")
    query = request.GET.get("q", "").strip()

    # SEARCH USERS
    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
            | Q(role__name__icontains=query)
        )

    # PAGINATION
    paginator = Paginator(users, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "accounts/user_list.html",
        {"page_obj": page_obj, "query": query},
    )


# ============================================================
# CREATE USER
# ADMINISTRATOR ONLY
# ============================================================

@login_required
@role_required("Administrator")
def user_create(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"User {user.username} created successfully.")
            return redirect("accounts:user_list")
    else:
        form = UserCreateForm()

    return render(
        request,
        "accounts/user_form.html",
        {"form": form, "title": "Add New User"},
    )


# ============================================================
# UPDATE USER
# ADMINISTRATOR ONLY
# ============================================================

@login_required
@role_required("Administrator")
def user_update(request, pk):
    user_instance = get_object_or_404(User, pk=pk)

    if request.method == "POST":
        form = UserUpdateForm(request.POST, instance=user_instance)
        if form.is_valid():
            form.save()
            messages.success(request, "User updated successfully.")
            return redirect("accounts:user_list")
    else:
        form = UserUpdateForm(instance=user_instance)

    return render(
        request,
        "accounts/user_form.html",
        {"form": form, "title": f"Edit User: {user_instance.username}"},
    )


# ============================================================
# DEACTIVATE USER
# ADMINISTRATOR ONLY
# ============================================================

@login_required
@role_required("Administrator")
@require_POST
def user_deactivate(request, pk):
    user = get_object_or_404(User, pk=pk)

    # PREVENT ADMIN FROM DEACTIVATING THEMSELVES
    if user == request.user:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect("accounts:user_list")

    user.is_active = False
    user.save(update_fields=["is_active"])
    messages.success(request, f"User {user.username} has been deactivated.")
    return redirect("accounts:user_list")


# ============================================================
# CHANGE PASSWORD
# ============================================================

@login_required
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Keep the user logged in after changing their password.
            update_session_auth_hash(request, user)
            messages.success(request, "Your password has been changed successfully.")
            return redirect("dashboard:dashboard")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, "accounts/change_password.html", {"form": form})


# ============================================================
# SETTINGS
# ============================================================

@login_required
def settings_view(request):
    return render(request, "accounts/settings.html")