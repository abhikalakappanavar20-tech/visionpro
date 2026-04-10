"""
Tests for core services (AI detection engine)
"""
from django.test import TestCase
from core.services import DeepfakeAnalyzer, ThreatLevelCalculator
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from PIL import Image
import json


class DeepfakeAnalyzerTest(TestCase):
    """Test DeepfakeAnalyzer service"""

    def setUp(self):
        """Set up analyzer"""
        self.analyzer = DeepfakeAnalyzer()

    def test_analyzer_initialization(self):
        """Test analyzer can be initialized"""
        self.assertTrue(isinstance(self.analyzer, DeepfakeAnalyzer))
        self.assertTrue(len(self.analyzer.analysis_stages) > 0)

    def test_analyze_media_with_image(self):
        """Test analyzing an image file"""
        # Create a simple test image
        img = Image.new('RGB', (100, 100), color='red')
        img_io = BytesIO()
        img.save(img_io, 'JPEG')
        img_io.seek(0)

        test_file = SimpleUploadedFile(
            "test.jpg",
            img_io.read(),
            content_type="image/jpeg"
        )

        result = self.analyzer.analyze_media(test_file, 'image')

        # Check result structure
        self.assertTrue('scan_result' in result)
        self.assertTrue('confidence_score' in result)
        self.assertTrue('trust_score' in result)
        self.assertTrue('heatmap_data' in result)
        self.assertTrue('forensic_match' in result)
        self.assertTrue('processing_time' in result)

        # Check data types
        self.assertIn(result['scan_result'], ['real', 'fake', 'manipulated', 'suspicious'])
        self.assertGreaterEqual(result['confidence_score'], 0)
        self.assertLessEqual(result['confidence_score'], 100)
        self.assertGreaterEqual(result['trust_score'], 0)
        self.assertLessEqual(result['trust_score'], 100)

    def test_analyze_url(self):
        """Test analyzing a URL"""
        test_url = "https://twitter.com/user/status/1234567890"
        result = self.analyzer.analyze_url(test_url)

        # Check result structure
        self.assertTrue('scan_result' in result)
        self.assertTrue('confidence_score' in result)
        self.assertTrue('trust_score' in result)
        self.assertTrue('analysis_details' in result)

        # Check analysis details contains domain info
        self.assertTrue('domain' in result['analysis_details'])
        self.assertEqual(result['analysis_details']['domain'], 'twitter.com')

    def test_heatmap_generation_for_fake(self):
        """Test heatmap generation for fake content"""
        heatmap = self.analyzer._generate_heatmap('fake')

        self.assertTrue('hotspots' in heatmap)
        self.assertTrue('intensity_level' in heatmap)
        self.assertTrue('total_hotspots' in heatmap)
        self.assertEqual(heatmap['intensity_level'], 'high')

        # Should have multiple hotspots for fake content
        self.assertGreaterEqual(heatmap['total_hotspots'], 4)

    def test_heatmap_generation_for_real(self):
        """Test heatmap generation for real content"""
        heatmap = self.analyzer._generate_heatmap('real')

        self.assertTrue('hotspots' in heatmap)
        self.assertEqual(heatmap['intensity_level'], 'low')

        # Should have fewer hotspots for real content
        self.assertLessEqual(heatmap['total_hotspots'], 2)

    def test_forensic_data_generation(self):
        """Test forensic data generation"""
        forensic_data = self.analyzer._generate_forensic_data('test_hash')

        self.assertTrue('first_seen' in forensic_data)
        self.assertTrue('usage_count' in forensic_data)
        self.assertTrue('context' in forensic_data)
        self.assertTrue('known_campaign' in forensic_data)
        self.assertTrue('threat_level' in forensic_data)
        self.assertTrue('verified' in forensic_data)


class ThreatLevelCalculatorTest(TestCase):
    """Test ThreatLevelCalculator service"""

    def test_calculate_threat_for_fake(self):
        """Test threat calculation for fake content"""
        threat = ThreatLevelCalculator.calculate(
            scan_result='fake',
            confidence_score=95,
            trust_score=20,
            forensic_match=True
        )

        self.assertGreaterEqual(threat, 0)
        self.assertLessEqual(threat, 100)
        # Fake content with high confidence should have high threat
        self.assertGreater(threat, 60)

    def test_calculate_threat_for_real(self):
        """Test threat calculation for real content"""
        threat = ThreatLevelCalculator.calculate(
            scan_result='real',
            confidence_score=90,
            trust_score=85,
            forensic_match=False
        )

        self.assertGreaterEqual(threat, 0)
        self.assertLessEqual(threat, 100)
        # Real content should have low threat
        self.assertLess(threat, 40)

    def test_calculate_threat_bounds(self):
        """Test threat calculation stays within bounds"""
        # Test maximum threat
        threat_max = ThreatLevelCalculator.calculate(
            scan_result='fake',
            confidence_score=100,
            trust_score=0,
            forensic_match=True
        )
        self.assertLessEqual(threat_max, 100)

        # Test minimum threat
        threat_min = ThreatLevelCalculator.calculate(
            scan_result='real',
            confidence_score=80,
            trust_score=100,
            forensic_match=False
        )
        self.assertGreaterEqual(threat_min, 0)


class ServiceIntegrationTest(TestCase):
    """Integration tests for services"""

    def setUp(self):
        """Set up analyzer"""
        self.analyzer = DeepfakeAnalyzer()

    def test_full_scan_workflow(self):
        """Test complete scan workflow"""
        # Create test image
        img = Image.new('RGB', (200, 200), color='blue')
        img_io = BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)

        test_file = SimpleUploadedFile(
            "test.png",
            img_io.read(),
            content_type="image/png"
        )

        # Run analysis
        result = self.analyzer.analyze_media(test_file, 'image')

        # Verify all components
        self.assertIsNotNone(result['scan_result'])
        self.assertIsNotNone(result['confidence_score'])
        self.assertIsNotNone(result['trust_score'])
        self.assertIsNotNone(result['heatmap_data'])
        self.assertGreater(result['processing_time'], 0)

        # Calculate threat level
        threat = ThreatLevelCalculator.calculate(
            result['scan_result'],
            result['confidence_score'],
            result['trust_score'],
            result['forensic_match']
        )

        self.assertGreaterEqual(threat, 0)
        self.assertLessEqual(threat, 100)
