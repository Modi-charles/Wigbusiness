# core/utils.py
from datetime import datetime


def parse_date_or_none(value):
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def build_querystring(request, exclude=None):
    """
    Return the current GET params as a query string, with the given
    keys removed. Used to rebuild links (period toggles, pagination)
    without duplicating a param that's about to be re-added.
    """
    exclude = exclude or []
    params = request.GET.copy()
    for key in exclude:
        params.pop(key, None)
    return params.urlencode()