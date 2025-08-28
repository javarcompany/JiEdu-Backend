from django.urls import path, include #type: ignore
from rest_framework.routers import DefaultRouter #type: ignore
from .views import *

router = DefaultRouter()
router.register(r'events', EventViewSet, basename='event')
router.register(r'event-participants', EventParticipantViewSet, basename='event-participant')
router.register(r'event-reminders', EventReminderViewSet, basename='event-reminder')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/get-user-upcoming-events/', get_user_upcoming_events, name="get-user-upcoming-events"),
    path('api/get-user-events/', get_user_events, name="get-user-events"),
]
