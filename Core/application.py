from .models import *
from django.utils import timezone #type: ignore
from django.contrib.auth.models import Group #type: ignore
from django.core.mail import send_mail  #type: ignore
from django.http import JsonResponse   #type: ignore
import string
import random
from uuid import uuid4
from django.conf import settings #type: ignore
from datetime import timedelta

def generate_password(length=8):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choices(chars, k=length))

def generate_username(app):
    return app.email.split('@')[0] + str(app.pk)
