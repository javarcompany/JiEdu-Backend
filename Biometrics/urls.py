from django.urls import path, include  #type: ignore
from rest_framework.routers import DefaultRouter #type: ignore
from .views import *

router = DefaultRouter()
router.register(r'cameras', CameraViewSet, basename='cameras')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/enroll-face/', FaceEnrollView.as_view(), name='enroll-face'),
    path('api/face-attendance/', activate_camera, name = "face-attendance"),

]
