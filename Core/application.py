import string
import random
from datetime import timedelta, datetime
import calendar
from django.utils.timezone import make_aware #type: ignore

from .models import *

def generate_password(length=8):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choices(chars, k=length))

def generate_username(app):
    return app.email.split('@')[0] + str(app.pk)

def get_or_create_module_by_name(module_input_name: str):
    # Normalize the input
    name_cleaned = module_input_name.strip().lower()

    # Map possible user inputs to canonical module name and abbreviation
    module_mapping = {
        '1': ('Module One', 'M1'),
        'one': ('Module One', 'M1'),
        'module one': ('Module One', 'M1'),
        'module 1': ('Module One', 'M1'),

        '2': ('Module Two', 'M2'),
        'two': ('Module Two', 'M2'),
        'module two': ('Module Two', 'M2'),
        'module 2': ('Module Two', 'M2'),

        '3': ('Module Three', 'M3'),
        'three': ('Module Three', 'M3'),
        'module three': ('Module Three', 'M3'),
        'module 3': ('Module Three', 'M3'),

        '4': ('Module Four', 'M4'),
        'four': ('Module Four', 'M4'),
        'module four': ('Module Four', 'M4'),
        'module 4': ('Module Four', 'M4'),

        '5': ('Module Five', 'M5'),
        'five': ('Module Five', 'M5'),
        'module five': ('Module Five', 'M5'),
        'module 5': ('Module Five', 'M5'),
    }

    # Resolve the intended canonical name/abbr
    module_data = module_mapping.get(name_cleaned)

    if not module_data:
        raise ValueError(f"Unrecognized module name: '{module_input_name}'")

    canonical_name, abbr = module_data

    # Try to find existing module
    module = Module.objects.filter(name__iexact=canonical_name).first()
    if not module:
        module = Module.objects.create(name=canonical_name, abbr=abbr)

    return module  # or return module.id if only ID is needed

def get_opening_date(year: int, month_name: str):
    month = list(calendar.month_name).index(month_name)
    d = datetime(year, month, 1)
    # Move to the second Monday
    mondays = [d + timedelta(days=i) for i in range(31) if (d + timedelta(days=i)).month == month and (d + timedelta(days=i)).weekday() == 0]
    return make_aware(mondays[1]) if len(mondays) > 1 else make_aware(mondays[0])

def get_closing_date(year: int, month_name: str):
    month = list(calendar.month_name).index(month_name)
    last_day = calendar.monthrange(year, month)[1]
    d = datetime(year, month, last_day)
    # Move backward to the last Friday
    while d.weekday() != 4:  # 4 = Friday
        d -= timedelta(days=1)
    return make_aware(d)