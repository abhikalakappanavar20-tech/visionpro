"""
Forensic Pipeline - Orchestrates all analyzers

Coordinates the forensic analysis workflow:
1. Image Forensics Analyzer (ELA, metadata, noise, compression, color)
2. Source Detector (AI generator identification)
3. Scoring and result aggregation
4. Database storage
"""

import os
import logging
from typing import Dict, Any
from datetime import datetime
import numpy as np

from .image_forensics import ImageForensicsAnalyzer
from .source_detector import SourceDetector

logger = logging.getLogger(__name__)


def _convert_to_native(obj):
    """Convert NumPy types and PIL Images to native Python types for JSON serialization."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, dict):
        return {k: _convert_to_native(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_convert_to_native(item) for item in obj]
    elif hasattr(obj, '__class__') and 'Image' in obj.__class__.__name__:
        # Handle PIL Image objects by returning None or a placeholder
        return None
    return obj


class ForensicPipeline:
    """
    Main forensic analysis pipeline.

    Orchestrates all analyzers and produces comprehensive results.
    """

    def __init__(self):
        self.image_analyzer = ImageForensicsAnalyzer()
        self.video_analyzer = None  # Lazy loaded
        self.audio_analyzer = None  # Lazy loaded
        self.source_detector = SourceDetector()
        self.ml_adapter = None  # Lazy loaded

    def analyze_image(self, image_path: str, source: str = 'upload') -> Dict[str, Any]:
        """
        Run complete forensic analysis on an image.

        Args:
            image_path: Path to image file
            source: Source of image ('upload', 'webcam', 'url')

        Returns:
            dict with complete analysis results:
                - scan_result: 'real', 'fake', 'manipulated', or 'suspicious'
                - confidence_score: Overall confidence (0-100)
                - trust_score: Inverse of confidence (0-100)
                - forensic_details: Detailed analysis from each technique
                - source_detection: Detected AI generators
                - heatmap_data: ELA visualization data
                - processing_time: Analysis duration
        """
        start_time = datetime.now()

        try:
            logger.info(f"Starting forensic analysis: {image_path} (source: {source})")

            # Validate image exists
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image not found: {image_path}")

            # Step 1: Run Image Forensics Analysis with source detection
            logger.info("Running image forensics analysis...")
            forensic_results = self.image_analyzer.analyze(image_path, source=source)

            # Step 2: Detect AI Generator Source
            # IMPORTANT: Skip AI detection for webcam captures (they can't be AI-generated)
            detected_sources = []
            if source != 'webcam':
                logger.info("Detecting AI generator source...")
                detected_sources = self.source_detector.detect_source(
                    image_path,
                    forensic_results['details']
                )
            else:
                logger.info("Skipping AI detection for webcam capture (can't be AI-generated)")

            # Step 3: Calculate final scores
            logger.info("Calculating final scores...")
            confidence_score = forensic_results['score']
            trust_score = 100 - confidence_score

            # Adjust confidence based on source detection (only for non-webcam)
            if detected_sources and source != 'webcam':
                # Boost confidence if AI source detected
                primary_source_confidence = detected_sources[0]['confidence']
                if primary_source_confidence > 60:
                    confidence_score = min(100, confidence_score * 1.1)
                    trust_score = 100 - confidence_score

            # Step 4: Determine scan result
            scan_result = self._determine_scan_result(
                confidence_score,
                forensic_results,
                detected_sources,
                source=source  # Pass source to classification
            )

            # Step 5: Prepare analysis details for database
            analysis_details = self._prepare_analysis_details(
                forensic_results,
                detected_sources
            )

            # Step 6: Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()

            logger.info(f"Analysis complete: {scan_result} ({confidence_score}% confidence)")

            result = {
                'scan_result': scan_result,
                'confidence_score': round(confidence_score, 2),
                'trust_score': round(trust_score, 2),
                'forensic_details': analysis_details,
                'source_detection': detected_sources,
                'heatmap_data': forensic_results['ela_heatmap'],
                'processing_time': round(processing_time, 3),
                'manipulation_indicators': forensic_results['indicators']
            }

            return _convert_to_native(result)

        except Exception as e:
            logger.error(f"Forensic pipeline failed: {str(e)}")
            raise

    def analyze_video(self, video_path: str, source: str = 'upload') -> Dict[str, Any]:
        """
        Run complete forensic analysis on a video file.

        Args:
            video_path: Path to video file
            source: Source of video ('upload', 'webcam', 'url')

        Returns:
            dict with complete analysis results
        """
        start_time = datetime.now()

        try:
            logger.info(f"Starting video forensic analysis: {video_path} (source: {source})")

            # Lazy load video analyzer
            if self.video_analyzer is None:
                from .video_forensics import VideoForensicsAnalyzer
                self.video_analyzer = VideoForensicsAnalyzer()

            # Validate video exists
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video not found: {video_path}")

            # Run video forensics analysis
            logger.info("Running video forensics analysis...")
            video_results = self.video_analyzer.analyze(video_path, source=source)

            # Step 2: Detect AI Video Generator Source
            # IMPORTANT: Skip AI detection for webcam captures (they can't be AI-generated)
            detected_sources = []
            if source != 'webcam':
                logger.info("Detecting AI video generator source...")
                detected_sources = self.source_detector.detect_video_source(
                    video_path,
                    video_results['details']
                )
            else:
                logger.info("Skipping AI detection for webcam capture (can't be AI-generated)")

            # Calculate scores
            confidence_score = video_results['score']
            trust_score = 100 - confidence_score

            # Adjust confidence if AI video source detected (only for non-webcam)
            if detected_sources and source != 'webcam':
                # Boost confidence if AI source detected
                primary_source_confidence = detected_sources[0]['confidence']
                if primary_source_confidence > 50:
                    confidence_score = min(100, confidence_score * 1.15)
                    trust_score = 100 - confidence_score

            # Determine scan result
            scan_result = self._determine_scan_result(
                confidence_score,
                video_results,
                detected_sources,
                source=source
            )

            # Prepare analysis details
            details = video_results.get('details', {})

            analysis_details = {
                'video_analysis': {
                    'frame_count': details.get('frame_count', 0),
                    'analyzed_frames': details.get('analyzed_frames', 0),
                    'temporal_consistency': details.get('temporal_consistency', {
                        'consistency_score': 100.0,
                        'avg_brightness_change': 0.0,
                        'max_brightness_change': 0.0
                    }),
                    'face_tracking': details.get('face_tracking', {
                        'faces_detected': 0,
                        'face_positions': [],
                        'movement_anomalies': 0,
                        'detection_rate': 0.0
                    }),
                    'motion_analysis': details.get('motion_analysis', {
                        'motion_detected': False,
                        'avg_motion': 0.0,
                        'max_motion': 0.0,
                        'frozen_frames': 0
                    })
                }
            }

            # Generate heatmap data (from most manipulated frame)
            heatmap_data = self._generate_video_heatmap(video_results)

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()

            logger.info(f"Video analysis complete: {scan_result} ({confidence_score}% confidence)")

            result = {
                'scan_result': scan_result,
                'confidence_score': round(confidence_score, 2),
                'trust_score': round(trust_score, 2),
                'forensic_details': analysis_details,
                'source_detection': detected_sources,
                'heatmap_data': heatmap_data,
                'processing_time': round(processing_time, 3),
                'manipulation_indicators': video_results['indicators']
            }

            return _convert_to_native(result)

        except Exception as e:
            logger.error(f"Video forensic pipeline failed: {str(e)}")
            raise

    def analyze_audio(self, audio_path: str, source: str = 'upload') -> Dict[str, Any]:
        """
        Run complete forensic analysis on an audio file.

        Args:
            audio_path: Path to audio file
            source: Source of audio ('upload', 'webcam', 'url')

        Returns:
            dict with complete analysis results
        """
        start_time = datetime.now()

        try:
            logger.info(f"Starting audio forensic analysis: {audio_path} (source: {source})")

            # Lazy load audio analyzer
            if self.audio_analyzer is None:
                from .audio_forensics import AudioForensicsAnalyzer
                self.audio_analyzer = AudioForensicsAnalyzer()

            # Validate audio exists
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio not found: {audio_path}")

            # Run audio forensics analysis
            logger.info("Running audio forensics analysis...")
            audio_results = self.audio_analyzer.analyze(audio_path)

            # Step 2: Detect AI Audio Generator Source
            # IMPORTANT: Skip AI detection for webcam captures (they can't be AI-generated)
            detected_sources = []
            if source != 'webcam':
                logger.info("Detecting AI audio generator source...")
                detected_sources = self.source_detector.detect_audio_source(
                    audio_path,
                    audio_results
                )
            else:
                logger.info("Skipping AI detection for webcam capture (can't be AI-generated)")

            # Calculate scores
            confidence_score = audio_results['score']
            trust_score = 100 - confidence_score

            # Adjust confidence if AI audio source detected (only for non-webcam)
            if detected_sources and source != 'webcam':
                # Boost confidence if AI source detected
                primary_source_confidence = detected_sources[0]['confidence']
                if primary_source_confidence > 50:
                    confidence_score = min(100, confidence_score * 1.15)
                    trust_score = 100 - confidence_score

            # Determine scan result
            scan_result = self._determine_scan_result(
                confidence_score,
                audio_results,
                detected_sources,
                source=source
            )

            # Prepare analysis details
            details = audio_results.get('details', {})

            analysis_details = {
                'audio_analysis': {
                    'duration': details.get('duration', 0.0),
                    'spectral_features': details.get('spectral_features', {
                        'mfcc_mean': [0.0] * 5,
                        'mfcc_std_mean': 0.0,
                        'spectral_contrast_mean': 0.0,
                        'spectral_centroid_mean': 0.0,
                        'zero_crossing_rate': 0.0
                    }),
                    'voice_characteristics': details.get('voice_characteristics', {
                        'pitch_mean': 0.0,
                        'pitch_std': 0.0,
                        'pitch_range': 0.0,
                        'rms_mean': 0.0,
                        'rms_std': 0.0
                    }),
                    'background_noise': details.get('background_noise', {
                        'spectral_flatness': 0.0,
                        'noise_floor_db': -60.0
                    }),
                    'silence_analysis': details.get('silence_analysis', {
                        'silence_ratio': 0.0,
                        'num_silence_segments': 0,
                        'avg_silence_length': 0.0
                    })
                }
            }

            # No heatmap for audio
            heatmap_data = {'hotspots': [], 'total_hotspots': 0, 'intensity_level': 'none'}

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()

            logger.info(f"Audio analysis complete: {scan_result} ({confidence_score}% confidence)")

            result = {
                'scan_result': scan_result,
                'confidence_score': round(confidence_score, 2),
                'trust_score': round(trust_score, 2),
                'forensic_details': analysis_details,
                'source_detection': detected_sources,
                'heatmap_data': heatmap_data,
                'processing_time': round(processing_time, 3),
                'manipulation_indicators': audio_results['indicators']
            }

            return _convert_to_native(result)

        except Exception as e:
            logger.error(f"Audio forensic pipeline failed: {str(e)}")
            raise

    def _generate_video_heatmap(self, video_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate heatmap data for video analysis.

        Uses frame analysis to create heatmap.

        Args:
            video_results: Results from video analyzer

        Returns:
            Heatmap data dictionary
        """
        # Get frame scores
        frame_scores = video_results['details']['frame_analysis']['frame_scores']

        # Find most manipulated frames
        if not frame_scores:
            return {'hotspots': [], 'total_hotspots': 0, 'intensity_level': 'none'}

        # Create hotspots for highly manipulated frames
        hotspots = []
        for i, score in enumerate(frame_scores):
            if score > 50:  # Only show manipulated frames
                # Distribute hotspots across the image
                x = (i % 5) * 20 + 10
                y = (i // 5) * 20 + 10

                intensity = min(1.0, score / 100)
                hotspots.append({
                    'x': x,
                    'y': y,
                    'radius': 8,
                    'intensity': intensity,
                    'frame': i
                })

        # Determine intensity level
        if not hotspots:
            intensity_level = 'none'
        elif max(s['intensity'] for s in hotspots) >= 0.7:
            intensity_level = 'high'
        elif max(s['intensity'] for s in hotspots) >= 0.4:
            intensity_level = 'medium'
        else:
            intensity_level = 'low'

        return {
            'hotspots': hotspots[:10],  # Limit to 10 hotspots
            'total_hotspots': len(hotspots),
            'intensity_level': intensity_level
        }

    def _determine_scan_result(
        self,
        confidence_score: float,
        forensic_results: dict,
        detected_sources: list,
        source: str = 'upload'
    ) -> str:
        """
        Determine the final scan result classification.

        Binary classification system:
        - REAL: No filters, no editing, no AI (completely authentic)
        - FAKE: Any editing, filters, or AI manipulation

        Rules:
        - confidence < 30: 'real' (no significant manipulation)
        - confidence 30-50: 'suspicious' (some manipulation signals)
        - confidence > 50: 'fake' (clear manipulation or AI)

        CRITICAL: AI source detection is only trusted if forensic score is HIGH (>= 40)
        - For low forensic scores (< 25), trust the forensics, not the source detector
        - This prevents false positives where source detector sees patterns in real videos
        """
        # CRITICAL FIX: Only trust AI source detection if forensic score is already moderately high
        # If forensic score is low (< 25), the video is likely real, don't override with AI detection
        # AI source detector has false positives on real videos, so we need forensic corroboration
        if source != 'webcam' and detected_sources and confidence_score >= 40:
            # ONLY boost confidence if both:
            # 1. AI source detected with high confidence (> 35%)
            # 2. Forensic score is already moderately high (>= 40)
            # This prevents false positives on real videos with similar characteristics
            if detected_sources[0]['confidence'] > 35:
                # Boost confidence score to ensure AI content is classified as FAKE
                # AI-generated content should have confidence >= 55
                if confidence_score < 55:
                    confidence_score = 55
                return 'fake'

        # Balanced classification thresholds
        # Real photos: low scores, minimal indicators
        # Suspicious: moderate scores, some indicators
        # Fake: high scores, multiple strong indicators
        if confidence_score < 30:
            return 'real'
        elif confidence_score <= 50:
            return 'suspicious'
        else:
            return 'fake'

    def _prepare_analysis_details(
        self,
        forensic_results: dict,
        detected_sources: list
    ) -> Dict[str, Any]:
        """
        Prepare analysis details for database storage.

        Creates a structured summary of all findings.
        """
        details = forensic_results.get('details', {})

        # Initialize analysis details
        analysis_details = {}

        # Add ELA analysis (if available)
        if 'ela' in details:
            try:
                analysis_details['ela_analysis'] = {
                    'score': float(details['ela']['score']),
                    'mean_difference': float(details['ela']['mean_difference']),
                    'findings': list(details['ela']['findings'])
                }
            except (KeyError, TypeError):
                pass

        # Add metadata analysis (if available)
        if 'metadata' in details:
            try:
                analysis_details['metadata_analysis'] = {
                    'has_exif': bool(details['metadata']['has_exif']),
                    'consistency': str(details['metadata']['consistency']),
                    'software_detected': details['metadata'].get('software_detected', ''),
                    'findings': list(details['metadata']['findings'])
                }
            except (KeyError, TypeError):
                pass

        # Add noise analysis (if available)
        if 'noise' in details:
            try:
                analysis_details['noise_analysis'] = {
                    'score': float(details['noise']['score']),
                    'uniformity': float(details['noise']['noise_uniformity']),
                    'findings': list(details['noise']['findings'])
                }
            except (KeyError, TypeError):
                pass

        # Add compression analysis (if available)
        if 'compression' in details:
            try:
                analysis_details['compression_analysis'] = {
                    'score': float(details['compression']['score']),
                    'double_compression': bool(details['compression']['double_compression']),
                    'findings': list(details['compression']['findings'])
                }
            except (KeyError, TypeError):
                pass

        # Add color analysis (if available)
        if 'color' in details:
            try:
                analysis_details['color_analysis'] = {
                    'score': float(details['color']['score']),
                    'avg_saturation': float(details['color']['avg_saturation']),
                    'findings': list(details['color']['findings'])
                }
            except (KeyError, TypeError):
                pass

        # Add preprocessing metadata (collage detection, etc.)
        if 'preprocessing' in details:
            try:
                analysis_details['preprocessing'] = {
                    'is_collage': bool(details['preprocessing']['is_collage']),
                    'enhancement_applied': details['preprocessing'].get('enhancement_applied', False),
                    'quality_validation': details['preprocessing'].get('quality_validation', {}),
                }
            except (KeyError, TypeError):
                pass

        return analysis_details

    def save_forensic_results(
        self,
        scan,
        analysis_results: dict
    ):
        """
        Save detailed forensic analysis results to database.

        Args:
            scan: MediaScan instance
            analysis_results: Results from analyze_image()
        """
        from core.models import ForensicAnalysisResult

        try:
            details = analysis_results['forensic_details']

            # Ensure heatmap_data is serializable
            heatmap_data = analysis_results.get('heatmap_data', {})
            if not isinstance(heatmap_data, dict):
                heatmap_data = {'hotspots': [], 'total_hotspots': 0, 'intensity_level': 'none'}

            # Create or update forensic analysis result
            forensic_result, created = ForensicAnalysisResult.objects.update_or_create(
                scan=scan,
                defaults={
                    # ELA Analysis
                    'ela_score': details['ela_analysis']['score'],
                    'ela_heatmap_data': heatmap_data,

                    # Metadata Analysis
                    'has_exif': details['metadata_analysis']['has_exif'],
                    'exif_data': details['metadata_analysis'].get('exif_data', {}),
                    'metadata_consistency': details['metadata_analysis']['consistency'],
                    'software_detected': details['metadata_analysis']['software_detected'],

                    # Noise Analysis
                    'noise_uniformity': details['noise_analysis']['uniformity'],

                    # Compression Analysis
                    'compression_artifacts_detected': details['compression_analysis']['score'] > 0,
                    'double_compression': details['compression_analysis']['double_compression'],

                    # Color Analysis
                    'color_histogram_score': details['color_analysis']['score'],

                    # Source Detection
                    'detected_sources': analysis_results['source_detection'],
                    'primary_source': details.get('source_detection', {}).get('primary_source'),
                    'source_confidence': details.get('source_detection', {}).get('confidence'),

                    # Overall
                    'manipulation_indicators': analysis_results['manipulation_indicators']
                }
            )

            logger.info(f"Forensic results saved for scan {scan.id}")
            return forensic_result

        except Exception as e:
            logger.error(f"Failed to save forensic results: {str(e)}")
            raise


def analyze_uploaded_file(file_object, file_type: str) -> dict:
    """
    Convenience function to analyze an uploaded file.

    Args:
        file_object: Django UploadedFile object
        file_type: 'image', 'video', 'audio', etc.

    Returns:
        Analysis results dict
    """
    import tempfile
    import os

    # Save uploaded file to temp location
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_object.name)[1]) as tmp_file:
        for chunk in file_object.chunks():
            tmp_file.write(chunk)
        tmp_path = tmp_file.name

    try:
        # Run analysis
        pipeline = ForensicPipeline()
        results = pipeline.analyze_image(tmp_path)
        return results
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
