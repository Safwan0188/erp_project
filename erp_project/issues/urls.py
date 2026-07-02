from django.urls import path
from . import views

urlpatterns = [
    path('', views.issue_list, name='issue_list'),
    path('create/', views.issue_create, name='issue_create'),
    path('<int:pk>/', views.issue_detail, name='issue_detail'),
    path('edit/<int:pk>/', views.issue_edit, name='issue_edit'),
    path('delete/<int:pk>/', views.issue_delete, name='issue_delete'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('settings/', views.settings_page, name='settings_page'),
    path('notifications/', views.notification_list, name='notification_list'),
]