import datetime
import requests
from django.core.management.base import BaseCommand #type: ignore
from django.utils.dateparse import parse_datetime  #type: ignore
from Events.models import Event

from django.conf import settings #type: ignore

USER_SETTINGS = getattr(settings, 'GOOGLE_CONFIGS', None)

class Command(BaseCommand):
    help = "Sync Kenya public holidays from Google Calendar"

    def handle(self, *args, **kwargs):
        url = f"https://www.googleapis.com/calendar/v3/calendars/{USER_SETTINGS.get('CALENDAR_ID')}/events?key={USER_SETTINGS.get('API_KEY')}"
        response = requests.get(url)

        if response.status_code != 200:
            self.stdout.write(self.style.ERROR("Failed to fetch holidays"))
            return

        data = response.json().get("items", [])
        for item in data:
            title = item.get("summary")
            start = item["start"].get("date") or item["start"].get("dateTime")
            end = item["end"].get("date") or item["end"].get("dateTime")

            # Convert all-day dates into datetime
            start_dt = parse_datetime(start) or datetime.datetime.fromisoformat(start)
            end_dt = parse_datetime(end) or datetime.datetime.fromisoformat(end)

            event, created = Event.objects.get_or_create(
                title=title,
                start_datetime=start_dt,
                end_datetime=end_dt,
                visibility="public",
                event_type="holiday",
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"Added {title}"))
            else:
                self.stdout.write(self.style.WARNING(f"Already exists: {title}"))
