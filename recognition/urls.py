from django.urls import path

from . import views

app_name = 'recognition'

urlpatterns = [
    path('residents/<int:pk>/enroll/', views.FaceEnrollView.as_view(), name='face_enroll'),
    path('residents/<int:pk>/verify/', views.FaceVerifyView.as_view(), name='face_verify'),
]
