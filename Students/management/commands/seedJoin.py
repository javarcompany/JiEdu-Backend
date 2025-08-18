import requests
from django.core.management.base import BaseCommand #type: ignore
from Students.models import Application

class Command(BaseCommand):
    help = "Enroll all approved applications by calling the enroll endpoint"

    def handle(self, *args, **options):
        BASE_URL = "http://127.0.0.1:8000/application/enroll/"

        applications = Application.objects.filter(state="Approved")

        if not applications.exists():
            self.stdout.write(self.style.WARNING("No approved applications found."))
            return

        for app in applications:
            regno = app.regno.split("/")[-1]
            url = f"{BASE_URL}{regno}/"
            try:
                response = requests.get(url)  # change to .post if your API expects POST
                self.stdout.write(
                    f"Regno: {regno} | Status: {response.status_code} | Response: {response.text[:100]}"
                )
            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.ERROR(f"Error with {regno}: {e}"))
