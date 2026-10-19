from django.urls import reverse

from accounts.models import User
from notifications.models import Notification


def _display_name(user):
    """Readable name for a user, or a fallback if the user was deleted."""
    if user is None:
        return "Someone"
    return user.get_full_name() or str(user)


def _notify_managers(title, message, url, sale_return):
    managers = User.objects.filter(role__name="Manager", is_active=True)
    Notification.objects.bulk_create([
        Notification(
            recipient=manager,
            notification_type=Notification.NotificationType.RETURN,
            title=title,
            message=message,
            action_url=url,
            metadata={"return_id": sale_return.pk},
        )
        for manager in managers
    ])


def notify_managers_return_requested(sale_return):
    """A salesperson requested a return -> tell every active Manager."""
    _notify_managers(
        title=f"Return {sale_return.return_number} needs approval",
        message=(
            f"{_display_name(sale_return.created_by)} requested a return "
            f"for invoice {sale_return.sale.invoice_number}."
        ),
        url=reverse("sales:return_approval_detail", args=[sale_return.pk]),
        sale_return=sale_return,
    )


def notify_return_decision(sale_return, approved):
    """A manager approved or rejected -> tell the salesperson who asked."""
    recipient = sale_return.created_by
    if recipient is None:
        return

    if approved:
        title = f"Return {sale_return.return_number} approved"
        message = "Your return was approved. Open it and click 'Return Product' to finish."
    else:
        title = f"Return {sale_return.return_number} rejected"
        message = f"Your return was rejected. Reason: {sale_return.rejection_reason or 'not given'}."

    Notification.objects.create(
        recipient=recipient,
        notification_type=Notification.NotificationType.RETURN,
        title=title,
        message=message,
        action_url=reverse("sales:return_detail", args=[sale_return.pk]),
        metadata={"return_id": sale_return.pk},
    )


def notify_return_completed(sale_return):
    """The salesperson returned the product -> tell the managers."""
    _notify_managers(
        title=f"Return {sale_return.return_number} completed",
        message=(
            f"{_display_name(sale_return.created_by)} returned the product for "
            f"invoice {sale_return.sale.invoice_number}. The refund has been recorded."
        ),
        url=reverse("sales:return_detail", args=[sale_return.pk]),
        sale_return=sale_return,
    )
