from django.urls import path

from . import views

app_name = 'residents'

urlpatterns = [
    path('', views.ResidentListView.as_view(), name='resident_list'),
    path('new/', views.ResidentCreateView.as_view(), name='resident_create'),
    path('<int:pk>/', views.ResidentDetailView.as_view(), name='resident_detail'),
    path('<int:pk>/edit/', views.ResidentUpdateView.as_view(), name='resident_update'),
    path('<int:pk>/delete/', views.ResidentDeleteView.as_view(), name='resident_delete'),
]
