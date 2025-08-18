from rest_framework.views import APIView  #type: ignore
from rest_framework import viewsets, status, permissions #type: ignore
from rest_framework.response import Response #type: ignore
from rest_framework.decorators import api_view, permission_classes #type: ignore
from rest_framework.pagination import PageNumberPagination #type: ignore

from django.core.files.uploadedfile import InMemoryUploadedFile  #type: ignore
from django.http import StreamingHttpResponse, JsonResponse #type: ignore
from django.shortcuts import get_object_or_404  #type: ignore

import threading
import cv2  #type: ignore
import numpy as np #type: ignore
import face_recognition  #type: ignore
import requests

from Students.models import Student
from Staff.models import Staff
from Timetable.models import Timetable

from .models import *
from .application import *
from .filters import *
from .serializers import *

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'results': data,
            'page': self.page.number if hasattr(self, 'page') else None,
            'total_pages': self.page.paginator.num_pages if hasattr(self, 'page') else None,
            'count': self.page.paginator.count if hasattr(self, 'page') else None,
        })

class CameraViewSet(viewsets.ModelViewSet):
    queryset = CameraDevice.objects.all().order_by('id')
    serializer_class = CameraDeviceSerializer
    filter_backends = [ExtendedMultiKeywordSearchFilter]
    pagination_class = StandardResultsSetPagination

    def list(self, request, *args, **kwargs):
        if request.query_params.get('all') == 'true':
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response({'results': serializer.data})  # mimic paginated structure
        no_pagination = request.query_params.get('no_pagination')
        if no_pagination == 'true':
            self.pagination_class = None  # disables pagination for this request
            
        return super().list(request, *args, **kwargs)
    
class FaceEnrollView(APIView):
    def post(self, request):
        image_file: InMemoryUploadedFile = request.FILES.get("image")
        regno = request.data.get("regno")
        user_type = request.data.get("type")

        if not regno:
            return Response({"error": "Registration number (regno) is required"}, status=status.HTTP_400_BAD_REQUEST)

        if not user_type:
            return Response({"error": "User type is required"}, status=status.HTTP_400_BAD_REQUEST)

        if not image_file:
            return Response({"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate user existence
        if user_type.lower() == "student":
            if not Student.objects.filter(regno=regno).exists():
                return Response({"error": "Student NOT Found!"}, status=status.HTTP_404_NOT_FOUND)
        elif user_type.lower() == "staff":
            if not Staff.objects.filter(regno=regno).exists():
                return Response({"error": "Staff NOT Found!"}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({"error": "Invalid user type. Must be 'student' or 'staff'."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Read and decode image
            image_data = image_file.read()
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if image is None:
                return Response({"error": "Invalid image file"}, status=status.HTTP_400_BAD_REQUEST)

            # Convert to RGB for face_recognition
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Detect and encode face
            face_locations = face_recognition.face_locations(rgb_image)
            if len(face_locations) == 0:
                return Response({"error": "No face detected in the image"}, status=status.HTTP_400_BAD_REQUEST)

            face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
            if not face_encodings:
                return Response({"error": "Face could not be encoded"}, status=status.HTTP_400_BAD_REQUEST)

            encoding = face_encodings[0]

            # Save or update KnownFace record
            known_face, created = KnownFace.objects.get_or_create(regno=regno)
            known_face.image.save(image_file.name, image_file, save=False)
            known_face.encoding = np.array(encoding).tobytes()
            known_face.save()

            return Response({
                "message": "Face enrolled successfully",
                "regno": known_face.regno,
                "updated": not created,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"Server error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def camera_proxy_view(request, camera_id):
    camera = get_object_or_404(CameraDevice, id = camera_id)
    stream_url = f"http://{camera.ip_address}/video"  # adjust path

    def stream():
        with requests.get(stream_url, stream=True) as r:
            for chunk in r.iter_content(chunk_size=1024):
                yield chunk

    return StreamingHttpResponse(stream(), content_type="multipart/x-mixed-replace; boundary=frame")

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def activate_camera(request):
    try:
        lesson_id = request.data.get("lesson_id")
        if not lesson_id:
            raise Exception("Lesson ID is required")

        timetable = Timetable.objects.filter(id=lesson_id).first()
        if not timetable:
            raise Exception("Lesson not found")

        classroom = timetable.classroom
        if not classroom:
            raise Exception("Classroom not assigned to this lesson")

        cameras = classroom.cameras.filter(is_active=True)
        if not cameras.exists():
            raise Exception("No active cameras set for this classroom")

        messages = []
        for cam in cameras:
            try:
                # Try opening the stream to verify it's active
                cap = cv2.VideoCapture(cam.stream_url)
                if not cap.isOpened():
                    raise Exception("Stream not reachable")
                ret, frame = cap.read()
                cap.release()

                if not ret:
                    raise Exception("No frame received")
 
                cam.is_activated = True
                cam.save()
 
                # Start face recognition in background
                threading.Thread(
                    target=recognize_faces,
                    args=(lesson_id, cam.stream_url, f"{cam.classroom.name}_{cam.role}",),
                    daemon=True
                ).start()
 
                messages.append(f"{cam.role.capitalize()} camera activated")
 
            except Exception as e:
                cam.is_activated = False
                cam.save()
                messages.append(f"{cam.role.capitalize()} camera failed to activate: {str(e)}")

        return JsonResponse({
            "message": " | ".join(messages),
            "classroom": classroom.name,
            "cameras": [cam.name for cam in cameras]
        })

    except Exception as e:
        print("Camera Activation Error:", e)
        return JsonResponse({"error": str(e)}, status=500)

@api_view(['GET'])
def camera_count(request):
    count = CameraDevice.objects.count()
    return Response({"count": count})

