"""
Forensic Pipeline - Orchestrates all analyzers

Coordinates the forensic analysis workflow:
1. Classical Forensics (ELA, metadata, noise, compression, color, spectral)
2. AI Deepfake Detection (ResNet-18, R3D-18, Wav2Vec2 via Hugging Face)
3. Source Detector (AI generator identification)
4. Score Fusion (weighted combination of forensics + AI model)
5. Classification and result aggregation
6. Database storage
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
        self.image_ai_detector = None  # Lazy loaded
        self.video_ai_detector = None  # Lazy loaded
        self.audio_ai_detector = None  # Lazy loaded

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

            # Step 1b: Run AI Deepfake Detection Model (if not webcam)
            ai_result = None
            if source != 'webcam':
                try:
                    if self.image_ai_detector is None:
                        from .ai_deepfake_detector import ImageAIDetector
                        self.image_ai_detector = ImageAIDetector()
                    logger.info("Running AI deepfake detection model...")
                    ai_result = self.image_ai_detector.analyze(image_path)
                    logger.info(f"AI model score: {ai_result['score']}")
                except Exception as e:
                    logger.warning(f"AI detection failed, using forensics only: {e}")
                    ai_result = None

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
            forensic_score = forensic_results['score']

            # Score fusion: combine forensics + AI model
            if ai_result is not None and ai_result.get('score') is not None:
                confidence_score = self._combine_scores(forensic_score, ai_result['score'])
                logger.info(f"Score fusion: forensics={forensic_score}, ai={ai_result['score']}, combined={confidence_score}")
            else:
                confidence_score = forensic_score
                logger.info(f"No AI model result, using forensics score: {forensic_score}")

            trust_score = 100 - confidence_score

            # Check if image has AI-standard resolution
            details = forensic_results.get('details', {})
            ai_res = False
            if 'preprocessing' in details:
                orig_size = details['preprocessing'].get('original_size', (0, 0))
                ai_dims = {256, 512, 768, 1024, 1536, 1792, 2048}
                ai_res = orig_size[0] in ai_dims or orig_size[1] in ai_dims

            # Adjust confidence based on source detection (only for non-webcam)
            if detected_sources and source != 'webcam':
                primary_source_confidence = detected_sources[0]['confidence']
                primary_source = detected_sources[0]['source']

                # Only boost if source confidence is high AND resolution is AI-like
                # OR if source is a specific known generator with very high confidence
                if primary_source_confidence > 55 and ai_res:
                    confidence_score = min(100, confidence_score * 1.15)
                    trust_score = 100 - confidence_score
                elif primary_source_confidence > 40 and ai_res:
                    confidence_score = min(100, confidence_score * 1.08)
                    trust_score = 100 - confidence_score
                elif primary_source_confidence > 65 and not ai_res:
                    # Very high confidence can still boost even on weird resolutions
                    confidence_score = min(100, confidence_score * 1.05)
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
                'manipulation_indicators': forensic_results['indicators'],
                'ai_detection': ai_result.get('details', {}) if ai_result else None,
                'ai_model_score': ai_result.get('score') if ai_result else None,
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

            # Step 1b: Run AI Deepfake Detection Model on video (if not webcam)
            ai_result = None
            if source != 'webcam':
                try:
                    if self.video_ai_detector is None:
                        from .ai_deepfake_detector import VideoAIDetector
                        self.video_ai_detector = VideoAIDetector()
                    logger.info("Running AI deepfake detection on video...")
                    ai_result = self.video_ai_detector.analyze(video_path)
                    logger.info(f"AI video model score: {ai_result['score']}")
                except Exception as e:
                    logger.warning(f"AI video detection failed, using forensics only: {e}")
                    ai_result = None

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
            forensic_score = video_results['score']

            # Score fusion: combine forensics + AI model
            if ai_result is not None and ai_result.get('score') is not None:
                confidence_score = self._combine_scores(forensic_score, ai_result['score'])
                logger.info(f"Video score fusion: forensics={forensic_score}, ai={ai_result['score']}, combined={confidence_score}")
            else:
                confidence_score = forensic_score

            trust_score = 100 - confidence_score

            # Boost confidence for strong video-specific AI signals
            video_details = video_results.get('details', {})
            face_tracking = video_details.get('face_tracking', {})
            temporal = video_details.get('temporal_consistency', {})
            anomalies = face_tracking.get('movement_anomalies', 0)
            consistency = temporal.get('consistency_score', 50)

            # Only boost confidence when BOTH signals corroborate — face anomalies
            # alone are too noisy on multi-person handheld video to justify a boost
            # (the anomaly count already feeds into video_fake_signals downstream,
            # so adding it here was double-counting the same evidence).
            if anomalies >= 6 and consistency > 95:
                confidence_score = min(100, confidence_score + 25)
            elif anomalies >= 4 and consistency > 95:
                confidence_score = min(100, confidence_score + 20)
            elif anomalies >= 3 and consistency > 95:
                confidence_score = min(100, confidence_score + 12)
            elif consistency > 95:
                confidence_score = min(100, confidence_score + 8)

            trust_score = 100 - confidence_score

            # Adjust confidence if AI video source detected (only for non-webcam).
            # Skip the boost for generic/unnamed signature matches — those are
            # often false positives on real handheld video.
            if detected_sources and source != 'webcam':
                primary = detected_sources[0]
                primary_source_confidence = primary.get('confidence', 0)
                primary_name = (primary.get('name')
                                or primary.get('source')
                                or '').strip()
                if primary_name:
                    if primary_source_confidence > 50:
                        confidence_score = min(100, confidence_score * 1.25)
                        trust_score = 100 - confidence_score
                    elif primary_source_confidence > 30:
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

            frame_analysis = details.get('frame_analysis', {})
            analysis_details = {
                'video_analysis': {
                    'frame_count': details.get('frame_count', 0),
                    'analyzed_frames': details.get('analyzed_frames', 0),
                    'frame_analysis': {
                        'average_score': frame_analysis.get('average_score', 0.0),
                        'frame_scores': frame_analysis.get('frame_scores', []),
                        'max_score': frame_analysis.get('max_score', 0.0),
                        'min_score': frame_analysis.get('min_score', 0.0),
                        'std_deviation': frame_analysis.get('std_deviation', 0.0)
                    },
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
                'manipulation_indicators': video_results['indicators'],
                'ai_detection': ai_result.get('details', {}) if ai_result else None,
                'ai_model_score': ai_result.get('score') if ai_result else None,
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

            # Step 1b: Run AI Deepfake Audio Detection Model (if not webcam)
            ai_result = None
            if source != 'webcam':
                try:
                    if self.audio_ai_detector is None:
                        from .ai_deepfake_detector import AudioAIDetector
                        self.audio_ai_detector = AudioAIDetector()
                    logger.info("Running AI deepfake detection on audio...")
                    ai_result = self.audio_ai_detector.analyze(audio_path)
                    logger.info(f"AI audio model score: {ai_result['score']}")
                except Exception as e:
                    logger.warning(f"AI audio detection failed, using forensics only: {e}")
                    ai_result = None

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
            forensic_score = audio_results['score']

            # Score fusion: combine forensics + AI model
            if ai_result is not None and ai_result.get('score') is not None:
                confidence_score = self._combine_scores(forensic_score, ai_result['score'])
                logger.info(f"Audio score fusion: forensics={forensic_score}, ai={ai_result['score']}, combined={confidence_score}")
            else:
                confidence_score = forensic_score

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
                'manipulation_indicators': audio_results['indicators'],
                'ai_detection': ai_result.get('details', {}) if ai_result else None,
                'ai_model_score': ai_result.get('score') if ai_result else None,
            }

            return _convert_to_native(result)

        except Exception as e:
            logger.error(f"Audio forensic pipeline failed: {str(e)}")
            raise

    def _combine_scores(self, forensic_score: float, ai_score: float) -> float:
        """
        Combine classical forensics score with AI model score.

        Uses weighted fusion: AI model gets higher weight (0.6) since it's a
        trained classifier, while forensics gets 0.4 as supplementary signal.

        If scores strongly disagree (both below 20 or both above 80),
        the higher confidence model gets extra weight.

        Args:
            forensic_score: Score from classical forensics (0-100)
            ai_score: Score from AI model (0-100)

        Returns:
            Combined score (0-100)
        """
        forensic_weight = 0.4
        ai_weight = 0.6

        # If both models agree strongly, boost confidence
        agreement = abs(forensic_score - ai_score)
        if agreement < 15:
            # Strong agreement - boost the combined score away from 50
            base = forensic_weight * forensic_score + ai_weight * ai_score
            boost = (50 - abs(base - 50)) * 0.1  # Pull toward extremes
            if base > 50:
                return min(100, base + boost)
            else:
                return max(0, base - boost)

        # If models disagree significantly, trust the AI model more
        if agreement > 40:
            # Strong disagreement - lean toward AI model
            return 0.3 * forensic_score + 0.7 * ai_score

        # Normal weighted fusion
        return forensic_weight * forensic_score + ai_weight * ai_score

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

        Uses a multi-signal approach to avoid false positives on real photos.
        """
        top_level_details = forensic_results.get('forensic_details', {})
        details = forensic_results.get('details', {})
        is_video = 'video_analysis' in top_level_details or 'frame_analysis' in details
        is_audio = 'audio_analysis' in top_level_details

        forensic_details = details
        ai_artifact_score = forensic_details.get('ai_artifacts', {}).get('score', 0)
        spectral_score = forensic_details.get('spectral', {}).get('score', 0)
        ela_score = forensic_details.get('ela', {}).get('score', 0)
        color_score = forensic_details.get('color', {}).get('score', 0)
        face_smoothness = forensic_details.get('ai_artifacts', {}).get('face_smoothness', 0.5)

        # Check if resolution is a known AI dimension
        ai_dims = {256, 512, 768, 1024, 1536, 1792, 2048}
        preprocessing = forensic_details.get('preprocessing', {})
        orig_size = preprocessing.get('original_size', (0, 0))
        is_ai_resolution = orig_size[0] in ai_dims or orig_size[1] in ai_dims

        # WEBCAM IMAGES: Almost always REAL unless extremely strong evidence
        # Webcam captures inherently have compression, noise, and lighting artifacts
        # that mimic AI signals. Require much higher bar for FAKE.
        if source == 'webcam':
            if confidence_score >= 70:
                return 'fake'
            elif confidence_score >= 45:
                return 'suspicious'
            else:
                return 'real'

        # VIDEO-SPECIFIC DETECTION LOGIC
        # Videos have different signal patterns than images
        if is_video:
            video_details = forensic_results.get('details', {})
            face_tracking = video_details.get('face_tracking', {})
            temporal = video_details.get('temporal_consistency', {})
            motion = video_details.get('motion_analysis', {})

            video_fake_signals = 0
            # Face tracking anomalies are strong indicators of AI-generated video
            anomalies = face_tracking.get('movement_anomalies', 0)
            if anomalies >= 6:
                video_fake_signals += 2
            elif anomalies >= 3:
                video_fake_signals += 1

            # Hyper-consistent temporal analysis suggests AI generation
            consistency = temporal.get('consistency_score', 50)
            if consistency > 95:
                video_fake_signals += 1

            # Motion anomalies
            frozen = motion.get('frozen_frames', 0)
            avg_motion = motion.get('avg_motion', 100)
            if frozen >= 2:
                video_fake_signals += 1
            if avg_motion < 3:
                video_fake_signals += 1

            # AI video source detection — ignore unnamed/generic signature matches
            # (the detector emits these on real video and they shouldn't escalate).
            if detected_sources:
                src = detected_sources[0]
                source_conf = src.get('confidence', 0)
                source_name = (src.get('name') or src.get('source') or '').lower().strip()
                if source_name:
                    is_video_source = any(s in source_name for s in ['sora', 'runway', 'pika', 'heygen', 'd-id', 'deepvideo'])
                    if is_video_source and source_conf >= 30:
                        video_fake_signals += 2
                    elif source_conf >= 50:
                        video_fake_signals += 1
                    elif source_conf >= 30:
                        video_fake_signals += 1

            # Video-specific thresholds (more sensitive to AI indicators)
            # Strong AI video signals should override lower confidence scores
            if confidence_score >= 35 and video_fake_signals >= 2:
                return 'fake'
            if confidence_score >= 25 and video_fake_signals >= 3:
                return 'fake'
            if confidence_score >= 15 and video_fake_signals >= 4:
                return 'fake'
            # Direct FAKE override: AI video source + face anomalies is definitive
            if anomalies >= 3 and detected_sources:
                src_name = detected_sources[0].get('name', '').lower()
                if any(s in src_name for s in ['sora', 'runway', 'pika', 'heygen', 'd-id', 'deepvideo']):
                    return 'fake'
            if video_fake_signals >= 2:
                return 'suspicious'
            if confidence_score < 15:
                return 'real'
            elif confidence_score <= 35:
                return 'suspicious'
            else:
                return 'fake'

        # STRONG FAKE: Requires very strong multi-signal evidence
        fake_signals = 0
        if confidence_score >= 55:
            fake_signals += 2
        elif confidence_score >= 45:
            fake_signals += 1

        if spectral_score >= 50:
            fake_signals += 2
        elif spectral_score >= 35:
            fake_signals += 1

        if ai_artifact_score >= 55:
            fake_signals += 2
        elif ai_artifact_score >= 40:
            fake_signals += 1

        if detected_sources and detected_sources[0]['confidence'] >= 60:
            fake_signals += 2
        elif detected_sources and detected_sources[0]['confidence'] >= 45:
            fake_signals += 1

        # Need at least 4 fake signals OR confidence >= 50 with spectral support
        if fake_signals >= 4 or (confidence_score >= 50 and spectral_score >= 30):
            return 'fake'

        # STRONG REAL RESCUE: Real photos often have these characteristics
        real_signals = 0
        if ela_score < 10:  # No editing detected
            real_signals += 1
        if color_score < 10:  # Natural colors
            real_signals += 1
        if face_smoothness < 0.25:  # Real facial texture
            real_signals += 1
        if not is_ai_resolution:  # Non-standard AI resolution = likely real
            real_signals += 2
        if spectral_score < 25:  # Natural frequency spectrum
            real_signals += 1

        # Need at least 4 real signals to override to REAL even if in suspicious range
        if real_signals >= 4 and confidence_score < 40:
            return 'real'

        # SUSPICIOUS: Some signals but not enough for definitive FAKE
        if fake_signals >= 2:
            return 'suspicious'

        # DEFAULT THRESHOLDS
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

        # Add AI artifact analysis
        if 'ai_artifacts' in details:
            try:
                analysis_details['ai_artifact_analysis'] = {
                    'score': float(details['ai_artifacts']['score']),
                    'background_uniformity': float(details['ai_artifacts'].get('background_uniformity', 0)),
                    'face_smoothness': float(details['ai_artifacts'].get('face_smoothness', 0)),
                    'diffusion_fingerprint': float(details['ai_artifacts'].get('diffusion_fingerprint', 0.5)),
                    'findings': list(details['ai_artifacts'].get('findings', []))
                }
            except (KeyError, TypeError):
                pass

        # Add spectral analysis
        if 'spectral' in details:
            try:
                analysis_details['spectral_analysis'] = {
                    'score': float(details['spectral']['score']),
                    'spectral_slope': float(details['spectral'].get('details', {}).get('spectral_slope', 0)),
                    'high_freq_ratio': float(details['spectral'].get('details', {}).get('high_freq_ratio', 0)),
                    'grid_artifact_score': float(details['spectral'].get('details', {}).get('grid_artifact_score', 0)),
                    'findings': list(details['spectral'].get('indicators', []))
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
