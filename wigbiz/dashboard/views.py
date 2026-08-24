from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect


@login_required
def dashboard(request):

    if not request.user.role:
        return redirect("accounts:no_role")

    role = request.user.role.name

    if role == "Administrator":

        return render(
            request,
            "administrator/dashboard.html"
        )

    if role == "Manager":

        return render(
            request,
            "manager/dashboard.html"
        )

    if role == "Salesperson":

        return render(
            request,
            "salesperson/dashboard.html"
        )

    if role == "Inventory Staff":

        return render(
            request,
            "inventorystaff/dashboard.html"
        )

    if role == "Accountant":

        return render(
            request,
            "accountant/dashboard.html"
        )

    return redirect("accounts:no_role")