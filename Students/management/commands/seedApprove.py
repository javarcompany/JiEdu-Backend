import requests
from django.core.management.base import BaseCommand #type: ignore
from Students.models import Application
from Students.application import approve_application, decline_application
from Core.models import Institution

class Command(BaseCommand):
    help = "Enroll all approved applications by calling the enroll endpoint"


    def handle(self, *args, **options):
        current_intake = Institution.objects.first().current_intake
        applications = Application.objects.filter(intake = current_intake)

        if not applications.exists():
            self.stdout.write(self.style.WARNING("No application(s) found."))
            return
        counter = 1
        for app in applications:
            try:
                if counter % 10 == 0:
                    response = decline_application(app.id) # change to .post if your API expects POST
                else: 
                    response = approve_application(app.id) # change to .post if your API expects POST

                self.stdout.write(
                    f"{response}"
                )
            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.ERROR(f"Error with {app.id}: {e}"))
