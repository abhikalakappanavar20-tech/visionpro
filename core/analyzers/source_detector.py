"""
AI Generator Source Detector

Identifies which AI generator likely created media by matching
forensic characteristics against known signatures.

Supports detection of:
Image Generators:
- Midjourney v5/v6
- DALL-E 2/3
- Stable Diffusion
- Adobe Firefly
- Leonardo.ai
- Ideogram
- DeepFaceLab / Faceswap (face manipulation)

Video Generators:
- Sora
- Runway Gen-2/Gen-3
- Pika Labs
- HeyGen
- D-ID
- DeepVideo Labs

Audio Generators:
- ElevenLabs
- Murf.ai
- Play.ht
- Resemble.ai
- Respeecher
"""

import logging
from typing import List, Dict, Any
import numpy as np

from .base_analyzer import BaseAnalyzer

logger = logging.getLogger(__name__)


class SourceDetector(BaseAnalyzer):
    """
    Detect AI generator sources by matching forensic patterns.

    Uses signature matching to identify which AI generator
    likely created an image.
    """

    # AI Generator Signatures Database
    GENERATOR_SIGNATURES = {
        'Midjourney v5': {
            'typical_resolutions': ['1024x1024', '2048x2048', '1024x1792'],
            'noise_pattern': {
                'uniformity_range': (0.4, 0.6),
                'distribution': 'non-uniform',
                'characteristics': ['patchy', 'inconsistent_across_regions']
            },
            'color_signature': {
                'saturation_range': (140, 180),
                'contrast_range': (50, 80),
                'warmth': 'slightly_warm',
                'characteristic': 'high_saturation'
            },
            'ela_threshold': (15, 35),
            'metadata_patterns': {
                'missing_exif': True,
                'software_signatures': []
            },
            'compression_artifacts': 'minimal_high_quality',
            'key_indicators': [
                'High saturation with warm tone',
                'Non-uniform noise distribution',
                'Clean edges with occasional artifacts',
                '1024x1024 or 2048x2048 resolution',
                'No EXIF data'
            ]
        },
        'Midjourney v6': {
            'typical_resolutions': ['1024x1024', '2048x2048', '1920x1080', '1080x1920'],
            'noise_pattern': {
                'uniformity_range': (0.5, 0.7),
                'distribution': 'relatively_uniform',
                'characteristics': ['smooth', 'photorealistic']
            },
            'color_signature': {
                'saturation_range': (110, 150),
                'contrast_range': (45, 75),
                'warmth': 'neutral',
                'characteristic': 'photorealistic_color'
            },
            'ela_threshold': (10, 30),
            'metadata_patterns': {
                'missing_exif': True,
                'software_signatures': []
            },
            'compression_artifacts': 'minimal',
            'key_indicators': [
                'Photorealistic quality',
                'Relatively uniform noise',
                'Multiple resolution options',
                'No EXIF data',
                'Improved text rendering'
            ]
        },
        'DALL-E 2': {
            'typical_resolutions': ['1024x1024', '512x512'],
            'noise_pattern': {
                'uniformity_range': (0.5, 0.7),
                'distribution': 'relatively_uniform',
                'characteristics': ['smooth', 'painterly']
            },
            'color_signature': {
                'saturation_range': (110, 160),
                'contrast_range': (45, 75),
                'characteristic': 'vivid_colors'
            },
            'ela_threshold': (12, 28),
            'metadata_patterns': {
                'missing_exif': True,
                'watermark_possible': False
            },
            'compression_artifacts': 'minimal',
            'key_indicators': [
                'Painterly style',
                'Smooth textures',
                '512x512 or 1024x1024 resolution',
                'No EXIF data',
                'Vivid but balanced colors'
            ]
        },
        'DALL-E 3': {
            'typical_resolutions': ['1024x1024'],
            'noise_pattern': {
                'uniformity_range': (0.5, 0.7),
                'distribution': 'relatively_uniform',
                'characteristics': ['smooth', 'low_texture_detail']
            },
            'color_signature': {
                'saturation_range': (100, 150),
                'contrast_range': (40, 70),
                'characteristic': 'vivid_colors'
            },
            'ela_threshold': (10, 25),
            'metadata_patterns': {
                'missing_exif': True,
                'watermark_possible': True
            },
            'compression_artifacts': 'minimal',
            'key_indicators': [
                'Balanced vivid colors',
                'Relatively smooth surfaces',
                '1024x1024 resolution',
                'Possible watermark',
                'No EXIF data'
            ]
        },
        'Stable Diffusion': {
            'typical_resolutions': ['512x512', '768x768', '1024x1024'],
            'noise_pattern': {
                'uniformity_range': (0.3, 0.5),
                'distribution': 'inconsistent',
                'characteristics': ['grainy', 'artifacts_in_edges']
            },
            'color_signature': {
                'saturation_range': (120, 170),
                'contrast_range': (60, 90),
                'characteristic': 'high_contrast'
            },
            'ela_threshold': (20, 40),
            'metadata_patterns': {
                'missing_exif': True,
                'compression_signatures': True
            },
            'compression_artifacts': 'visible_compression_blocks',
            'key_indicators': [
                'High contrast and saturation',
                'Grainy noise pattern',
                'Edge artifacts',
                'Common resolutions: 512x512, 768x768',
                'Compression block artifacts'
            ]
        },
        'Stable Diffusion XL': {
            'typical_resolutions': ['1024x1024', '1024x768', '768x1024', '1536x640', '640x1536'],
            'noise_pattern': {
                'uniformity_range': (0.4, 0.6),
                'distribution': 'relatively_uniform',
                'characteristics': ['smooth', 'detailed']
            },
            'color_signature': {
                'saturation_range': (115, 165),
                'contrast_range': (55, 85),
                'characteristic': 'enhanced_detail'
            },
            'ela_threshold': (15, 35),
            'metadata_patterns': {
                'missing_exif': True,
                'compression_signatures': True
            },
            'compression_artifacts': 'minimal_to_moderate',
            'key_indicators': [
                'Enhanced detail and sharpness',
                'Multiple aspect ratios',
                'Improved photorealism',
                'No EXIF data',
                'Better text rendering'
            ]
        },
        'Adobe Firefly': {
            'typical_resolutions': ['1920x1080', '1080x1920', '1024x1024', '2048x2048'],
            'noise_pattern': {
                'uniformity_range': (0.5, 0.7),
                'distribution': 'uniform',
                'characteristics': ['smooth', 'professional_quality']
            },
            'color_signature': {
                'saturation_range': (100, 140),
                'contrast_range': (40, 70),
                'characteristic': 'balanced_color'
            },
            'ela_threshold': (10, 28),
            'metadata_patterns': {
                'missing_exif': True,
                'software_signatures': ['Adobe']
            },
            'compression_artifacts': 'minimal',
            'key_indicators': [
                'Professional quality',
                'Balanced colors and contrast',
                'Multiple aspect ratios',
                'Adobe quality standards',
                'Minimal artifacts'
            ]
        },
        'Leonardo.ai': {
            'typical_resolutions': ['1024x1024', '1024x1365', '768x1024', '512x768'],
            'noise_pattern': {
                'uniformity_range': (0.45, 0.65),
                'distribution': 'relatively_uniform',
                'characteristics': ['stylized', 'smooth']
            },
            'color_signature': {
                'saturation_range': (125, 175),
                'contrast_range': (55, 85),
                'characteristic': 'vivid_stylized'
            },
            'ela_threshold': (12, 32),
            'metadata_patterns': {
                'missing_exif': True,
                'software_signatures': []
            },
            'compression_artifacts': 'minimal',
            'key_indicators': [
                'Stylized appearance',
                'Vivid colors',
                'Portrait-oriented common',
                'No EXIF data',
                'Artistic quality'
            ]
        },
        'Ideogram': {
            'typical_resolutions': ['1024x1024', '1024x1536', '1536x1024'],
            'noise_pattern': {
                'uniformity_range': (0.5, 0.7),
                'distribution': 'uniform',
                'characteristics': ['smooth', 'text_rendering']
            },
            'color_signature': {
                'saturation_range': (105, 155),
                'contrast_range': (45, 75),
                'characteristic': 'balanced'
            },
            'ela_threshold': (10, 30),
            'metadata_patterns': {
                'missing_exif': True,
                'software_signatures': []
            },
            'compression_artifacts': 'minimal',
            'key_indicators': [
                'Excellent text rendering',
                'Balanced aesthetics',
                'No EXIF data',
                'Clean composition'
            ]
        },
        'DeepFaceLab': {
            'typical_resolutions': ['variable'],
            'noise_pattern': {
                'uniformity_range': (0.2, 0.4),
                'distribution': 'inconsistent',
                'characteristics': ['face_region_mismatch', 'boundary_artifacts']
            },
            'color_signature': {
                'saturation_range': (80, 140),
                'contrast_range': (30, 70),
                'characteristic': 'skin_tone_inconsistency'
            },
            'ela_threshold': (30, 60),
            'metadata_patterns': {
                'missing_exif': True,
                'face_artifacts': True
            },
            'compression_artifacts': 'double_compression_likely',
            'key_indicators': [
                'Face boundary artifacts',
                'Skin tone inconsistencies',
                'High ELA at face edges',
                'Variable resolution',
                'Double compression'
            ]
        },
        'Faceswap': {
            'typical_resolutions': ['variable'],
            'noise_pattern': {
                'uniformity_range': (0.25, 0.45),
                'distribution': 'inconsistent',
                'characteristics': ['lighting_inconsistency', 'boundary_artifacts']
            },
            'color_signature': {
                'saturation_range': (90, 130),
                'contrast_range': (40, 60),
                'characteristic': 'skin_tone_mismatch'
            },
            'ela_threshold': (25, 55),
            'metadata_patterns': {
                'missing_exif': True,
                'face_artifacts': True
            },
            'compression_artifacts': 'moderate',
            'key_indicators': [
                'Face lighting inconsistencies',
                'Skin tone mismatch at boundaries',
                'ELA highlights face edges',
                'Variable resolution',
                'Possible double compression'
            ]
        }
    }

    def analyze(self, image_path: str) -> dict:
        """
        Detect AI generator source.

        This doesn't analyze the image directly - it matches the
        forensic results against known signatures.
        """
        # This method is required by BaseAnalyzer but we use match_source instead
        return {
            'score': 0,
            'details': {},
            'indicators': []
        }

    def detect_source(self, image_path: str, forensic_results: dict) -> List[Dict[str, Any]]:
        """
        Match forensic results against AI generator signatures.

        Args:
            image_path: Path to the analyzed image
            forensic_results: Results from ImageForensicsAnalyzer

        Returns:
            List of detected sources with confidence scores, sorted by confidence.
            Each source has:
                - source: Generator name
                - confidence: Match confidence (0-100)
                - indicators: List of matching indicators
                - match_details: Detailed match information
        """
        try:
            from PIL import Image

            # Get image resolution
            with Image.open(image_path) as img:
                resolution = f"{img.width}x{img.height}"

            detected_sources = []

            for generator_name, signature in self.GENERATOR_SIGNATURES.items():
                match_score = self._calculate_match_score(
                    forensic_results,
                    signature,
                    resolution
                )

                logger.info(f"Source detection: {generator_name} = {match_score}% (resolution: {resolution})")

                # Only add if there's a strong match (multiple characteristics)
                # Real photos might match 1-2 characteristics by chance
                # AI-generated content matches multiple characteristics
                if match_score > 30:  # Require higher confidence
                    indicators = self._get_matching_indicators(
                        forensic_results,
                        signature,
                        match_score
                    )

                    # Only report if multiple key indicators match
                    if len(indicators) >= 2:
                        detected_sources.append({
                            'source': generator_name,
                            'confidence': round(match_score, 2),
                            'indicators': indicators,
                            'match_details': self._get_match_details(
                                forensic_results,
                                signature
                            )
                        })

            # Sort by confidence (highest first)
            detected_sources.sort(key=lambda x: x['confidence'], reverse=True)

            # Filter out low-confidence matches (increased threshold to 30% to avoid false positives)
            # Real photos often match 1-2 AI characteristics, but AI-generated content matches multiple
            detected_sources = [
                s for s in detected_sources if s['confidence'] > 30
            ]

            # Fallback generic AI detection for suspicious images without a strong generator match
            if not detected_sources:
                metadata_result = forensic_results.get('metadata', {})
                ela_result = forensic_results.get('ela', {})
                noise_result = forensic_results.get('noise', {})
                color_result = forensic_results.get('color', {})
                compression_result = forensic_results.get('compression', {})

                suspicious_signals = 0
                if not metadata_result.get('has_exif', True):
                    suspicious_signals += 1
                if ela_result.get('score', 0) >= 35:
                    suspicious_signals += 1
                if noise_result.get('score', 0) >= 35:
                    suspicious_signals += 1
                if color_result.get('score', 0) >= 25:
                    suspicious_signals += 1
                if compression_result.get('score', 0) >= 30:
                    suspicious_signals += 1

                if suspicious_signals >= 3:
                    generic_confidence = min(
                        95,
                        30 + ela_result.get('score', 0) * 0.4 + noise_result.get('score', 0) * 0.2
                    )
                    detected_sources.append({
                        'source': 'AI-generated (unknown model)',
                        'confidence': round(generic_confidence, 2),
                        'indicators': [
                            'Missing EXIF data',
                            'Suspicious noise characteristics',
                            'Unnatural color/compression patterns'
                        ],
                        'match_details': {
                            'metadata': {
                                'has_exif': metadata_result.get('has_exif', False),
                                'consistency': metadata_result.get('consistency', 'unknown')
                            },
                            'ela': {
                                'score': ela_result.get('score', 0),
                                'mean_difference': ela_result.get('mean_difference', 0)
                            },
                            'noise': {
                                'score': noise_result.get('score', 0),
                                'uniformity': noise_result.get('noise_uniformity', 0)
                            },
                            'color': {
                                'score': color_result.get('score', 0),
                                'avg_saturation': color_result.get('avg_saturation', 0)
                            },
                            'compression': {
                                'score': compression_result.get('score', 0),
                                'double_compression': compression_result.get('double_compression', False)
                            },
                            'generic_match_score': round(generic_confidence, 2)
                        }
                    })

            return detected_sources

        except Exception as e:
            logger.error(f"Source detection failed: {str(e)}")
            return []

    def detect_video_source(self, video_path: str, forensic_results: dict) -> List[Dict[str, Any]]:
        """
        Detect AI generator source for videos.

        Args:
            video_path: Path to the analyzed video
            forensic_results: Results from VideoForensicsAnalyzer

        Returns:
            List of detected sources with confidence scores
        """
        try:
            import cv2

            # Get video properties
            cap = cv2.VideoCapture(video_path)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()

            resolution = f"{width}x{height}"
            duration = frame_count / fps if fps > 0 else 0

            # Video AI generator signatures
            video_signatures = {
                'Sora': {
                    'typical_resolutions': ['1920x1080', '1080x1920', '1080x1080'],
                    'fps_range': (24, 30),
                    'min_duration': 1,
                    'motion_pattern': 'smooth_realistic',
                    'temporal_consistency': 'high',
                    'key_indicators': [
                        'Photorealistic video generation',
                        'Smooth motion transitions',
                        'High temporal consistency',
                        'Common 16:9 or 9:16 aspect ratio',
                        'Realistic physics simulation'
                    ]
                },
                'Runway Gen-3': {
                    'typical_resolutions': ['1920x1080', '1024x1024', '768x768'],
                    'fps_range': (24, 30),
                    'min_duration': 1,
                    'motion_pattern': 'smooth_artistic',
                    'temporal_consistency': 'high',
                    'key_indicators': [
                        'High-quality video generation',
                        'Artistic style options',
                        'Smooth motion',
                        'Multiple resolution options',
                        'Good temporal consistency'
                    ]
                },
                'Pika Labs': {
                    'typical_resolutions': ['1024x1024', '1024x768', '768x1024'],
                    'fps_range': (24, 30),
                    'min_duration': 3,
                    'motion_pattern': 'animated',
                    'temporal_consistency': 'moderate',
                    'key_indicators': [
                        'Image-to-video conversion',
                        'Animation-style motion',
                        '3-second default duration',
                        'Square aspect ratio common',
                        'Moderate temporal consistency'
                    ]
                },
                'HeyGen': {
                    'typical_resolutions': ['1920x1080', '1280x720'],
                    'fps_range': (24, 30),
                    'min_duration': 0,
                    'motion_pattern': 'talking_head',
                    'temporal_consistency': 'very_high',
                    'key_indicators': [
                        'AI avatar/talking head',
                        'Lip sync generation',
                        'Professional quality',
                        'Standard video resolutions',
                        'Very high temporal consistency'
                    ]
                },
                'D-ID': {
                    'typical_resolutions': ['1920x1080', '1280x720', '1080x1080'],
                    'fps_range': (25, 30),
                    'min_duration': 0,
                    'motion_pattern': 'talking_head',
                    'temporal_consistency': 'high',
                    'key_indicators': [
                        'AI talking head generation',
                        'Photo animation',
                        'Lip sync from audio',
                        'Multiple aspect ratios',
                        'High facial consistency'
                    ]
                },
                'DeepVideo Labs': {
                    'typical_resolutions': ['1920x1080', '1280x720'],
                    'fps_range': (24, 30),
                    'min_duration': 2,
                    'motion_pattern': 'face_manipulation',
                    'temporal_consistency': 'inconsistent',
                    'key_indicators': [
                        'Face manipulation in video',
                        'Deepfake characteristics',
                        'Temporal inconsistencies at face boundaries',
                        'Standard resolutions',
                        'Possible face artifacts'
                    ]
                }
            }

            detected_sources = []
            temporal_consistency = forensic_results.get('temporal_consistency', {})
            face_tracking = forensic_results.get('face_tracking', {})

            for generator_name, signature in video_signatures.items():
                match_score = self._calculate_video_match_score(
                    forensic_results,
                    signature,
                    resolution,
                    fps,
                    duration
                )

                logger.info(f"Video source detection: {generator_name} = {match_score}%")

                if match_score > 30:  # Increased from 5 to 30 - avoid false positives
                    detected_sources.append({
                        'source': generator_name,
                        'confidence': round(match_score, 2),
                        'indicators': signature['key_indicators'][:3],
                        'match_details': {
                            'resolution': resolution,
                            'fps': fps,
                            'duration': duration
                        }
                    })

            detected_sources.sort(key=lambda x: x['confidence'], reverse=True)
            return detected_sources

        except Exception as e:
            logger.error(f"Video source detection failed: {str(e)}")
            return []

    def _calculate_video_match_score(
        self,
        forensic_results: dict,
        signature: dict,
        resolution: str,
        fps: int,
        duration: float
    ) -> float:
        """Calculate video AI generator match score."""
        match_score = 0
        max_score = 100

        # Check resolution (20 points)
        if resolution in signature['typical_resolutions']:
            match_score += 20

        # Check FPS (15 points)
        fps_range = signature['fps_range']
        if fps_range[0] <= fps <= fps_range[1]:
            match_score += 15

        # Check duration (10 points)
        if duration >= signature['min_duration']:
            match_score += 10

        # Check temporal consistency (30 points)
        temporal = forensic_results.get('temporal_consistency', {})
        consistency_score = temporal.get('consistency_score', 100)

        if signature['temporal_consistency'] == 'very_high' and consistency_score > 90:
            match_score += 30
        elif signature['temporal_consistency'] == 'high' and consistency_score > 80:
            match_score += 25
        elif signature['temporal_consistency'] == 'moderate' and 60 < consistency_score <= 85:
            match_score += 20
        elif signature['temporal_consistency'] == 'inconsistent' and consistency_score < 70:
            match_score += 25

        # Check face tracking for deepfakes (25 points)
        face_tracking = forensic_results.get('face_tracking', {})
        if 'face' in signature.get('motion_pattern', ''):
            if face_tracking.get('movement_anomalies', 0) > 0:
                match_score += 15  # Face manipulation detected
            if face_tracking.get('detection_rate', 0) > 0.8:
                match_score += 10  # High face detection rate

        return min(max_score, match_score)

    def detect_audio_source(self, audio_path: str, forensic_results: dict) -> List[Dict[str, Any]]:
        """
        Detect AI generator source for audio.

        Args:
            audio_path: Path to the analyzed audio
            forensic_results: Results from AudioForensicsAnalyzer

        Returns:
            List of detected sources with confidence scores
        """
        try:
            # Get audio properties
            details = forensic_results.get('details', {})
            duration = details.get('duration', 0)
            spectral_features = details.get('spectral_features', {})
            voice_characteristics = details.get('voice_characteristics', {})

            # Audio AI generator signatures
            audio_signatures = {
                'ElevenLabs': {
                    'typical_duration_range': (0.5, 300),
                    'quality_indicators': ['high_quality', 'low_noise'],
                    'spectral_pattern': 'synthetic_but_realistic',
                    'voice_pattern': 'consistent_pitch',
                    'key_indicators': [
                        'High-quality synthetic voice',
                        'Very consistent pitch throughout',
                        'Low background noise',
                        'Natural-sounding intonation',
                        'Minimal breath sounds'
                    ]
                },
                'Murf.ai': {
                    'typical_duration_range': (1, 600),
                    'quality_indicators': ['professional_quality', 'clear'],
                    'spectral_pattern': 'professional_synthetic',
                    'voice_pattern': 'steady_rhythm',
                    'key_indicators': [
                        'Professional voice quality',
                        'Steady speaking rhythm',
                        'Clear pronunciation',
                        'Multiple voice options',
                        'Consistent audio levels'
                    ]
                },
                'Play.ht': {
                    'typical_duration_range': (1, 600),
                    'quality_indicators': ['natural', 'clear'],
                    'spectral_pattern': 'natural_sounding',
                    'voice_pattern': 'variable_intonation',
                    'key_indicators': [
                        'Natural-sounding voice',
                        'Variable intonation patterns',
                        'Multiple language support',
                        'Professional quality',
                        'Emotional expression'
                    ]
                },
                'Resemble.ai': {
                    'typical_duration_range': (0.5, 300),
                    'quality_indicators': ['voice_clone', 'high_fidelity'],
                    'spectral_pattern': 'voice_clone',
                    'voice_pattern': 'matched_characteristics',
                    'key_indicators': [
                        'Voice cloning detected',
                        'Matched voice characteristics',
                        'High fidelity reproduction',
                        'Minimal audio artifacts',
                        'Preserved voice nuances'
                    ]
                },
                'Respeecher': {
                    'typical_duration_range': (1, 300),
                    'quality_indicators': ['voice_clone', 'emotional_preservation'],
                    'spectral_pattern': 'emotional_clone',
                    'voice_pattern': 'emotional_matching',
                    'key_indicators': [
                        'Voice cloning with emotion',
                        'Emotional characteristics preserved',
                        'High-quality synthesis',
                        'Natural speech patterns',
                        'Minimal artifacts'
                    ]
                },
                'VALL-E': {
                    'typical_duration_range': (1, 300),
                    'quality_indicators': ['few_shot', 'high_quality'],
                    'spectral_pattern': 'few_shot_synthesis',
                    'voice_pattern': 'acoustic_matching',
                    'key_indicators': [
                        'Few-shot voice cloning',
                        'Acoustic detail matching',
                        'High quality with minimal training',
                        'Natural speech patterns',
                        'Minimal audio artifacts'
                    ]
                }
            }

            detected_sources = []

            for generator_name, signature in audio_signatures.items():
                match_score = self._calculate_audio_match_score(
                    forensic_results,
                    signature,
                    duration
                )

                logger.info(f"Audio source detection: {generator_name} = {match_score}%")

                if match_score > 30:  # Increased from 5 to 30 - avoid false positives
                    detected_sources.append({
                        'source': generator_name,
                        'confidence': round(match_score, 2),
                        'indicators': signature['key_indicators'][:3],
                        'match_details': {
                            'duration': duration,
                            'quality': spectral_features.get('spectral_centroid_mean', 0)
                        }
                    })

            detected_sources.sort(key=lambda x: x['confidence'], reverse=True)
            return detected_sources

        except Exception as e:
            logger.error(f"Audio source detection failed: {str(e)}")
            return []

    def _calculate_audio_match_score(
        self,
        forensic_results: dict,
        signature: dict,
        duration: float
    ) -> float:
        """Calculate audio AI generator match score."""
        match_score = 0
        max_score = 100

        # Check duration (15 points)
        duration_range = signature['typical_duration_range']
        if duration_range[0] <= duration <= duration_range[1]:
            match_score += 15

        # Check spectral features (35 points)
        spectral = forensic_results.get('spectral_features', {})
        spectral_centroid = spectral.get('spectral_centroid_mean', 0)
        zero_crossing_rate = spectral.get('zero_crossing_rate', 0)

        # Synthetic audio typically has different spectral characteristics
        if signature['spectral_pattern'] in ['synthetic_but_realistic', 'professional_synthetic']:
            if 2000 < spectral_centroid < 4000:  # Typical for synthetic voices
                match_score += 20
            if zero_crossing_rate < 0.15:  # Lower ZCR for synthetic
                match_score += 15

        # Check voice characteristics (35 points)
        voice = forensic_results.get('voice_characteristics', {})
        pitch_std = voice.get('pitch_std', 0)

        if signature['voice_pattern'] == 'consistent_pitch':
            # AI voices have very consistent pitch (low standard deviation)
            if pitch_std < 50:
                match_score += 35
            elif pitch_std < 80:
                match_score += 20

        elif signature['voice_pattern'] in ['matched_characteristics', 'emotional_matching', 'acoustic_matching']:
            # Voice cloning - check for specific patterns
            if pitch_std < 100:  # More variation than pure synthetic but still controlled
                match_score += 25
            if voice.get('pitch_range', 0) < 300:  # Controlled pitch range
                match_score += 10

        # Quality indicators (15 points)
        quality_indicators = signature.get('quality_indicators', [])
        if 'high_quality' in quality_indicators:
            if spectral.get('spectral_contrast_mean', 0) > 20:
                match_score += 15

        return min(max_score, match_score)

    def _calculate_match_score(
        self,
        forensic_results: dict,
        signature: dict,
        resolution: str
    ) -> float:
        """
        Calculate how well forensic results match a generator signature.

        Returns confidence score 0-100.
        """
        match_score = 0
        max_score = 100

        # Check resolution (15 points)
        if resolution in signature['typical_resolutions']:
            match_score += 15
        else:
            # Partial match for similar resolutions (within 200 pixels)
            try:
                width, height = map(int, resolution.split('x'))
                for sig_res in signature['typical_resolutions']:
                    sig_width, sig_height = map(int, sig_res.split('x'))
                    if abs(width - sig_width) <= 200 and abs(height - sig_height) <= 200:
                        match_score += 8  # Partial match
                        break
            except:
                pass

        # Check noise pattern (25 points) - STRICTER TO AVOID FALSE POSITIVES
        noise_result = forensic_results.get('noise', {})
        noise_uniformity = noise_result.get('noise_uniformity', 0)
        noise_range = signature['noise_pattern']['uniformity_range']
        if noise_range[0] <= noise_uniformity <= noise_range[1]:
            match_score += 25
        elif abs(noise_uniformity - noise_range[0]) < 0.1:  # Reduced from 0.2 - stricter
            match_score += 8  # Reduced from 15 - less partial match

        # Check color signature (25 points) - STRICTER TO AVOID FALSE POSITIVES
        color_result = forensic_results.get('color', {})
        avg_saturation = color_result.get('avg_saturation', 0)
        saturation_range = signature['color_signature']['saturation_range']
        if saturation_range[0] <= avg_saturation <= saturation_range[1]:
            match_score += 25
        elif abs(avg_saturation - saturation_range[0]) < 20:  # Reduced from 40 - stricter
            match_score += 8  # Reduced from 15 - less partial match

        # Check ELA threshold (20 points) - MORE LENIENT FOR AI
        ela_result = forensic_results.get('ela', {})
        mean_diff = ela_result.get('mean_difference', 0)
        ela_score = ela_result.get('score', 0)

        # Use ELA score (0-100) instead of mean_difference for better matching
        # Signatures use score-based thresholds, not raw pixel values
        ela_range = signature['ela_threshold']

        # Map ELA score to signature ranges
        # Score 0-20: low manipulation, 20-50: medium, 50+: high
        normalized_ela_value = ela_score
        if ela_range[0] <= normalized_ela_value <= ela_range[1]:
            match_score += 20
        elif normalized_ela_value > ela_range[0] * 0.5:
            match_score += 10  # Partial match

        # Check metadata (15 points) - STRICTER TO AVOID FALSE POSITIVES
        metadata_result = forensic_results.get('metadata', {})
        has_exif = metadata_result.get('has_exif', False)
        software_detected = metadata_result.get('software_detected', '')

        # Only give points for missing EXIF if it's a strong AI indicator
        # Don't penalize real photos that happen to have missing EXIF
        if signature['metadata_patterns'].get('missing_exif') and not has_exif:
            # Check if this is likely AI: common AI resolutions + missing EXIF
            ai_resolutions = ['1024x1024', '512x512', '768x768']
            if resolution in ai_resolutions:
                match_score += 15  # Only add points for common AI resolutions
            # Otherwise, no points - missing EXIF alone is not enough
        elif not signature['metadata_patterns'].get('missing_exif') and has_exif:
            match_score += 15

        # NO BONUS POINTS - removed to avoid false positives on real photos

        return min(max_score, match_score)

    def _get_matching_indicators(
        self,
        forensic_results: dict,
        signature: dict,
        match_score: float
    ) -> List[str]:
        """
        Get list of indicators that matched for this source.
        """
        indicators = []

        # Always add key indicators if score is high
        if match_score > 50:
            indicators.extend(signature['key_indicators'][:2])

        # Add specific match indicators
        noise_result = forensic_results.get('noise', {})
        noise_uniformity = noise_result.get('noise_uniformity', 0)
        if signature['noise_pattern']['uniformity_range'][0] <= noise_uniformity <= signature['noise_pattern']['uniformity_range'][1]:
            indicators.append(f"Noise pattern matches {signature['noise_pattern']['distribution']}")

        color_result = forensic_results.get('color', {})
        color_findings = color_result.get('findings', [])
        if color_findings:
            indicators.extend(color_findings[:2])

        ela_result = forensic_results.get('ela', {})
        ela_findings = ela_result.get('findings', [])
        if ela_findings and match_score > 40:
            indicators.extend(ela_findings[:1])

        return indicators[:5]  # Limit to top 5 indicators

    def _get_match_details(
        self,
        forensic_results: dict,
        signature: dict
    ) -> Dict[str, Any]:
        """
        Get detailed match information for debugging/transparency.
        """
        noise_result = forensic_results.get('noise', {})
        color_result = forensic_results.get('color', {})
        ela_result = forensic_results.get('ela', {})
        metadata_result = forensic_results.get('metadata', {})

        return {
            'noise_uniformity_match': {
                'expected': list(signature['noise_pattern']['uniformity_range']),
                'actual': float(noise_result.get('noise_uniformity', 0)),
                'matched': bool(signature['noise_pattern']['uniformity_range'][0] <=
                         noise_result.get('noise_uniformity', 0) <=
                         signature['noise_pattern']['uniformity_range'][1])
            },
            'color_saturation_match': {
                'expected': list(signature['color_signature']['saturation_range']),
                'actual': float(color_result.get('avg_saturation', 0)),
                'matched': bool(signature['color_signature']['saturation_range'][0] <=
                         color_result.get('avg_saturation', 0) <=
                         signature['color_signature']['saturation_range'][1])
            },
            'ela_match': {
                'expected': list(signature['ela_threshold']),
                'actual': float(ela_result.get('mean_difference', 0)),
                'matched': bool(signature['ela_threshold'][0] <=
                         ela_result.get('mean_difference', 0) <=
                         signature['ela_threshold'][1])
            },
            'metadata_match': {
                'expected_exif': bool(not signature['metadata_patterns'].get('missing_exif')),
                'actual_has_exif': bool(metadata_result.get('has_exif', False)),
                'matched': bool((not signature['metadata_patterns'].get('missing_exif')) ==
                         metadata_result.get('has_exif', False))
            }
        }

    def get_primary_source(
        self,
        detected_sources: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Get the primary (most likely) source from detected sources.

        Returns None if no sources detected.
        """
        if not detected_sources:
            return None

        return detected_sources[0]
