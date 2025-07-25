# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models #type: ignore

import numpy as np #type:ignore

# ==========================================================================================#
# ========================              BIOMETRICS MODULE          =========================#
class KnownFace(models.Model):
    regno = models.CharField(max_length=255, unique=True)
    image = models.ImageField(upload_to='face_images/')
    encoding = models.BinaryField(null=True, blank=True)  # Store encoded face data as JSON
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def save_encoding(self, encoding_array):
        """ Convert NumPy array to JSON and save it """
        """ self.encoding = json.dumps(encoding_array.tolist()) """

        """Save the encoding after serializing it."""
        """ self.encoding = pickle.dumps(encoding_array) """
        """ self.save() """

        self.encoding = np.array(encoding_array).tobytes()
        self.save()

    def get_encoding(self):
        """ Convert JSON string back to NumPy array """
        """ return np.array(json.loads(self.encoding)) """
    
        """Deserialize the encoding when retrieving it."""
        """ return pickle.loads(self.encoding) """
    
        return np.frombuffer(self.encoding)

    def __str__(self):
        return self.regno

class CameraDevice(models.Model):
    ROLE_CHOICES = [
        ("front", "Front Camera"),
        ("aux", "Auxiliary Camera"),
        ("side", "Side Camera"),
    ]

    name = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(unique=True)
    location_hint = models.CharField(max_length=255, blank=True, null=True)
    stream_url = models.URLField()
    stream_type = models.CharField(
        max_length=20,
        choices=[("mjpeg", "MJPEG"), ("hls", "HLS"), ("webrtc", "WebRTC")],
        default="mjpeg"
    )
    is_active = models.BooleanField(default=True)
    is_activated = models.BooleanField(default=False)
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    classroom = models.ForeignKey("Core.Classroom", on_delete=models.CASCADE, related_name="cameras")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.role}) - {self.classroom.name}"
