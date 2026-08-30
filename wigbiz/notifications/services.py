from django.db import transaction

from .models import Notification


def create_notification(
    *,
    recipient,
    title,
    message,
    notification_type=Notification.NotificationType.GENERAL,
    action_url="",
    metadata=None,
):
    """Create one notification for a specific user."""
    return Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        action_url=action_url,
        metadata=metadata or {},
    )


@transaction.atomic
def create_notifications(
    *,
    recipients,
    title,
    message,
    notification_type=Notification.NotificationType.GENERAL,
    action_url="",
    metadata=None,
):
    """Create the same notification for multiple users efficiently."""
    notifications = [
        Notification(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            action_url=action_url,
            metadata=metadata or {},
        )
        for recipient in recipients
    ]
    return Notification.objects.bulk_create(notifications)


def get_notifications_for_user(user, *, unread_only=False, limit=None):
    """Return a user's notifications in newest-first order."""
    notifications = Notification.objects.filter(recipient=user)

    if unread_only:
        notifications = notifications.filter(is_read=False)

    if limit is not None:
        notifications = notifications[:limit]

    return notifications