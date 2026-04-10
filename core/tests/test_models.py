"""
Tests for core models
"""
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from core.models import MediaScan, ReportedContent, ForensicDatabase
from datetime import datetime, timedelta
import json


class MediaScanModelTest(TestCase):
    """Test MediaScan model"""

    def setUp(self):
        """Set up test data"""
        self.scan = MediaScan.objects.create(
            file_type='image',
            scan_result='fake',
            confidence_score=95.5,
            trust_score=30,
            forensic_match=True,
            heatmap_data={'hotspots': [{'x': 50, 'y': 50, 'radius': 10}]},
            analysis_details={'test': 'data'},
            processing_time=2.5
        )

    def test_media_scan_creation(self):
        """Test MediaScan can be created"""
        self.assertTrue(isinstance(self.scan, MediaScan))
        self.assertEqual(self.scan.scan_result, 'fake')
        self.assertEqual(self.scan.confidence_score, 95.5)

    def test_media_scan_str_method(self):
        """Test MediaScan string representation"""
        expected = f"MediaScan {self.scan.id} - fake (95.5%)"
        self.assertEqual(str(self.scan), expected)

    def test_forensic_match_defaults(self):
        """Test forensic match defaults to False"""
        scan_no_forensic = MediaScan.objects.create(
            file_type='video',
            scan_result='real',
            confidence_score=85.0,
            trust_score=80,
            processing_time=3.0
        )
        self.assertFalse(scan_no_forensic.forensic_match)

    def test_heatmap_data_default(self):
        """Test heatmap_data defaults to empty dict"""
        scan = MediaScan.objects.create(
            file_type='audio',
            scan_result='suspicious',
            confidence_score=70.0,
            trust_score=50,
            processing_time=1.5
        )
        self.assertEqual(scan.heatmap_data, {})


class ReportedContentModelTest(TestCase):
    """Test ReportedContent model"""

    def setUp(self):
        """Set up test data"""
        self.scan = MediaScan.objects.create(
            file_type='image',
            scan_result='fake',
            confidence_score=90.0,
            trust_score=25,
            processing_time=2.0
        )

        self.report = ReportedContent.objects.create(
            scan=self.scan,
            url_or_file_name='test_image.jpg',
            file_type='image',
            reason='This looks like a deepfake'
        )

    def test_report_creation(self):
        """Test report can be created"""
        self.assertTrue(isinstance(self.report, ReportedContent))
        self.assertEqual(self.report.status, 'pending')
        self.assertEqual(self.report.url_or_file_name, 'test_image.jpg')

    def test_report_default_status(self):
        """Test default status is pending"""
        report = ReportedContent.objects.create(
            url_or_file_name='another.jpg',
            file_type='image',
            reason='Another report'
        )
        self.assertEqual(report.status, 'pending')

    def test_report_scan_relationship(self):
        """Test foreign key relationship"""
        self.assertEqual(self.report.scan, self.scan)
        self.assertEqual(self.report.scan.scan_result, 'fake')


class ForensicDatabaseModelTest(TestCase):
    """Test ForensicDatabase model"""

    def test_forensic_entry_creation(self):
        """Test forensic entry can be created"""
        entry = ForensicDatabase.objects.create(
            content_hash='abc123def456',
            content_type='image',
            first_seen=datetime.now().date(),
            usage_count=10,
            context='Test context'
        )
        self.assertTrue(isinstance(entry, ForensicDatabase))
        self.assertEqual(entry.content_hash, 'abc123def456')
        self.assertEqual(entry.usage_count, 10)

    def test_default_threat_level(self):
        """Test default threat level is medium"""
        entry = ForensicDatabase.objects.create(
            content_hash='xyz789',
            content_type='video',
            first_seen=datetime.now().date(),
            context='Test'
        )
        self.assertEqual(entry.threat_level, 'medium')

    def test_default_usage_count(self):
        """Test default usage count is 1"""
        entry = ForensicDatabase.objects.create(
            content_hash='test123',
            content_type='audio',
            first_seen=datetime.now().date(),
            context='Test'
        )
        self.assertEqual(entry.usage_count, 1)


class ModelQueryTests(TestCase):
    """Test model queries and relationships"""

    @classmethod
    def setUpTestData(cls):
        """Set up data for all tests"""
        # Create multiple scans
        cls.fake_scan = MediaScan.objects.create(
            file_type='image',
            scan_result='fake',
            confidence_score=95.0,
            trust_score=20,
            processing_time=2.0
        )

        cls.real_scan = MediaScan.objects.create(
            file_type='image',
            scan_result='real',
            confidence_score=85.0,
            trust_score=85,
            processing_time=1.5
        )

        cls.manipulated_scan = MediaScan.objects.create(
            file_type='video',
            scan_result='manipulated',
            confidence_score=75.0,
            trust_score=40,
            processing_time=4.0
        )

    def test_filter_by_scan_result(self):
        """Test filtering by scan result"""
        fake_scans = MediaScan.objects.filter(scan_result='fake')
        self.assertEqual(fake_scans.count(), 1)
        self.assertEqual(fake_scans.first().confidence_score, 95.0)

    def test_filter_by_file_type(self):
        """Test filtering by file type"""
        image_scans = MediaScan.objects.filter(file_type='image')
        self.assertEqual(image_scans.count(), 2)

    def test_average_confidence(self):
        """Test calculating average confidence"""
        from django.db.models import Avg
        avg_confidence = MediaScan.objects.aggregate(
            avg=Avg('confidence_score')
        )['avg']
        expected = (95.0 + 85.0 + 75.0) / 3
        self.assertAlmostEqual(avg_confidence, expected, places=2)

    def test_ordering(self):
        """Test default ordering by created_at desc"""
        all_scans = MediaScan.objects.all()
        # Most recent should be first
        self.assertTrue(
            all_scans[0].created_at >= all_scans[1].created_at
        )
