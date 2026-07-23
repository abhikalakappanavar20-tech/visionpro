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
    path('scan/delete/<int:scan_id>/', views.delete_scan, name='delete_scan'),

    # Authentication URLs
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/change-password/', views.change_password, name='change_password'),
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/question/<str:username>/', views.password_reset_question, name='password_reset_question'),
    path('password-reset/complete/', views.password_reset_complete, name='password_reset_complete'),

    # Custom Admin Panel (gated by is_staff; uses the same /login/ form)
    path('admin-panel/', views.admin_panel_dashboard, name='admin_panel_dashboard'),
    path('admin-panel/users/', views.admin_panel_users, name='admin_panel_users'),
    path('admin-panel/users/<int:user_id>/', views.admin_panel_user_detail, name='admin_panel_user_detail'),
    path('admin-panel/users/<int:user_id>/action/', views.admin_panel_user_action, name='admin_panel_user_action'),
    path('admin-panel/scans/', views.admin_panel_scans, name='admin_panel_scans'),
    path('admin-panel/scans/<int:scan_id>/delete/', views.admin_panel_scan_delete, name='admin_panel_scan_delete'),
    path('admin-panel/reports/', views.admin_panel_reports, name='admin_panel_reports'),
    path('admin-panel/reports/<int:report_id>/action/', views.admin_panel_report_action, name='admin_panel_report_action'),
]
