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

## Environment configuration

- `SESSION_SECRET`: optional in development, but should be set through Replit
  Secrets for a stable secret key.
- `DJANGO_DEBUG`: defaults to `true`; set to `false` for production-style
  security settings.
- `DJANGO_ALLOWED_HOSTS`: comma-separated hostnames; defaults to `*` for the
  Replit development preview.

## Useful commands

```bash
cd wigbiz
python manage.py check
python manage.py migrate
python manage.py createsuperuser
```