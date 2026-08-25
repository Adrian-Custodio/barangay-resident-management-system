from django.contrib import admin
from .models import FaceProfile, FaceVerificationAttempt

admin.site.register(FaceProfile)
admin.site.register(FaceVerificationAttempt)
