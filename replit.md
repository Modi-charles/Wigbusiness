# WigBiz ERP

## Run on Replit

The project is a Django application in `wigbiz/`. The `Start application`
workflow runs:

```text
cd wigbiz && python manage.py runserver 0.0.0.0:5000
```

Dependencies are listed in `requirements.txt`. The app uses the included
SQLite database for development and reads `SESSION_SECRET` for Django's
secret key.

## Recent workflow behavior

- Sales can be completed without selecting a customer; the form labels this
  as a walk-in customer.
- Selecting a product fills its barcode, and entering a barcode in a sale row
  fills the matching product.
- Salespeople submit returns for manager approval. Inventory is updated only
  when a manager approves, and refund processing is manager-only.
- Saving a purchase takes the user directly to the payment form, where the
  purchase can be paid in full or partially.