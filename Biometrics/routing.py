from django.urls import path #type: ignore
from .consumers import AttendanceConsumer

websocket_urlpatterns = [
    path("fr/attendance/", AttendanceConsumer.as_asgi()),
]