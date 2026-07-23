"""
Video Forensics Analyzer

Analyzes video files for deepfake detection using:
- Frame-by-frame analysis (reuses ImageForensicsAnalyzer)
- Temporal consistency checks
- Face tracking anomalies
- Motion analysis
"""

import os
import logging
import tempfile
from typing import Dict, Any, List
import numpy as np

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

from .base_analyzer import BaseAnalyzer
from .image_forensics import ImageForensicsAnalyzer

logger = logging.getLogger(__name__)


def _convert_to_native(obj):
    """Convert NumPy types to native Python types for JSON serialization."""
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
    return obj


class VideoForensicsAnalyzer(BaseAnalyzer):
    """
    Video forensics analyzer for deepfake detection.

    Extracts frames from video and analyzes them for manipulation.
    """

    def __init__(self, max_frames: int = 20):
        """
        Initialize video analyzer.

        Args:
            max_frames: Maximum number of frames to extract (for performance)
        """
        super().__init__()
        self.name = "VideoForensicsAnalyzer"
        self.version = "1.0.0"
        self.max_frames = max_frames
        self.image_analyzer = ImageForensicsAnalyzer()

    def _validate_video(self, video_path: str) -> None:
        """
        Validate video file.

        Args:
            video_path: Path to video file

        Raises:
            AnalyzerError: If video file is invalid
        """
        if not OPENCV_AVAILABLE:
            raise AnalyzerError("OpenCV not available. Cannot analyze video.")

        if not os.path.exists(video_path):
            raise AnalyzerError(f"Video file not found: {video_path}")

        # Try to open video to validate format
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            cap.release()
            raise AnalyzerError(f"Cannot open video file (may be corrupted or unsupported format): {video_path}")

        # Check if video has frames
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count <= 0:
            cap.release()
            raise AnalyzerError(f"Video file has no frames: {video_path}")

        cap.release()

    def analyze(self, video_path: str, source: str = 'upload') -> Dict[str, Any]:
        """
        Analyze video for deepfake detection.

        Args:
            video_path: Path to video file
            source: Source of video ('upload', 'webcam', 'url')

        Returns:
            dict with analysis results:
                - score: Overall manipulation score (0-100)
                - details: Detailed analysis metrics
                - indicators: List of manipulation indicators
                - source_detected: detected source (upload/webcam/url)
        """
        try:
            self._validate_video(video_path)
            is_webcam = (source == 'webcam')
            logger.info(f"Starting video forensics analysis: {video_path} (source: {source})")

            # Step 1: Extract frames with quality enhancement
            frames_data = self._extract_frames(video_path, is_webcam=is_webcam)

            if not frames_data['frames']:
                logger.warning("No frames extracted from video")
                return self._fallback_analysis()

            logger.info(f"Extracted {len(frames_data['frames'])} frames for analysis")

            # Step 2: Analyze each frame
            try:
                frame_analysis = self._analyze_frames(frames_data, is_webcam=is_webcam)
            except Exception as e:
                logger.error(f"Frame analysis failed: {str(e)}")
                frame_analysis = {
                    'frame_scores': [50.0] * len(frames_data['frames']),
                    'average_score': 50.0,
                    'std_deviation': 0.0,
                    'max_score': 50.0,
                    'min_score': 50.0
                }

            # Step 3: Temporal consistency analysis
            try:
                temporal_analysis = self._analyze_temporal_consistency(
                    frames_data,
                    frame_analysis
                )
            except Exception as e:
                logger.error(f"Temporal analysis failed: {str(e)}")
                temporal_analysis = {
                    'consistency_score': 100.0,
                    'avg_brightness_change': 0.0,
                    'max_brightness_change': 0.0
                }

            # Step 4: Face tracking analysis
            try:
                face_analysis = self._analyze_face_tracking(frames_data)
            except Exception as e:
                logger.error(f"Face tracking failed: {str(e)}")
                face_analysis = {
                    'faces_detected': 0,
                    'face_positions': [],
                    'movement_anomalies': 0,
                    'detection_rate': 0.0
                }

            # Step 5: Motion analysis (with webcam adjustment)
            try:
                motion_analysis = self._analyze_motion(frames_data, is_webcam=is_webcam)
            except Exception as e:
                logger.error(f"Motion analysis failed: {str(e)}")
                motion_analysis = {
                    'motion_detected': False,
                    'avg_motion': 0.0,
                    'max_motion': 0.0,
                    'frozen_frames': 0
                }

            # Step 6: Calculate overall score (with webcam adjustment)
            overall_score = self._calculate_overall_score(
                frame_analysis,
                temporal_analysis,
                face_analysis,
                motion_analysis,
                is_webcam=is_webcam
            )

            # Step 7: Compile indicators
            indicators = self._compile_indicators(
                frame_analysis,
                temporal_analysis,
                face_analysis,
                motion_analysis,
                overall_score,
                is_webcam=is_webcam
            )

            logger.info(f"Video analysis complete: {overall_score:.2f}%")

            result = {
                'score': overall_score,
                'details': {
                    'frame_count': frames_data['frame_count'],
                    'analyzed_frames': len(frames_data['frames']),
                    'frame_analysis': frame_analysis,
                    'temporal_consistency': temporal_analysis,
                    'face_tracking': face_analysis,
                    'motion_analysis': motion_analysis
                },
                'indicators': indicators,
                'source_detected': source,
                'is_webcam_capture': is_webcam
            }

            return _convert_to_native(result)

        except Exception as e:
            logger.error(f"Video forensics analysis failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return self._fallback_analysis()

    def _extract_frames(self, video_path: str, is_webcam: bool = False) -> Dict[str, Any]:
        """
        Extract frames from video for analysis.

        Args:
            video_path: Path to video file
            is_webcam: True if video is from webcam (adjusts extraction quality)

        Returns:
            dict with frames and metadata
        """
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            return {'frames': [], 'frame_count': 0, 'fps': 0}

        # Get video properties
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = frame_count / fps if fps > 0 else 0

        # Calculate frame extraction interval
        # For webcam videos, extract more frames for better analysis
        max_frames = self.max_frames * 2 if is_webcam else self.max_frames

        if frame_count <= max_frames:
            interval = 1
        else:
            interval = frame_count // max_frames

        frames = []
        frame_indices = []

        # Extract frames with quality improvement
        frame_idx = 0
        while len(frames) < max_frames and frame_idx < frame_count:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()

            if ret:
                # Enhance frame quality for analysis
                if is_webcam:
                    # Apply mild denoising for webcam frames
                    frame = cv2.fastNlMeansDenoisingColored(frame, None, 3, 3, 7, 21)

                    # Ensure minimum resolution
                    h, w = frame.shape[:2]
                    if h < 512 or w < 512:
                        scale = max(512 / h, 512 / w)
                        new_h, new_w = int(h * scale), int(w * scale)
                        frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

                frames.append(frame)
                frame_indices.append(frame_idx)

            frame_idx += interval

        cap.release()

        logger.info(f"Extracted {len(frames)} frames from video (total: {frame_count}, source: {'webcam' if is_webcam else 'upload'})")

        return {
            'frames': frames,
            'frame_indices': frame_indices,
            'frame_count': frame_count,
            'fps': fps,
            'duration': duration
        }

    def _analyze_frames(self, frames_data: Dict[str, Any], is_webcam: bool = False) -> Dict[str, Any]:
        """
        Analyze each extracted frame.

        Args:
            frames_data: Frames extracted from video
            is_webcam: True if video is from webcam (adjusts analysis)

        Returns:
            Frame analysis results
        """
        frames = frames_data['frames']
        frame_scores = []
        frame_details = []

        for i, frame in enumerate(frames):
            try:
                # Save frame to temp file for ImageForensicsAnalyzer
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    # Use higher quality for frame save to preserve details
                    cv2.imwrite(tmp.name, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                    tmp_path = tmp.name

                # Analyze frame with source parameter
                try:
                    # Mark frames as video frames so image analyzer applies lenient thresholds
                    frame_source = 'webcam' if is_webcam else 'video-frame'
                    result = self.image_analyzer.analyze(tmp_path, source=frame_source)
                    frame_scores.append(result.get('score', 50.0))
                    frame_details.append(result.get('details', {}))
                except Exception as analyze_err:
                    logger.warning(f"Frame {i} analysis error: {str(analyze_err)}")
                    frame_scores.append(50.0)  # Neutral score
                    frame_details.append({})

                # Clean up temp file
                try:
                    os.unlink(tmp_path)
                except:
                    pass

            except Exception as e:
                logger.warning(f"Failed to process frame {i}: {str(e)}")
                frame_scores.append(50.0)  # Neutral score
                frame_details.append({})

        # Calculate statistics
        if frame_scores:
            avg_score = float(np.mean(frame_scores))
            std_score = float(np.std(frame_scores))
            max_score = float(max(frame_scores))
            min_score = float(min(frame_scores))
        else:
            avg_score = 50.0
            std_score = 0.0
            max_score = 50.0
            min_score = 50.0

        return {
            'frame_scores': frame_scores,
            'average_score': avg_score,
            'std_deviation': std_score,
            'max_score': max_score,
            'min_score': min_score
        }

    def _analyze_temporal_consistency(
        self,
        frames_data: Dict[str, Any],
        frame_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze temporal consistency across frames.

        Detects inconsistencies in lighting, background, and scene composition
        that may indicate manipulation.

        Args:
            frames_data: Extracted frames
            frame_analysis: Results from frame analysis

        Returns:
            Temporal consistency metrics
        """
        frames = frames_data['frames']

        if len(frames) < 2:
            return {
                'consistency_score': 100.0,
                'lighting_variations': [],
                'brightness_changes': []
            }

        # Calculate brightness for each frame
        brightness_values = []
        for frame in frames:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness = np.mean(gray)
            brightness_values.append(brightness)

        # Calculate brightness variations
        brightness_changes = []
        for i in range(1, len(brightness_values)):
            change = abs(brightness_values[i] - brightness_values[i-1])
            brightness_changes.append(change)

        # High variations suggest potential manipulation
        avg_change = np.mean(brightness_changes) if brightness_changes else 0
        max_change = max(brightness_changes) if brightness_changes else 0

        # Consistency score: lower changes = higher consistency
        # Normalize: 0 change = 100 consistency, 50+ change = 0 consistency
        consistency_score = max(0, 100 - (avg_change * 2))

        return {
            'consistency_score': consistency_score,
            'avg_brightness_change': avg_change,
            'max_brightness_change': max_change,
            'lighting_variations': brightness_changes[:10]  # First 10 for storage
        }

    def _analyze_face_tracking(self, frames_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze face tracking across frames.

        Detects unnatural face movements or inconsistencies.

        Args:
            frames_data: Extracted frames

        Returns:
            Face tracking analysis results
        """
        frames = frames_data['frames']

        # Simple face detection using Haar cascade (faster than DNN)
        try:
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
        except:
            # Fallback if cascade file not available
            return {
                'faces_detected': 0,
                'face_positions': [],
                'movement_anomalies': 0
            }

        face_positions = []

        for frame in frames:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )

            if len(faces) > 0:
                # Use the largest face, but remember if the frame was crowded —
                # in multi-person scenes the "largest face" can flip between people.
                largest_face = max(faces, key=lambda x: x[2] * x[3])
                face_positions.append({
                    'x': int(largest_face[0]),
                    'y': int(largest_face[1]),
                    'w': int(largest_face[2]),
                    'h': int(largest_face[3]),
                    'multi': len(faces) > 1
                })

        # Analyze movement anomalies — only between frames that plausibly
        # show the SAME face (no multi-face frames, similar size).
        movement_anomalies = 0
        comparable_pairs = 0
        if len(face_positions) > 1 and frames:
            # Scale threshold to frame size so HD video isn't unfairly penalized.
            fh, fw = frames[0].shape[:2]
            distance_threshold = max(100.0, min(fh, fw) * 0.20)

            for i in range(1, len(face_positions)):
                prev = face_positions[i - 1]
                curr = face_positions[i]

                # Crowded frames almost always mean we're comparing different
                # people across frames — skip these pairs entirely.
                if prev.get('multi') or curr.get('multi'):
                    continue

                # Drastic size change → different person, not movement.
                size_ratio = curr['w'] / max(prev['w'], 1)
                if size_ratio < 0.7 or size_ratio > 1.43:
                    continue

                comparable_pairs += 1
                distance = np.sqrt(
                    (curr['x'] - prev['x']) ** 2 +
                    (curr['y'] - prev['y']) ** 2
                )
                if distance > distance_threshold:
                    movement_anomalies += 1

        # Sanity check: a genuine deepfake would have a FEW jerky moments,
        # not constant teleportation. A high anomaly ratio means the cascade
        # is locking onto different people frame-to-frame, not tracking a
        # single face — discard the signal.
        if comparable_pairs >= 3 and (movement_anomalies / comparable_pairs) > 0.4:
            movement_anomalies = 0

        return {
            'faces_detected': len(face_positions),
            'face_positions': [{k: v for k, v in p.items() if k != 'multi'}
                               for p in face_positions[:5]],
            'movement_anomalies': movement_anomalies,
            'comparable_pairs': comparable_pairs,
            'detection_rate': len(face_positions) / len(frames) if frames else 0
        }

    def _analyze_motion(self, frames_data: Dict[str, Any], is_webcam: bool = False) -> Dict[str, Any]:
        """
        Analyze motion patterns in video.

        Detects unnatural motion or frozen frames.

        Args:
            frames_data: Extracted frames
            is_webcam: True if video is from webcam (adjusts thresholds)

        Returns:
            Motion analysis results
        """
        frames = frames_data['frames']

        if len(frames) < 2:
            return {
                'motion_detected': False,
                'avg_motion': 0.0,
                'frozen_frames': 0
            }

        motion_scores = []

        # Calculate motion between consecutive frames
        for i in range(1, len(frames)):
            prev_gray = cv2.cvtColor(frames[i-1], cv2.COLOR_BGR2GRAY)
            curr_gray = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)

            # Calculate absolute difference
            diff = cv2.absdiff(prev_gray, curr_gray)
            motion_score = np.mean(diff)
            motion_scores.append(motion_score)

        # Adjust thresholds for webcam (webcam videos have different motion patterns)
        if is_webcam:
            frozen_threshold = 3.0  # Lower threshold for webcam (can have less motion)
            motion_threshold = 3.0
        else:
            frozen_threshold = 5.0
            motion_threshold = 5.0

        # Detect frozen frames (very low motion)
        frozen_frames = sum(1 for score in motion_scores if score < frozen_threshold)
        avg_motion = np.mean(motion_scores) if motion_scores else 0.0

        return {
            'motion_detected': avg_motion > motion_threshold,
            'avg_motion': avg_motion,
            'max_motion': max(motion_scores) if motion_scores else 0.0,
            'frozen_frames': frozen_frames,
            'motion_scores': motion_scores[:10],  # Store first 10
            'is_webcam_adjusted': is_webcam
        }

    def _calculate_overall_score(
        self,
        frame_analysis: Dict[str, Any],
        temporal_analysis: Dict[str, Any],
        face_analysis: Dict[str, Any],
        motion_analysis: Dict[str, Any],
        is_webcam: bool = False
    ) -> float:
        """
        Calculate overall manipulation score from all analyses.

        Args:
            frame_analysis: Frame analysis results
            temporal_analysis: Temporal consistency results
            face_analysis: Face tracking results
            motion_analysis: Motion analysis results
            is_webcam: True if video is from webcam (adjusts weights)

        Returns:
            Overall score (0-100)
        """
        if is_webcam:
            # Adjusted weights for webcam videos
            # Frame analysis: 60% (main detector for webcam)
            # Temporal consistency: 20% (reduced)
            # Face tracking: 10% (reduced)
            # Motion analysis: 10% (reduced)
            weights = {'frame': 0.60, 'temporal': 0.20, 'face': 0.10, 'motion': 0.10}
        else:
            # Normal weights for uploaded videos
            # Frame analysis: 50%
            # Temporal consistency: 25%
            # Face tracking: 15%
            # Motion analysis: 10%
            weights = {'frame': 0.50, 'temporal': 0.25, 'face': 0.15, 'motion': 0.10}

        frame_score = frame_analysis['average_score']
        temporal_score = 100 - temporal_analysis['consistency_score']  # Invert: low consistency = high manipulation
        # Hyper-consistency penalty: AI videos often have unnaturally perfect consistency (>95%)
        if temporal_analysis['consistency_score'] > 95:
            temporal_score += 30  # Boost score for unnaturally consistent video
        temporal_score = min(100, temporal_score)
        # Face anomalies are noisy when detection is unreliable (low rate, few comparable
        # pairs) — scale the signal so it can't dominate based on sparse data.
        raw_face_score = min(100, face_analysis['movement_anomalies'] * 30)
        detection_rate = face_analysis.get('detection_rate', 0)
        comparable_pairs = face_analysis.get('comparable_pairs', 0)
        # Require at least 4 comparable pairs before trusting the anomaly signal fully.
        pair_confidence = min(1.0, comparable_pairs / 4.0)
        face_score = raw_face_score * detection_rate * pair_confidence

        # Adjust motion score calculation for webcam
        if is_webcam:
            motion_score = min(100, motion_analysis['frozen_frames'] * 8 + (100 if motion_analysis['avg_motion'] < 3 else 0))
        else:
            motion_score = min(100, motion_analysis['frozen_frames'] * 10 + (100 if motion_analysis['avg_motion'] < 5 else 0))

        overall = (
            frame_score * weights['frame'] +
            temporal_score * weights['temporal'] +
            face_score * weights['face'] +
            motion_score * weights['motion']
        )

        # Apply soft cap to reduce false positives on real videos
        # Real videos often score higher due to codec compression, temporal variations, etc.
        # This brings down the score for typical real videos while keeping clearly fake videos high
        if is_webcam and 15 <= overall <= 50:
            # Webcam videos are most lenient
            overall = overall * 0.60  # Reduce by 40%
        elif not is_webcam and 20 <= overall <= 55:
            # Uploaded real videos often score 30-45 due to compression
            # This reduces that range significantly but preserves AI-generated video signals
            overall = overall * 0.75  # Reduce by 25%

        return round(overall, 2)

    def _compile_indicators(
        self,
        frame_analysis: Dict[str, Any],
        temporal_analysis: Dict[str, Any],
        face_analysis: Dict[str, Any],
        motion_analysis: Dict[str, Any],
        overall_score: float,
        is_webcam: bool = False
    ) -> List[str]:
        """
        Compile list of manipulation indicators.

        Args:
            frame_analysis: Frame analysis results
            temporal_analysis: Temporal consistency results
            face_analysis: Face tracking results
            motion_analysis: Motion analysis results
            overall_score: Overall score
            is_webcam: True if video is from webcam (adjusts indicators)

        Returns:
            List of indicator strings
        """
        indicators = []

        # Frame analysis indicators (with webcam adjustment)
        frame_threshold = 50 if is_webcam else 60
        if frame_analysis['average_score'] > frame_threshold:
            high_score_frames = sum(1 for s in frame_analysis['frame_scores'] if s > frame_threshold)
            indicators.append(f"High manipulation detected in {high_score_frames} frames")
        if frame_analysis['std_deviation'] > 20:
            indicators.append("Inconsistent manipulation across frames")

        # Temporal indicators
        temporal_threshold = 50 if is_webcam else 60
        if temporal_analysis['consistency_score'] < temporal_threshold:
            indicators.append("Lighting inconsistencies detected")
        if temporal_analysis['consistency_score'] > 95:
            indicators.append("Unnaturally consistent lighting/background (AI generation suspected)")
        if temporal_analysis['max_brightness_change'] > 50:
            indicators.append("Sudden lighting changes")

        # Face tracking indicators
        if face_analysis['movement_anomalies'] > 2:
            indicators.append("Unnatural face movement patterns")
        if face_analysis['detection_rate'] < 0.5:
            indicators.append("Face detection inconsistencies")

        # Motion indicators
        if motion_analysis['frozen_frames'] > 3:
            indicators.append("Frozen frames detected")
        if motion_analysis['avg_motion'] < 5:
            indicators.append("Unusually low motion")

        return indicators

    def _fallback_analysis(self) -> Dict[str, Any]:
        """
        Fallback analysis when video processing fails.

        Returns:
            Neutral/unknown analysis result with all required keys
        """
        return {
            'score': 50.0,
            'details': {
                'frame_count': 0,
                'analyzed_frames': 0,
                'frame_analysis': {
                    'frame_scores': [],
                    'average_score': 50.0,
                    'std_deviation': 0.0,
                    'max_score': 50.0,
                    'min_score': 50.0
                },
                'temporal_consistency': {
                    'consistency_score': 100.0,
                    'avg_brightness_change': 0.0,
                    'max_brightness_change': 0.0,
                    'lighting_variations': []
                },
                'face_tracking': {
                    'faces_detected': 0,
                    'face_positions': [],
                    'movement_anomalies': 0,
                    'detection_rate': 0.0
                },
                'motion_analysis': {
                    'motion_detected': False,
                    'avg_motion': 0.0,
                    'max_motion': 0.0,
                    'frozen_frames': 0,
                    'motion_scores': []
                }
            },
            'indicators': ['Video analysis not available - using fallback']
        }
