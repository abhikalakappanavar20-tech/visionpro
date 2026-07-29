"""
AI Detection Services for VeriVision
Real Deepfake Detection Engine with Forensic + ML Analysis
"""
import hashlib
import os
import tempfile
import logging
from django.utils import timezone
from .models import ForensicDatabase

logger = logging.getLogger(__name__)


class DeepfakeAnalyzer:
    """
    Deepfake Detection Engine

    Uses real forensic analysis + pre-trained AI models:
    - Classical forensics: ELA, metadata, noise, compression, color, spectral
    - AI models: ResNet-18 (image), R3D-18 (video), Wav2Vec2 (audio)
    - Source detection: AI generator signature matching
    - Score fusion: Weighted combination of forensics + AI model
    """

    def __init__(self):
        try:
            from .analyzers import ForensicPipeline
            self.forensic_pipeline = ForensicPipeline()
            self.use_real_analysis = True
        except ImportError as e:
            logger.error(f"Could not import forensic pipeline: {e}")
            self.use_real_analysis = False
            self.forensic_pipeline = None

        self.analysis_stages = [
            "Extracting metadata...",
            "Running classical forensic analysis...",
            "Running AI deepfake detection model...",
            "Detecting AI generator source...",
            "Fusing forensic + AI scores...",
            "Generating explainable heatmap...",
            "Calculating trust metrics...",
            "Finalizing analysis..."
        ]

    def analyze_media(self, file, file_type, url=None):
        """
        Main analysis method that processes media and returns detection results.

        Args:
            file: UploadedFile object
            file_type: 'image', 'video', 'audio', or 'url'
            url: Optional URL for social media content

        Returns:
            dict with analysis results
        """
        start_time = timezone.now()

        if not self.use_real_analysis:
            return {
                'scan_result': 'error',
                'confidence_score': 0,
                'trust_score': 0,
                'forensic_match': False,
                'heatmap_data': {'hotspots': [], 'total_hotspots': 0, 'intensity_level': 'none'},
                'analysis_details': {
                    'error': 'Forensic pipeline not available. Please install required dependencies.'
                },
                'forensic_data': None,
                'processing_time': 0,
            }

        if file_type == 'image':
            return self._analyze_with_forensics(file, start_time)
        elif file_type == 'video':
            return self._analyze_video_with_forensics(file, start_time)
        elif file_type == 'audio':
            return self._analyze_audio_with_forensics(file, start_time)
        else:
            return {
                'scan_result': 'error',
                'confidence_score': 0,
                'trust_score': 0,
                'forensic_match': False,
                'heatmap_data': {'hotspots': [], 'total_hotspots': 0, 'intensity_level': 'none'},
                'analysis_details': {
                    'error': f'Unsupported file type: {file_type}'
                },
                'forensic_data': None,
                'processing_time': (timezone.now() - start_time).total_seconds(),
            }

    def _analyze_with_forensics(self, file, start_time):
        """Use real forensic pipeline + AI model for image analysis."""
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp_file:
                for chunk in file.chunks():
                    tmp_file.write(chunk)
                temp_path = tmp_file.name

            forensic_results = self.forensic_pipeline.analyze_image(temp_path)

            with open(temp_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()

            forensic_match = ForensicDatabase.objects.filter(
                content_hash=file_hash[:16]
            ).exists()

            forensic_results['forensic_match'] = forensic_match
            forensic_results['file_size'] = file.size
            forensic_results['file_hash'] = file_hash[:16]
            forensic_results['processing_time'] = (timezone.now() - start_time).total_seconds()

            return forensic_results

        except Exception as e:
            logger.error(f"Forensic image analysis failed: {e}")
            return {
                'scan_result': 'error',
                'confidence_score': 0,
                'trust_score': 0,
                'forensic_match': False,
                'heatmap_data': {'hotspots': [], 'total_hotspots': 0, 'intensity_level': 'none'},
                'analysis_details': {'error': f'Image analysis failed: {e}'},
                'forensic_data': None,
                'processing_time': (timezone.now() - start_time).total_seconds(),
            }
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def _analyze_video_with_forensics(self, file, start_time):
        """Use the forensic pipeline + AI model for video analysis."""
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp_file:
                for chunk in file.chunks():
                    tmp_file.write(chunk)
                temp_path = tmp_file.name

            forensic_results = self.forensic_pipeline.analyze_video(temp_path)

            with open(temp_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()

            forensic_results['forensic_match'] = ForensicDatabase.objects.filter(
                content_hash=file_hash[:16]
            ).exists()
            forensic_results['file_size'] = file.size
            forensic_results['file_hash'] = file_hash[:16]
            forensic_results['processing_time'] = (timezone.now() - start_time).total_seconds()

            return forensic_results

        except Exception as e:
            logger.error(f"Video forensic analysis failed: {e}")
            return {
                'scan_result': 'error',
                'confidence_score': 0,
                'trust_score': 0,
                'forensic_match': False,
                'heatmap_data': {'hotspots': [], 'total_hotspots': 0, 'intensity_level': 'none'},
                'analysis_details': {'error': f'Video analysis failed: {e}'},
                'forensic_data': None,
                'processing_time': (timezone.now() - start_time).total_seconds(),
            }
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def _analyze_audio_with_forensics(self, file, start_time):
        """Use the forensic pipeline + AI model for audio analysis."""
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp_file:
                for chunk in file.chunks():
                    tmp_file.write(chunk)
                temp_path = tmp_file.name

            forensic_results = self.forensic_pipeline.analyze_audio(temp_path)

            with open(temp_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()

            forensic_results['forensic_match'] = ForensicDatabase.objects.filter(
                content_hash=file_hash[:16]
            ).exists()
            forensic_results['file_size'] = file.size
            forensic_results['file_hash'] = file_hash[:16]
            forensic_results['processing_time'] = (timezone.now() - start_time).total_seconds()

            return forensic_results

        except Exception as e:
            logger.error(f"Audio forensic analysis failed: {e}")
            return {
                'scan_result': 'error',
                'confidence_score': 0,
                'trust_score': 0,
                'forensic_match': False,
                'heatmap_data': {'hotspots': [], 'total_hotspots': 0, 'intensity_level': 'none'},
                'analysis_details': {'error': f'Audio analysis failed: {e}'},
                'forensic_data': None,
                'processing_time': (timezone.now() - start_time).total_seconds(),
            }
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def analyze_url(self, url):
        """
        Analyze social media URL for authenticity.

        Actually fetches the URL content, extracts any media,
        and analyzes it through the forensic pipeline.
        """
        start_time = timezone.now()

        try:
            import requests
            from urllib.parse import urlparse

            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Domain trust scoring (based on platform verification rigor)
            domain_trust_scores = {
                'twitter.com': 75, 'x.com': 72,
                'facebook.com': 70, 'instagram.com': 68,
                'youtube.com': 80, 'tiktok.com': 65,
                'linkedin.com': 85, 'reddit.com': 78,
            }
            base_score = domain_trust_scores.get(domain, 50)

            # Fetch URL content
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            response.raise_for_status()

            content_type = response.headers.get('Content-Type', '')
            content_length = len(response.content)

            # Check if URL points directly to media
            media_result = None
            if any(ct in content_type for ct in ['image/', 'video/', 'audio/']):
                # Direct media URL - download and analyze
                media_result = self._analyze_media_url(url, response.content, content_type, start_time)
            else:
                # HTML page - try to extract media URLs
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')

                media_urls = []
                for tag in soup.find_all(['img', 'video', 'source']):
                    src = tag.get('src') or tag.get('data-src')
                    if src:
                        # Make absolute URL
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif src.startswith('/'):
                            src = f'{parsed.scheme}://{parsed.netloc}{src}'
                        media_urls.append(src)

                # Also check OpenGraph meta tags for media
                for meta in soup.find_all('meta'):
                    prop = meta.get('property', '') or meta.get('name', '')
                    if 'image' in prop or 'video' in prop:
                        content = meta.get('content', '')
                        if content and content.startswith('http'):
                            media_urls.append(content)

                if media_urls:
                    # Analyze first media found
                    media_result = self._analyze_media_url(
                        media_urls[0], None, None, start_time
                    )

            # Build analysis details
            analysis_details = {
                'domain': domain,
                'domain_trust_score': base_score,
                'url': url,
                'content_type': content_type,
                'content_length': content_length,
                'status_code': response.status_code,
                'ssl_valid': parsed.scheme == 'https',
                'media_found': media_result is not None,
                'analysis_notes': f'Fetched and analyzed content from {domain}',
            }

            if media_result:
                # Use the actual media analysis results
                result = {
                    'scan_result': media_result.get('scan_result', 'unknown'),
                    'confidence_score': media_result.get('confidence_score', 50),
                    'trust_score': media_result.get('trust_score', 50),
                    'forensic_match': media_result.get('forensic_match', False),
                    'heatmap_data': media_result.get('heatmap_data', {
                        'hotspots': [], 'total_hotspots': 0, 'intensity_level': 'none'
                    }),
                    'analysis_details': {
                        **analysis_details,
                        'media_analysis': media_result.get('forensic_details', {}),
                        'ai_detection': media_result.get('ai_detection', {}),
                    },
                    'forensic_data': None,
                    'processing_time': (timezone.now() - start_time).total_seconds(),
                }
            else:
                # No media found - analyze page metadata only
                result = {
                    'scan_result': 'unknown',
                    'confidence_score': 0,
                    'trust_score': base_score,
                    'forensic_match': False,
                    'heatmap_data': {'hotspots': [], 'total_hotspots': 0, 'intensity_level': 'none'},
                    'analysis_details': {
                        **analysis_details,
                        'analysis_notes': f'No downloadable media found at {domain}. Page metadata analyzed only.',
                    },
                    'forensic_data': None,
                    'processing_time': (timezone.now() - start_time).total_seconds(),
                }

            return result

        except requests.exceptions.Timeout:
            return self._url_error_result(url, 'URL request timed out', start_time)
        except requests.exceptions.ConnectionError:
            return self._url_error_result(url, 'Could not connect to URL', start_time)
        except requests.exceptions.HTTPError as e:
            return self._url_error_result(url, f'HTTP error: {e.response.status_code}', start_time)
        except ImportError:
            return self._url_error_result(
                url, 'requests/beautifulsoup4 not installed. Run: pip install requests beautifulsoup4',
                start_time
            )
        except Exception as e:
            logger.error(f"URL analysis failed: {e}")
            return self._url_error_result(url, str(e), start_time)

    def _analyze_media_url(self, url, content_bytes, content_type, start_time):
        """Download media from URL and analyze through forensic pipeline."""
        temp_path = None
        try:
            # Determine file extension from content type
            ext_map = {
                'image/jpeg': '.jpg', 'image/png': '.png', 'image/gif': '.gif',
                'image/webp': '.webp', 'video/mp4': '.mp4', 'video/webm': '.webm',
                'audio/mpeg': '.mp3', 'audio/wav': '.wav', 'audio/ogg': '.ogg',
            }
            ext = '.bin'
            for ct, e in ext_map.items():
                if ct in (content_type or ''):
                    ext = e
                    break

            # Download if not already fetched
            if content_bytes is None:
                import requests
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                content_bytes = response.content
                content_type = response.headers.get('Content-Type', '')

            # Determine file type
            file_type = 'unknown'
            if 'image' in (content_type or ''):
                file_type = 'image'
            elif 'video' in (content_type or ''):
                file_type = 'video'
            elif 'audio' in (content_type or ''):
                file_type = 'audio'

            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
                tmp_file.write(content_bytes)
                temp_path = tmp_file.name

            # Run through forensic pipeline
            if file_type == 'image':
                return self.forensic_pipeline.analyze_image(temp_path)
            elif file_type == 'video':
                return self.forensic_pipeline.analyze_video(temp_path)
            elif file_type == 'audio':
                return self.forensic_pipeline.analyze_audio(temp_path)
            else:
                return None

        except Exception as e:
            logger.error(f"Failed to analyze media URL {url}: {e}")
            return None
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def _url_error_result(self, url, error_msg, start_time):
        """Return error result for failed URL analysis."""
        return {
            'scan_result': 'error',
            'confidence_score': 0,
            'trust_score': 0,
            'forensic_match': False,
            'heatmap_data': {'hotspots': [], 'total_hotspots': 0, 'intensity_level': 'none'},
            'analysis_details': {
                'url': url,
                'error': error_msg,
                'analysis_notes': f'URL analysis failed: {error_msg}',
            },
            'forensic_data': None,
            'processing_time': (timezone.now() - start_time).total_seconds(),
        }

    def _generate_heatmap(self, scan_result):
        if scan_result == 'fake':
            return {
                'hotspots': [
                    {'x': 25, 'y': 30, 'radius': 15, 'intensity': 0.85},
                    {'x': 60, 'y': 40, 'radius': 12, 'intensity': 0.75},
                    {'x': 45, 'y': 65, 'radius': 18, 'intensity': 0.80},
                    {'x': 70, 'y': 55, 'radius': 10, 'intensity': 0.70},
                ],
                'total_hotspots': 4,
                'intensity_level': 'high'
            }
        elif scan_result == 'suspicious':
            return {
                'hotspots': [
                    {'x': 30, 'y': 40, 'radius': 12, 'intensity': 0.55},
                ],
                'total_hotspots': 1,
                'intensity_level': 'medium'
            }
        else:
            return {
                'hotspots': [
                    {'x': 50, 'y': 50, 'radius': 8, 'intensity': 0.15},
                ],
                'total_hotspots': 1,
                'intensity_level': 'low'
            }

    def _generate_forensic_data(self, file_hash):
        import random
        contexts = [
            "Previously identified in misinformation campaign",
            "Known deepfake template used in social engineering",
            "Flagged by multiple fact-checking organizations",
            "Associated with known disinformation network",
            "Reported as manipulated media by community"
        ]
        campaigns = ["Disinfo2024", "DeepFakeWave", None, None, None]
        return {
            'first_seen': (timezone.now() - timezone.timedelta(days=random.randint(1, 90))).strftime('%Y-%m-%d'),
            'usage_count': random.randint(1, 50),
            'context': random.choice(contexts),
            'known_campaign': random.choice(campaigns),
            'threat_level': random.choice(['low', 'medium', 'high']),
            'verified': random.choice([True, False])
        }

    def get_analysis_stages(self):
        return self.analysis_stages


class ThreatLevelCalculator:
    """Calculate overall threat level based on multiple factors."""

    @staticmethod
    def calculate(scan_result, confidence_score, trust_score, forensic_match):
        threat = 0

        if scan_result == 'fake':
            threat += 50
        elif scan_result == 'manipulated':
            threat += 40
        elif scan_result == 'suspicious':
            threat += 25

        if confidence_score > 90 and scan_result != 'real':
            threat += 20
        elif confidence_score > 80:
            threat += 10

        threat += (100 - trust_score) * 0.3

        if forensic_match:
            threat += 15

        return min(100, max(0, int(threat)))
