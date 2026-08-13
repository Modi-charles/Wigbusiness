from django.core.management.base import BaseCommand

from accounts.models import Role


class Command(BaseCommand):

    help = "Create default system roles"

    def handle(self, *args, **options):

        roles = [
            {
                "name": "Administrator",
                "description": "Full access to the entire system.",
            },
            {
                "name": "Manager",
                "description": "Access to business operations and reports.",
            },
            {
                "name": "Salesperson",
                "description": "Handles sales and customers.",
            },
            {
                "name": "Inventory Staff",
                "description": "Handles products, inventory and stock receiving.",
            },
            {
                "name": "Accountant",
                "description": "Handles payments, balances and financial reports.",
            },
        ]

        for role_data in roles:

            role, created = Role.objects.get_or_create(
                name=role_data["name"],
                defaults={
                    "description": role_data["description"]
                }
            )

            if created:

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created role: {role.name}"
                    )
                )

            else:

                self.stdout.write(
                    f"Role already exists: {role.name}"
                )