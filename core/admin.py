"""
Admin configuration for VeriVision
"""
from django.contrib import admin
from .models import MediaScan, ReportedContent, ForensicDatabase


@admin.register(MediaScan)
class MediaScanAdmin(admin.ModelAdmin):
    """Admin interface for MediaScan model"""
    list_display = [
        'id', 'user', 'file_type', 'scan_result', 'confidence_score',
        'trust_score', 'forensic_match', 'created_at'
    ]
    list_filter = ['file_type', 'scan_result', 'forensic_match', 'created_at']
    search_fields = ['original_filename', 'url']
    readonly_fields = [
        'created_at', 'processing_time', 'heatmap_data',
        'analysis_details'
    ]

    fieldsets = (
        ('File Information', {
            'fields': ('file', 'file_type', 'url', 'original_filename')
        }),
        ('Analysis Results', {
            'fields': ('scan_result', 'confidence_score', 'trust_score')
        }),
        ('Forensic Data', {
            'fields': ('forensic_match', 'forensic_first_seen',
                      'forensic_usage_count', 'forensic_context')
        }),
        ('Technical Details', {
            'fields': ('heatmap_data', 'analysis_details', 'processing_time'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'ip_address', 'user')
        }),
    )


@admin.register(ReportedContent)
class ReportedContentAdmin(admin.ModelAdmin):
    """Admin interface for ReportedContent model"""
    list_display = [
        'id', 'url_or_file_name', 'file_type', 'status',
        'created_at', 'reporter_email'
    ]
    list_filter = ['status', 'file_type', 'created_at']
    search_fields = ['url_or_file_name', 'reason', 'reporter_email']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Content Information', {
            'fields': ('scan', 'url_or_file_name', 'file_type')
        }),
        ('Report Details', {
            'fields': ('reason', 'reporter_email', 'additional_info')
        }),
        ('Moderation', {
            'fields': ('status', 'moderator_notes')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ForensicDatabase)
class ForensicDatabaseAdmin(admin.ModelAdmin):
    """Admin interface for ForensicDatabase model"""
    list_display = [
        'content_hash', 'content_type', 'first_seen',
        'usage_count', 'threat_level', 'known_campaigns'
    ]
    list_filter = ['content_type', 'threat_level', 'first_seen']
    search_fields = ['content_hash', 'context', 'known_campaigns']
