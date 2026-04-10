"""
URL configuration for core app
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('scan/', views.scan, name='scan'),
    path('scan/url/', views.scan_url, name='scan_url'),
    path('webcam/', views.webcam, name='webcam'),
    path('result/<int:scan_id>/', views.result, name='result'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('report/', views.report_content, name='report'),
    path('report/<int:scan_id>/', views.report_content, name='report_scan'),
    path('history/', views.history, name='history'),
    path('api/stats/', views.api_stats, name='api_stats'),

    # Authentication URLs
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile, name='profile'),
]
