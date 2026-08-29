# WigBiz

This repository contains a Django business management application.

## Run on Replit

The app runs from the `wigbiz` directory with Django's development server:

```bash
cd wigbiz
python manage.py runserver 0.0.0.0:5000
```

The Replit workflow uses the same command and serves the preview on port 5000.
The project currently uses its existing SQLite database at `wigbiz/db.sqlite3`.

## Useful commands

```bash
cd wigbiz
python manage.py check
python manage.py migrate
python manage.py createsuperuser
```