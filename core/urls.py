from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('settings/', views.SiteSettingsUpdateView.as_view(), name='site_settings'),
    path('officials/', views.OfficialListView.as_view(), name='official_list'),
    path('officials/new/', views.OfficialCreateView.as_view(), name='official_create'),
    path('officials/<int:pk>/edit/', views.OfficialUpdateView.as_view(), name='official_update'),
]
