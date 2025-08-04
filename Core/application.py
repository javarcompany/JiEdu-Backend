from django.utils import timezone #type: ignore
from django.contrib.auth.models import Group #type: ignore
from django.core.mail import send_mail  #type: ignore
from django.http import JsonResponse   #type: ignore
import string
import random
from uuid import uuid4
from django.conf import settings #type: ignore
from datetime import timedelta

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