from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notification_list(request):
    show = request.GET.get("show", "all")
    notifications = Notification.objects.filter(recipient=request.user)
    if show == "unread":
        notifications = notifications.filter(is_read=False)

    page_obj = Paginator(notifications, 20).get_page(request.GET.get("page"))

    # Attach the live expense status to expense notifications (Pending / Approved / Rejected)
    from expenses.models import Expense  # imported here to keep the apps loosely coupled

    expense_ids = [
        n.metadata.get("expense_id")
        for n in page_obj
        if isinstance(n.metadata, dict) and n.metadata.get("expense_id")
    ]
    statuses = dict(
        Expense.objects.filter(pk__in=expense_ids).values_list("pk", "status")
    )
    for n in page_obj:
        expense_id = n.metadata.get("expense_id") if isinstance(n.metadata, dict) else None
        n.expense_status = statuses.get(expense_id)

    return render(
        request,
        "notifications/notification_list.html",
        {"page_obj": page_obj, "show": show},
    )
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Notification


def _meta_ids(page_obj, key):
    ids = []
    for n in page_obj:
        if isinstance(n.metadata, dict) and n.metadata.get(key):
            ids.append(n.metadata[key])
    return ids


@login_required
def notification_list(request):
    show = request.GET.get("show", "all")
    notifications = Notification.objects.filter(recipient=request.user)
    if show == "unread":
        notifications = notifications.filter(is_read=False)

    page_obj = Paginator(notifications, 20).get_page(request.GET.get("page"))

    # Imported here to keep the apps loosely coupled
    from expenses.models import Expense
    from sales.models import SaleReturn

    expense_statuses = dict(
        Expense.objects
        .filter(pk__in=_meta_ids(page_obj, "expense_id"))
        .values_list("pk", "status")
    )
    return_statuses = dict(
        SaleReturn.objects
        .filter(pk__in=_meta_ids(page_obj, "return_id"))
        .values_list("pk", "status")
    )

    # Attach the LIVE status so the Status column is always current
    for n in page_obj:
        meta = n.metadata if isinstance(n.metadata, dict) else {}
        n.expense_status = expense_statuses.get(meta.get("expense_id"))
        n.return_status = return_statuses.get(meta.get("return_id"))

    return render(
        request,
        "notifications/notification_list.html",
        {"page_obj": page_obj, "show": show},
    )


@login_required
def notification_open(request, pk):
    """Mark one notification as read, then go to the page it points at."""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=["is_read", "read_at"])

    # Only follow site-relative links we created ourselves
    if notification.action_url.startswith("/") and not notification.action_url.startswith("//"):
        return redirect(notification.action_url)
    return redirect("notifications:notification_list")


@login_required
@require_POST
def notification_mark_all_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(
        is_read=True, read_at=timezone.now()
    )
    messages.success(request, "All notifications marked as read.")
    return redirect("notifications:notification_list")


@login_required
def notification_open(request, pk):
    """Mark one notification as read, then go to the page it points at."""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=["is_read", "read_at"])

    # Only follow site-relative links we created ourselves
    if notification.action_url.startswith("/"):
        return redirect(notification.action_url)
    return redirect("notifications:notification_list")


@login_required
@require_POST
def notification_mark_all_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(
        is_read=True, read_at=timezone.now()
    )
    messages.success(request, "All notifications marked as read.")
    return redirect("notifications:notification_list")