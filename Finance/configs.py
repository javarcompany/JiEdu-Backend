from django.conf import settings #type: ignore
from rest_framework.settings import APISettings #type: ignore

USER_SETTINGS = getattr(settings, 'MPESA_CONFIG', None)

# Detect environment: 'sandbox' or 'production'
MPESA_ENV = USER_SETTINGS.get('MPESA_ENV').lower()

# Base URLs for environments
MPESA_BASE_URLS = {
    'sandbox': 'https://sandbox.safaricom.co.ke',
    'production': 'https://api.safaricom.co.ke'
}

DEFAULTS = {
    'MPESA_CONSUMER_KEY': None,
    'MPESA_CONSUMER_SECRET': None,
    'CERTIFICATE_FILE': None,
    'MPESA_CALLBACK_URL': '',
    'MPESA_PASSKEY': None,
    'MPESA_SHORTCODE': None,
    'TRANSACTION_TYPE': 'CustomerPayBillOnline',
    'ENV': MPESA_ENV,  # can be "sandbox" or "production"
    'SAFARICOM_API': MPESA_BASE_URLS.get(MPESA_ENV, MPESA_BASE_URLS['sandbox']),
}

api_settings = APISettings(USER_SETTINGS, DEFAULTS, None)


