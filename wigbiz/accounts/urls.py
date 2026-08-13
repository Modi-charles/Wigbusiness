from django.urls import path

from . import views


app_name = "accounts"


urlpatterns = [

    path(
        "login/",
        views.login_view,
        name="login"
    ),

    path(
        "logout/",
        views.logout_view,
        name="logout"
    ),

    path(
        "no-role/",
        views.no_role,
        name="no_role"
    ),

    path(
        "users/",
        views.user_list,
        name="user_list"
    ),

    path(
        "users/add/",
        views.user_create,
        name="user_create"
    ),

    path(
        "users/<int:pk>/edit/",
        views.user_update,
        name="user_update"
    ),

    path(
        "users/<int:pk>/deactivate/",
        views.user_deactivate,
        name="user_deactivate"
    ),

    path(
        "change-password/",
        views.change_password,
        name="change_password"
    ),

]