from .models import Notification


def unread_notifications(request):
    """Makes `unread_notifications_count` available in every template (for the bell)."""
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        return {
            "unread_notifications_count": Notification.objects.filter(
                recipient=user, is_read=False
            ).count()
        }
    return {"unread_notifications_count": 0}