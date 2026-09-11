from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from products.models import Brand, Category, Product
from suppliers.models import Supplier

from .models import Purchase, PurchasePayment


User = get_user_model()


class PurchaseWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="purchaser",
            password="test-password",
        )
        category = Category.objects.create(name="Wigs")
        brand = Brand.objects.create(name="Test Brand")
        self.product = Product.objects.create(
            category=category,
            brand=brand,
            product_code="WIG-001",
            barcode="987654321",
            name="Straight Wig",
            cost_price=Decimal("8.00"),
            selling_price=Decimal("15.00"),
        )
        self.supplier = Supplier.objects.create(
            name="Test Supplier",
            phone="0700000002",
        )
        self.client.force_login(self.user)

    def purchase_payload(self, invoice_number="PUR-001"):
        return {
            "supplier": str(self.supplier.pk),
            "invoice_number": invoice_number,
            "purchase_date": "2026-09-11",
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "1000",
            "items-0-product": str(self.product.pk),
            "items-0-quantity": "3",
            "items-0-cost_price": "12.00",
        }

    def create_purchase(self, invoice_number="PUR-001"):
        response = self.client.post(
            reverse("purchase:add_purchase"),
            self.purchase_payload(invoice_number),
        )
        self.assertEqual(response.status_code, 302)
        return Purchase.objects.get(invoice_number=invoice_number)

    def test_purchase_creation_redirects_to_payment_form(self):
        response = self.client.post(
            reverse("purchase:add_purchase"),
            self.purchase_payload(),
        )

        purchase = Purchase.objects.get(invoice_number="PUR-001")
        self.assertEqual(
            response.url,
            reverse("purchase:add_purchase_payment", args=[purchase.pk]),
        )
        self.assertEqual(purchase.total_amount, Decimal("36.00"))
        self.assertEqual(purchase.balance, Decimal("36.00"))
        self.assertEqual(purchase.payment_status, "UNPAID")
        self.assertEqual(purchase.items.get().quantity, 3)
        self.assertEqual(purchase.items.get().subtotal, Decimal("36.00"))

    def test_purchase_can_be_paid_in_full(self):
        purchase = self.create_purchase()

        response = self.client.post(
            reverse("purchase:add_purchase_payment", args=[purchase.pk]),
            {
                "amount": "36.00",
                "payment_method": "CASH",
                "reference": "FULL-PAYMENT",
            },
        )

        self.assertEqual(
            response.url,
            reverse("purchase:purchase_details", args=[purchase.pk]),
        )
        purchase.refresh_from_db()
        self.assertEqual(purchase.paid_amount, Decimal("36.00"))
        self.assertEqual(purchase.balance, Decimal("0.00"))
        self.assertEqual(purchase.payment_status, "PAID")
        self.assertEqual(
            PurchasePayment.objects.get(purchase=purchase).amount,
            Decimal("36.00"),
        )

    def test_purchase_can_be_paid_partially(self):
        purchase = self.create_purchase()

        response = self.client.post(
            reverse("purchase:add_purchase_payment", args=[purchase.pk]),
            {
                "amount": "10.00",
                "payment_method": "MOBILE_MONEY",
                "reference": "PARTIAL-PAYMENT",
            },
        )

        self.assertEqual(
            response.url,
            reverse("purchase:purchase_details", args=[purchase.pk]),
        )
        purchase.refresh_from_db()
        self.assertEqual(purchase.paid_amount, Decimal("10.00"))
        self.assertEqual(purchase.balance, Decimal("26.00"))
        self.assertEqual(purchase.payment_status, "PARTIAL")
        self.assertEqual(
            PurchasePayment.objects.get(purchase=purchase).payment_method,
            "MOBILE_MONEY",
        )
