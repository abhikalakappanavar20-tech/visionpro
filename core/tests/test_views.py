"""
Tests for core views
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import MediaScan
import json


class HomeViewTest(TestCase):
    """Test home page view"""

    def setUp(self):
        """Set up test client"""
        self.client = Client()

    def test_home_page_status(self):
        """Test home page loads successfully"""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'VeriVision')

    def test_home_template_used(self):
        """Test correct template is used"""
        response = self.client.get(reverse('home'))
        self.assertTemplateUsed(response, 'core/home.html')


class ScanViewTest(TestCase):
    """Test scan page view"""

    def setUp(self):
        """Set up test client"""
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')

    def test_scan_page_status(self):
        """Test scan page loads successfully"""
        response = self.client.get(reverse('scan'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Media Analysis Scanner')

    def test_scan_form_in_context(self):
        """Test scan form is in context"""
        response = self.client.get(reverse('scan'))
        self.assertTrue('form' in response.context)


class DashboardViewTest(TestCase):
    """Test dashboard view"""

    def setUp(self):
        """Set up test client and data"""
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
        # Create some test scans
        MediaScan.objects.create(
            user=self.user,
            file_type='image',
            scan_result='fake',
            confidence_score=90.0,
            trust_score=30,
            processing_time=2.0
        )
        MediaScan.objects.create(
            user=self.user,
            file_type='video',
            scan_result='real',
            confidence_score=85.0,
            trust_score=80,
            processing_time=3.0
        )

    def test_dashboard_page_status(self):
        """Test dashboard page loads successfully"""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Analytics Dashboard')

    def test_dashboard_context_data(self):
        """Test dashboard contains required context data"""
        response = self.client.get(reverse('dashboard'))
        self.assertTrue('total_scans' in response.context)
        self.assertEqual(response.context['total_scans'], 2)


class HistoryViewTest(TestCase):
    """Test history view"""

    def setUp(self):
        """Set up test client and data"""
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
        self.scan = MediaScan.objects.create(
            user=self.user,
            file_type='image',
            scan_result='fake',
            confidence_score=90.0,
            trust_score=30,
            processing_time=2.0
        )

    def test_history_page_status(self):
        """Test history page loads successfully"""
        response = self.client.get(reverse('history'))
        self.assertEqual(response.status_code, 200)

    def test_history_contains_scan(self):
        """Test history page shows scans"""
        response = self.client.get(reverse('history'))
        self.assertContains(response, 'fake')
        self.assertContains(response, '90.0')

    def test_history_filter_by_result(self):
        """Test filtering history by result"""
        response = self.client.get(reverse('history') + '?result=fake')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'fake')


class ResultViewTest(TestCase):
    """Test result view"""

    def setUp(self):
        """Set up test client and data"""
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
        self.scan = MediaScan.objects.create(
            user=self.user,
            file_type='image',
            scan_result='fake',
            confidence_score=95.0,
            trust_score=25,
            forensic_match=True,
            heatmap_data={'hotspots': [{'x': 50, 'y': 50}]},
            processing_time=2.5
        )

    def test_result_page_status(self):
        """Test result page loads successfully"""
        response = self.client.get(reverse('result', args=[self.scan.id]))
        self.assertEqual(response.status_code, 200)

    def test_result_context_data(self):
        """Test result page contains scan data"""
        response = self.client.get(reverse('result', args=[self.scan.id]))
        self.assertTrue('scan' in response.context)
        self.assertEqual(response.context['scan'], self.scan)
        self.assertTrue('heatmap_data' in response.context)
        self.assertTrue('threat_level' in response.context)

    def test_result_404_for_invalid_id(self):
        """Test result page returns 404 for invalid scan ID"""
        response = self.client.get(reverse('result', args=[99999]))
        self.assertEqual(response.status_code, 404)


class APIStatsTest(TestCase):
    """Test API stats endpoint"""

    def setUp(self):
        """Set up test client and data"""
        self.client = Client()
        MediaScan.objects.create(
            file_type='image',
            scan_result='fake',
            confidence_score=90.0,
            trust_score=30,
            processing_time=2.0
        )

    def test_api_stats_endpoint(self):
        """Test API stats endpoint returns JSON"""
        response = self.client.get(reverse('api_stats'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_api_stats_data(self):
        """Test API stats returns correct data"""
        response = self.client.get(reverse('api_stats'))
        data = json.loads(response.content)
        self.assertTrue('total_scans' in data)
        self.assertEqual(data['total_scans'], 1)
        self.assertTrue('fake_count' in data)
