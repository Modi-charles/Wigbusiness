from django.test import TestCase

from accounts.models import User

from .models import Notification
from .services import (
    create_notification,
    create_notifications,
    get_notifications_for_user,
)


class NotificationServiceTests(TestCase):
    def setUp(self):
        self.first_user = User.objects.create_user(
            username="notification-user-1",
            password="test-password",
        )
        self.second_user = User.objects.create_user(
            username="notification-user-2",
            password="test-password",
        )

    def test_create_notification_stores_notification_details(self):
        notification = create_notification(
            recipient=self.first_user,
            title="Low Stock",
            message="Shampoo is running low.",
            notification_type=Notification.NotificationType.LOW_STOCK,
            action_url="/inventory/",
            metadata={"product_id": 12},
        )

        self.assertEqual(notification.recipient, self.first_user)
        self.assertEqual(notification.notification_type, "low_stock")
        self.assertFalse(notification.is_read)
        self.assertEqual(notification.metadata, {"product_id": 12})

    def test_create_notifications_targets_each_recipient(self):
        created = create_notifications(
            recipients=[self.first_user, self.second_user],
            title="Expense",
            message="New expense recorded.",
            notification_type=Notification.NotificationType.EXPENSE,
        )

        self.assertEqual(len(created), 2)
        self.assertEqual(
            Notification.objects.filter(
                notification_type=Notification.NotificationType.EXPENSE,
            ).count(),
            2,
        )

    def test_get_notifications_can_filter_unread_and_limit(self):
        first = create_notification(
            recipient=self.first_user,
            title="Older",
            message="Older notification",
        )
        create_notification(
            recipient=self.first_user,
            title="Newer",
            message="Newer notification",
        )
        first.is_read = True
        first.save(update_fields=["is_read"])

        notifications = get_notifications_for_user(
            self.first_user,
            unread_only=True,
            limit=1,
        )

        self.assertEqual(notifications.count(), 1)
        self.assertEqual(notifications.first().title, "Newer")
        self.assertFalse(
            get_notifications_for_user(self.second_user).exists()
        )