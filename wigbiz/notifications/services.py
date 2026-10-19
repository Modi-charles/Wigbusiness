from django.contrib.auth import get_user_model

from .models import Notification


def create_notification(
    recipient,
    title,
    message,
    action_url="",
    notification_type=Notification.NotificationType.GENERAL,
    metadata=None,
):
    return Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        action_url=action_url,
        metadata=metadata or {},
    )


def notify_role(role_name, title, message, action_url="", notification_type=Notification.NotificationType.GENERAL, metadata=None, exclude=None):
    """Send one notification to every active user holding the given role.

    Returns the number of notifications created.
    """
    User = get_user_model()
    recipients = User.objects.filter(is_active=True, role__name__iexact=role_name)
    if exclude is not None:
        recipients = recipients.exclude(pk=exclude.pk)

    notifications = [
        Notification(
            recipient=user,
            notification_type=notification_type,
            title=title,
            message=message,
            action_url=action_url,
            metadata=metadata or {},
        )
        for user in recipients
    ]
    Notification.objects.bulk_create(notifications)
    return len(notifications)