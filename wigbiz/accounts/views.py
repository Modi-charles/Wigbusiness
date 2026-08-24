from django.shortcuts import render,redirect,get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate,login,logout,update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator
from .models import User, Role
from .decorators import role_required


# ============================================================
# LOGIN
# ============================================================

def login_view(request):

    # If the user is already logged in,
    # send them to the central dashboard router.
    if request.user.is_authenticated:

        return redirect_user_by_role(
            request.user
        )

    if request.method == "POST":
        username = request.POST.get( "username","").strip()
        password = request.POST.get("password","")
        user = authenticate(
            request,
            username=username,
            password=password,
        )
# INVALID LOGIN
    
        if user is None:
            messages.error(request,"Invalid username or password.")
            return render(request,"accounts/login.html")

# DEACTIVATED ACCOUNT
        

        if not user.is_active:
            messages.error(request,"Your account has been deactivated.")
            return redirect("accounts:login")
# LOGIN USER
        login(request,user)
# SEND USER TO THEIR ROLE DASHBOARD
        return redirect_user_by_role(user)
    return render(request,"accounts/login.html")

# ============================================================
# ROLE-BASED DASHBOARD REDIRECT
# ============================================================

def redirect_user_by_role(user):

    # User has no role
    if user.role is None:

        return redirect(
            "accounts:no_role"
        )

    # All authenticated users go through
    # the central dashboard router.
    #
    # dashboard/views.py then decides which
    # dashboard belongs to the user's role.

    return redirect(
        "dashboard:dashboard"
    )


# ============================================================
# LOGOUT
# ============================================================

def logout_view(request):

    logout(request)

    messages.success(
        request,
        "You have been logged out successfully."
    )

    return redirect(
        "accounts:login"
    )


# ============================================================
# NO ROLE
# ============================================================

def no_role(request):

    return render(
        request,
        "accounts/no_role.html"
    )


# ============================================================
# USER LIST
# ADMINISTRATOR ONLY
# ============================================================

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

    # --------------------------------------------------------
    # SEARCH USERS
    # --------------------------------------------------------

    if query:

        users = users.filter(
            username__icontains=query
        ) | users.filter(
            first_name__icontains=query
        ) | users.filter(
            last_name__icontains=query
        )

    # --------------------------------------------------------
    # PAGINATION
    # --------------------------------------------------------

    paginator = Paginator(users,20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request,"accounts/user_list.html",{"page_obj": page_obj,"query": query,})

# CREATE USER
# ADMINISTRATOR ONLY
# ============================================================

@login_required
@role_required("Administrator")
def user_create(request):
    if request.method == "POST":
        username = request.POST.get( "username","" ).strip()
        first_name = request.POST.get("first_name","").strip()
        last_name = request.POST.get("last_name","").strip()
        email = request.POST.get("email","").strip()
        phone = request.POST.get("phone","").strip()
        password = request.POST.get("password","")
        role_id = request.POST.get("role")
        # ----------------------------------------------------
        # REQUIRED FIELDS
        # ----------------------------------------------------
        if not username or not password:
            messages.error(request,"Username and password are required.")
            return redirect("accounts:user_create")
        # ----------------------------------------------------
        # CHECK USERNAME
        # ----------------------------------------------------
        if User.objects.filter(username=username).exists():
            messages.error(request,"That username already exists.")
            return redirect("accounts:user_create")

        # ----------------------------------------------------
        # GET ROLE
        # ----------------------------------------------------

        role = Role.objects.filter(id=role_id).first()
        if role is None:
            messages.error(request,"Please select a valid role.")
            return redirect("accounts:user_create")
        # ----------------------------------------------------
        # CREATE USER
        # ----------------------------------------------------

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

    # --------------------------------------------------------
    # GET ROLES
    # --------------------------------------------------------

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


# ============================================================
# UPDATE USER
# ADMINISTRATOR ONLY
# ============================================================

@login_required
@role_required("Administrator")
def user_update(request, pk):

    user = get_object_or_404(
        User,
        pk=pk
    )

    if request.method == "POST":
        user.first_name = request.POST.get("first_name","").strip()
        user.last_name = request.POST.get("last_name","").strip()
        user.email = request.POST.get("email","").strip()
        user.phone = request.POST.get("phone","").strip()
        role_id = request.POST.get("role")

        # ----------------------------------------------------
        # GET ROLE
        # ----------------------------------------------------

        role = Role.objects.filter(id=role_id).first()
        if role is None:
            messages.error(request,"Please select a valid role.")
            return redirect("accounts:user_update",pk=user.pk)
        user.role = role
        user.save()
        messages.success(request,"User updated successfully.")
        return redirect("accounts:user_list")

    # --------------------------------------------------------
    # GET ROLES
    # --------------------------------------------------------

    roles = Role.objects.all().order_by("name")
    return render(request,"accounts/user_form.html",{"user_account": user,"roles": roles,})


# ============================================================
# DEACTIVATE USER
# ADMINISTRATOR ONLY
# ============================================================

@login_required
@role_required("Administrator")
def user_deactivate(request, pk):
    user = get_object_or_404(User,pk=pk)
    # --------------------------------------------------------
    # PREVENT ADMIN FROM DEACTIVATING THEMSELVES
    # --------------------------------------------------------

    if user == request.user:
        messages.error(request,"You cannot deactivate your own account.")
        return redirect("accounts:user_list")

    # --------------------------------------------------------
    # DEACTIVATE
    # --------------------------------------------------------

    user.is_active = False
    user.save(update_fields=["is_active"])
    messages.success(request,f"User {user.username} has been deactivated.")
    return redirect("accounts:user_list")
# ============================================================
# CHANGE PASSWORD
# ============================================================

@login_required
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(
            request.user,
            request.POST
        )
        if form.is_valid():
            user = form.save()
            # Keep the user logged in after
            # changing their password.
            update_session_auth_hash(
                request,
                user
            )

            messages.success(
                request,
                "Your password has been changed successfully."
            )

            # Send them back through the central
            # role-based dashboard.
            return redirect("dashboard:dashboard")
    else:
        form = PasswordChangeForm(request.user)
    return render(request,"accounts/change_password.html",{"form": form})
#-----------------------------------------------------
#seetings
#------------------------------------------------------
@login_required
def settings_view(request):

    return render(
        request,
        "accounts/settings.html"
    )