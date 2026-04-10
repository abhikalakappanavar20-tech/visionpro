"""
Database Models for VeriVision
"""
from django.db import models
from django.core.validators import URLValidator, MinValueValidator, MaxValueValidator
import os
import json


def validate_score_range(value):
    """Validate that score is between 0 and 100"""
    if not (0 <= value <= 100):
        raise ValidationError(f'Score must be between 0 and 100, got {value}')


from django.core.exceptions import ValidationError


def upload_path(instance, filename):
    """Generate upload path based on file type"""
    ext = os.path.splitext(filename)[1].lower()
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
        return f'images/{filename}'
    elif ext in ['.mp4', '.avi', '.mov', '.mkv']:
        return f'videos/{filename}'
    elif ext in ['.wav', '.mp3', '.m4a', '.flac']:
        return f'audio/{filename}'
    return f'uploads/{filename}'


class MediaScan(models.Model):
    """
    Store information about media scans for deepfake detection
    """
    FILE_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('url', 'Social Media URL'),
    ]

    SCAN_RESULT_CHOICES = [
        ('real', 'Real'),
        ('suspicious', 'Suspicious'),
        ('fake', 'Fake'),
    ]

    # File information
    file = models.FileField(upload_to=upload_path, null=True, blank=True)
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES)
    url = models.URLField(null=True, blank=True, help_text="Social media URL if applicable")
    original_filename = models.CharField(max_length=255, null=True, blank=True)

    # Analysis results
    scan_result = models.CharField(max_length=15, choices=SCAN_RESULT_CHOICES)
    confidence_score = models.FloatField(
        help_text="AI confidence percentage (0-100)",
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    trust_score = models.IntegerField(
        help_text="Trust score (0-100)",
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    # Forensic data
    forensic_match = models.BooleanField(default=False, help_text="Found in historical database")
    forensic_first_seen = models.DateField(null=True, blank=True)
    forensic_usage_count = models.IntegerField(default=0)
    forensic_context = models.TextField(null=True, blank=True)

    # XAI Heatmap data (stored as JSON string)
    heatmap_data = models.JSONField(default=dict, help_text="Heatmap coordinates for visualization")

    # Analysis details
    analysis_details = models.JSONField(default=dict, help_text="Detailed analysis metrics")
    processing_time = models.FloatField(help_text="Processing time in seconds")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return f"MediaScan {self.id} - {self.scan_result} ({self.confidence_score}%)"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Media Scan"
        verbose_name_plural = "Media Scans"


class ReportedContent(models.Model):
    """
    Store user-reported suspicious content
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('under_review', 'Under Review'),
        ('verified_fake', 'Verified as Fake'),
        ('verified_real', 'Verified as Real'),
        ('dismissed', 'Dismissed'),
    ]

    # Link to scan or standalone report
    scan = models.ForeignKey(MediaScan, on_delete=models.SET_NULL, null=True, blank=True)

    # Content information
    url_or_file_name = models.CharField(max_length=500)
    file_type = models.CharField(max_length=10, choices=MediaScan.FILE_TYPE_CHOICES)

    # Report details
    reason = models.TextField(help_text="Why this content is being reported")
    reporter_email = models.EmailField(null=True, blank=True)
    additional_info = models.TextField(null=True, blank=True)

    # Moderation
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    moderator_notes = models.TextField(null=True, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Report {self.id} - {self.status}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Reported Content"
        verbose_name_plural = "Reported Content"


class ForensicDatabase(models.Model):
    """
    Mock forensic database of known manipulated media
    """
    CONTENT_TYPE = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Audio'),
    ]

    content_hash = models.CharField(max_length=64, unique=True)
    content_type = models.CharField(max_length=10, choices=CONTENT_TYPE)
    first_seen = models.DateField()
    usage_count = models.IntegerField(default=1)
    context = models.TextField()
    known_campaigns = models.CharField(max_length=255, null=True, blank=True)
    threat_level = models.CharField(max_length=20, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], default='medium')

    def __str__(self):
        return f"Forensic Entry {self.content_hash[:8]} - {self.threat_level}"

    class Meta:
        verbose_name = "Forensic Database Entry"
        verbose_name_plural = "Forensic Database Entries"


class AIGeneratorSignature(models.Model):
    """
    Store known AI generator signatures for source detection
    """
    GENERATOR_TYPE_CHOICES = [
        ('image', 'Image Generator'),
        ('video', 'Video Generator'),
        ('audio', 'Audio Generator'),
        ('manipulation', 'Manipulation Tool'),
    ]

    # Basic information
    name = models.CharField(max_length=100, help_text="e.g., 'Midjourney v5', 'DALL-E 3'")
    generator_type = models.CharField(max_length=20, choices=GENERATOR_TYPE_CHOICES)

    # Signature characteristics
    typical_resolutions = models.JSONField(
        help_text="List of common resolutions, e.g., ['1024x1024', '512x512']"
    )
    noise_pattern = models.JSONField(
        help_text="Expected noise distribution characteristics"
    )
    color_signature = models.JSONField(
        help_text="RGB histogram patterns characteristic of this generator"
    )
    compression_artifacts = models.TextField(
        help_text="Description of characteristic compression artifacts"
    )

    # Detection thresholds
    ela_threshold_min = models.FloatField(help_text="Minimum ELA score for this generator")
    ela_threshold_max = models.FloatField(help_text="Maximum ELA score for this generator")
    metadata_patterns = models.JSONField(
        help_text="Expected metadata patterns (e.g., missing EXIF, software signatures)"
    )

    # Additional characteristics
    key_indicators = models.JSONField(
        help_text="List of key visual indicators for this generator",
        default=list
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.generator_type})"

    class Meta:
        verbose_name = "AI Generator Signature"
        verbose_name_plural = "AI Generator Signatures"
        ordering = ['name']


class ForensicAnalysisResult(models.Model):
    """
    Detailed forensic analysis results for each scan
    Stores all technical analysis metrics for transparency and debugging
    """
    scan = models.OneToOneField(
        MediaScan,
        on_delete=models.CASCADE,
        related_name='forensic_analysis'
    )

    # ELA (Error Level Analysis) Results
    ela_score = models.FloatField(
        null=True,
        blank=True,
        help_text="ELA manipulation score (0-100)"
    )
    ela_heatmap_data = models.JSONField(
        null=True,
        blank=True,
        help_text="ELA difference map for visualization"
    )

    # Metadata/EXIF Analysis
    has_exif = models.BooleanField(default=False)
    exif_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Extracted EXIF metadata"
    )
    metadata_consistency = models.CharField(
        max_length=20,
        choices=[
            ('consistent', 'Consistent'),
            ('inconsistent', 'Inconsistent'),
            ('missing', 'Missing'),
        ],
        default='missing'
    )
    software_detected = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Software signatures found (e.g., 'Photoshop', 'GIMP')"
    )

    # Noise Pattern Analysis
    noise_uniformity = models.FloatField(
        null=True,
        blank=True,
        help_text="Noise uniformity score (0-1, higher = more uniform)"
    )
    noise_pattern_anomalies = models.JSONField(
        null=True,
        blank=True,
        help_text="List of detected noise anomalies"
    )

    # Compression Analysis
    compression_artifacts_detected = models.BooleanField(default=False)
    double_compression = models.BooleanField(default=False)
    compression_quality_estimate = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text="Estimated compression quality (e.g., '95', '85')"
    )

    # Color Histogram Analysis
    color_histogram_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Color anomaly score (0-100)"
    )
    color_anomalies = models.JSONField(
        null=True,
        blank=True,
        help_text="Detected color distribution anomalies"
    )

    # Source Detection Results
    detected_sources = models.JSONField(
        null=True,
        blank=True,
        help_text="List of detected AI generators with confidence scores"
    )
    primary_source = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Most likely AI generator source"
    )
    source_confidence = models.FloatField(
        null=True,
        blank=True,
        help_text="Confidence in primary source detection (0-100)"
    )

    # Overall Assessment
    manipulation_indicators = models.JSONField(
        default=list,
        help_text="List of all detected manipulation indicators"
    )
    analysis_timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Forensic Analysis for Scan {self.scan_id}"

    def get_detected_sources_list(self):
        """Return detected sources as a list of dicts for easy access"""
        if self.detected_sources:
            if isinstance(self.detected_sources, str):
                return json.loads(self.detected_sources)
            return self.detected_sources
        return []

    class Meta:
        verbose_name = "Forensic Analysis Result"
        verbose_name_plural = "Forensic Analysis Results"
        ordering = ['-analysis_timestamp']
