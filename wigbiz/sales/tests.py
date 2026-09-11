from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Role
from customers.models import Customer
from inventory.models import Inventory, InventoryTransaction
from products.models import Brand, Category, Product

from .forms import SaleItemForm
from .models import Sale, SaleReturn
from .returns import create_sale_return
from .services import create_sale


User = get_user_model()


class SalesWorkflowTests(TestCase):
    def setUp(self):
        self.cashier = User.objects.create_user(
            username="cashier",
            password="test-password",
        )
        self.manager = User.objects.create_user(
            username="manager",
            password="test-password",
            role=Role.objects.create(name="Manager"),
        )
        category = Category.objects.create(name="Wigs")
        brand = Brand.objects.create(name="Test Brand")
        self.product = Product.objects.create(
            category=category,
            brand=brand,
            product_code="WIG-001",
            barcode="123456789",
            name="Body Wave Wig",
            cost_price=Decimal("6.00"),
            selling_price=Decimal("10.00"),
        )
        self.inventory = Inventory.objects.create(
            product=self.product,
            quantity_available=10,
        )
        self.customer = Customer.objects.create(
            first_name="Jane",
            last_name="Customer",
            phone="0700000001",
        )
        self.client.force_login(self.cashier)

    def sale_payload(self, customer=""):
        return {
            "customer": customer,
            "discount": "0.00",
            "tax": "0.00",
            "payment_method": "CASH",
            "amount_paid": "20.00",
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-product": str(self.product.pk),
            "form-0-quantity": "2",
        }

    def test_sale_can_be_completed_without_a_customer(self):
        response = self.client.post(
            reverse("sales:create_sale"),
            self.sale_payload(),
        )

        self.assertEqual(response.status_code, 302)
        sale = Sale.objects.get()
        self.assertIsNone(sale.customer)
        self.assertEqual(sale.status, Sale.Status.COMPLETED)
        self.assertEqual(sale.total_amount, Decimal("20.00"))
        self.assertEqual(sale.paid_amount, Decimal("20.00"))
        self.assertEqual(sale.balance, Decimal("0.00"))
        self.assertEqual(sale.items.get().quantity, 2)
        self.assertEqual(
            Inventory.objects.get(product=self.product).quantity_available,
            8,
        )

    def test_sale_can_be_completed_for_a_customer(self):
        response = self.client.post(
            reverse("sales:create_sale"),
            self.sale_payload(customer=str(self.customer.pk)),
        )

        self.assertEqual(response.status_code, 302)
        sale = Sale.objects.get()
        self.assertEqual(sale.customer, self.customer)
        self.assertEqual(sale.items.get().product, self.product)

    def test_product_selection_exposes_price_and_barcode_and_barcode_lookup(self):
        form = SaleItemForm(
            data={
                "product": str(self.product.pk),
                "quantity": "1",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        rendered_product_select = form["product"].as_widget()
        self.assertIn('data-price="10.00"', rendered_product_select)
        self.assertIn('data-barcode="123456789"', rendered_product_select)

        response = self.client.get(
            reverse("sales:product_by_barcode"),
            {"barcode": self.product.barcode},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "success": True,
                "product": {
                    "id": self.product.pk,
                    "name": self.product.name,
                    "barcode": self.product.barcode,
                    "selling_price": "10.00",
                },
            },
        )

    def test_return_waits_for_manager_approval_before_updating_inventory(self):
        sale = create_sale(
            customer=self.customer,
            created_by=self.cashier,
            items=[{"product": self.product, "quantity": 2}],
            payment_method="CASH",
            amount_paid=Decimal("20.00"),
        )
        sale_item = sale.items.get()
        sale_return = create_sale_return(
            sale=sale,
            created_by=self.cashier,
            items=[{"sale_item": sale_item, "quantity": 1}],
            reason="Customer changed their mind",
        )

        inventory = Inventory.objects.get(product=self.product)
        self.assertEqual(inventory.quantity_available, 8)
        self.assertEqual(inventory.quantity_sold, 2)
        self.assertEqual(sale_return.status, SaleReturn.Status.PENDING)
        self.assertFalse(
            InventoryTransaction.objects.filter(
                transaction_type="RETURN",
                reference_id=sale_return.pk,
            ).exists()
        )

        self.client.force_login(self.manager)
        response = self.client.post(
            reverse("sales:approve_return", args=[sale_return.pk]),
        )

        self.assertEqual(
            response.url,
            reverse("sales:return_approval_list"),
        )
        sale_return.refresh_from_db()
        inventory.refresh_from_db()
        self.assertEqual(sale_return.status, SaleReturn.Status.COMPLETED)
        self.assertEqual(inventory.quantity_available, 9)
        self.assertEqual(inventory.quantity_sold, 1)
        self.assertEqual(
            InventoryTransaction.objects.filter(
                transaction_type="RETURN",
                reference_id=sale_return.pk,
            ).count(),
            1,
        )
