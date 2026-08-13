from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator

from .models import Employee
from .forms import EmployeeForm


@login_required
def employee_list(request):

    query = request.GET.get("q", "").strip()

    status = request.GET.get(
        "status",
        "active"
    ).strip()


    # Get all employees
    employees = Employee.objects.select_related(
        "user"
    ).all()


    # =========================
    # STATUS FILTER
    # =========================

    if status == "active":

        employees = employees.filter(
            status=True
        )

    elif status == "inactive":

        employees = employees.filter(
            status=False
        )


    # =========================
    # SEARCH
    # =========================

    if query:

        employees = employees.filter(

            Q(employee_number__icontains=query)

            | Q(position__icontains=query)

            | Q(department__icontains=query)

            | Q(address__icontains=query)

            | Q(user__username__icontains=query)

            | Q(user__first_name__icontains=query)

            | Q(user__last_name__icontains=query)

            | Q(user__email__icontains=query)

        )


    # Newest employee information first
    employees = employees.order_by(
        "user__first_name",
        "user__last_name"
    )


    # =========================
    # SUMMARY
    # =========================

    total_employees = Employee.objects.count()

    active_employees = Employee.objects.filter(
        status=True
    ).count()

    inactive_employees = Employee.objects.filter(
        status=False
    ).count()


    # =========================
    # PAGINATION
    # =========================

    paginator = Paginator(
        employees,
        20
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )


    context = {
        "page_obj": page_obj,

        "query": query,

        "status": status,

        "total_employees": total_employees,

        "active_employees": active_employees,

        "inactive_employees": inactive_employees,
    }


    return render(
        request,
        "employees/employee_list.html",
        context
    )


@login_required
def employee_detail(request, pk):

    employee = get_object_or_404(
        Employee.objects.select_related("user"),
        pk=pk
    )

    return render(
        request,
        "employees/employee_detail.html",
        {
            "employee": employee
        }
    )


@login_required
def employee_create(request):

    if request.method == "POST":

        form = EmployeeForm(
            request.POST
        )

        if form.is_valid():

            employee = form.save()

            messages.success(
                request,
                "Employee added successfully."
            )

            return redirect(
                "employees:employee_detail",
                pk=employee.pk
            )

    else:

        form = EmployeeForm()


    return render(
        request,
        "employees/employee_form.html",
        {
            "form": form,
            "action": "Add"
        }
    )


@login_required
def employee_update(request, pk):

    employee = get_object_or_404(
        Employee,
        pk=pk
    )


    if request.method == "POST":

        form = EmployeeForm(
            request.POST,
            instance=employee
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Employee updated successfully."
            )

            return redirect(
                "employees:employee_detail",
                pk=employee.pk
            )

    else:

        form = EmployeeForm(
            instance=employee
        )


    return render(
        request,
        "employees/employee_form.html",
        {
            "form": form,
            "action": "Edit",
            "employee": employee
        }
    )


@login_required
def employee_delete(request, pk):

    employee = get_object_or_404(
        Employee,
        pk=pk
    )


    if request.method == "POST":

        employee.status = False

        employee.save(
            update_fields=["status"]
        )

        messages.success(
            request,
            "Employee deactivated successfully."
        )

        return redirect(
            "employees:employee_list"
        )


    return render(
        request,
        "employees/employee_confirm_delete.html",
        {
            "employee": employee
        }
    )