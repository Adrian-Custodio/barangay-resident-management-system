from django.contrib.auth import views as auth_views
from django.urls import path

app_name = 'accounts'

# Login/logout are Django's built-in auth views, not custom ones -- there's
# no non-standard behavior here (no email verification, no social login),
# so writing our own would just be re-implementing something the framework
# already gets right. We only supply our own template.
urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
