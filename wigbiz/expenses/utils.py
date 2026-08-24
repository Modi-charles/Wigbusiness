from .models import Expense


def generate_expense_number():
    last_expense = Expense.objects.order_by("-id").first()

    if last_expense is None:
        return "EXP-000001"

    last_number = last_expense.expense_number

    number = int(last_number.split("-")[1])

    number += 1

    return f"EXP-{number:06d}"