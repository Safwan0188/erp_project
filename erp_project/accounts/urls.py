from django.urls import path
from . import views

urlpatterns = [
    path('login-as/', views.login_as, name='login_as'),
    path('logout/', views.logout_view, name='logout'),
    path('user-management/', views.user_management, name='user_management'),
]