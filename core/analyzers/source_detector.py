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
            'typical_resolutions': ['1024x1024', '2048x2048', '1024x1792', '1792x1024', '1024x1536', '1536x1024'],
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
            'typical_resolutions': ['1024x1024', '1024x1536', '1792x1024', '1024x1792', '1536x1024'],
            'noise_pattern': {
                'uniformity_range': (0.5, 0.75),
                'distribution': 'relatively_uniform',
                'characteristics': ['smooth', 'low_texture_detail']
            },
            'color_signature': {
                'saturation_range': (90, 160),
                'contrast_range': (35, 75),
                'characteristic': 'vivid_colors'
            },
            'ela_threshold': (8, 28),
            'metadata_patterns': {
                'missing_exif': True,
                'watermark_possible': True
            },
            'compression_artifacts': 'minimal',
            'key_indicators': [
                'Balanced vivid colors',
                'Relatively smooth surfaces',
                'Common resolutions: 1024x1024, 1024x1536, 1792x1024',
                'Possible watermark',
                'No EXIF data',
                'Portrait or square aspect ratio'
            ]
        },
        'ChatGPT / DALL-E Portrait': {
            'typical_resolutions': ['1024x1536', '1536x1024', '1024x1024', '1792x1024', '1024x1792'],
            'noise_pattern': {
                'uniformity_range': (0.55, 0.85),
                'distribution': 'very_uniform',
                'characteristics': ['extremely_smooth', 'studio_portrait_quality']
            },
            'color_signature': {
                'saturation_range': (80, 140),
                'contrast_range': (30, 65),
                'characteristic': 'clean_portrait'
            },
            'ela_threshold': (5, 25),
            'metadata_patterns': {
                'missing_exif': True,
                'software_signatures': []
            },
            'compression_artifacts': 'minimal',
            'key_indicators': [
                'Studio-style portrait with clean background',
                'Extremely smooth skin texture',
                'No EXIF data',
                'Portrait aspect ratio common',
                'Professional headshot appearance',
                'Uniform or gradient background'
            ]
        },
        'Generic AI Portrait': {
            'typical_resolutions': ['512x512', '768x768', '1024x1024', '1024x1536', '1536x1024', '1024x1792', '1792x1024', '2048x2048'],
            'noise_pattern': {
                'uniformity_range': (0.5, 0.9),
                'distribution': 'uniform',
                'characteristics': ['smooth', 'low_texture', 'studio_quality']
            },
            'color_signature': {
                'saturation_range': (70, 160),
                'contrast_range': (25, 80),
                'characteristic': 'clean_digital'
            },
            'ela_threshold': (5, 30),
            'metadata_patterns': {
                'missing_exif': True,
                'software_signatures': []
            },
            'compression_artifacts': 'minimal',
            'key_indicators': [
                'AI-generated portrait characteristics',
                'Smooth or uniform background',
                'Missing camera EXIF data',
                'Perfect or near-perfect facial features',
                'Digital rendering artifacts'
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

                # Add matches with reasonable confidence
                # Real photos might match 1-2 characteristics by chance
                # AI-generated content matches multiple characteristics
                if match_score > 20:  # Lowered from 30 to catch more AI content
                    indicators = self._get_matching_indicators(
                        forensic_results,
                        signature,
                        match_score
                    )

                    # Only report if key indicators match
                    if len(indicators) >= 1:
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

            # Filter out very low-confidence matches
            # Real photos often match 1-2 AI characteristics, but AI-generated content matches multiple
            detected_sources = [
                s for s in detected_sources if s['confidence'] > 20
            ]

            # Fallback generic AI detection for suspicious images without a strong generator match
            if not detected_sources:
                metadata_result = forensic_results.get('metadata', {})
                ela_result = forensic_results.get('ela', {})
                noise_result = forensic_results.get('noise', {})
                color_result = forensic_results.get('color', {})
                compression_result = forensic_results.get('compression', {})
                ai_artifacts = forensic_results.get('ai_artifacts', {})

                suspicious_signals = 0
                if not metadata_result.get('has_exif', True):
                    suspicious_signals += 1
                if ela_result.get('score', 0) >= 25:
                    suspicious_signals += 1
                if noise_result.get('score', 0) >= 25:
                    suspicious_signals += 1
                if color_result.get('score', 0) >= 20:
                    suspicious_signals += 1
                if compression_result.get('score', 0) >= 20:
                    suspicious_signals += 1
                if ai_artifacts.get('portrait_score', 0) >= 40:
                    suspicious_signals += 2  # Strong signal
                if ai_artifacts.get('background_uniformity', 0) >= 0.85:
                    suspicious_signals += 1

                if suspicious_signals >= 2:  # Lowered from 3
                    base_confidence = 25
                    if ai_artifacts.get('portrait_score', 0) >= 40:
                        base_confidence += 25
                    if ai_artifacts.get('background_uniformity', 0) >= 0.85:
                        base_confidence += 15
                    generic_confidence = min(
                        90,
                        base_confidence + ela_result.get('score', 0) * 0.3 + noise_result.get('score', 0) * 0.2
                    )
                    indicators = ['Missing EXIF data']
                    if ai_artifacts.get('portrait_score', 0) >= 40:
                        indicators.append('AI portrait characteristics detected')
                    if ai_artifacts.get('background_uniformity', 0) >= 0.85:
                        indicators.append('Unnaturally uniform background')
                    if len(indicators) < 2:
                        indicators.append('Suspicious noise/color/compression patterns')

                    detected_sources.append({
                        'source': 'AI-generated (unknown model)',
                        'confidence': round(generic_confidence, 2),
                        'indicators': indicators,
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
                            'ai_artifacts': {
                                'portrait_score': ai_artifacts.get('portrait_score', 0),
                                'background_uniformity': ai_artifacts.get('background_uniformity', 0)
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

                if match_score > 55:  # Tightened — generic 30fps clips were matching at ~50
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

        # AI generators show *unnaturally* perfect consistency. Real handheld
        # video routinely sits at 88-94%, so the previous thresholds (>90, >80)
        # flagged virtually every uploaded clip as AI.
        if signature['temporal_consistency'] == 'very_high' and consistency_score > 97:
            match_score += 30
        elif signature['temporal_consistency'] == 'high' and consistency_score > 94:
            match_score += 25
        elif signature['temporal_consistency'] == 'moderate' and 70 < consistency_score <= 88:
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

    # Common AI generator output dimensions
    AI_DIMENSIONS = {256, 512, 768, 1024, 1536, 1792, 2048}

    def _is_ai_resolution(self, resolution: str) -> bool:
        """Check if resolution dimensions are standard AI generator outputs."""
        try:
            w, h = map(int, resolution.split('x'))
            return w in self.AI_DIMENSIONS or h in self.AI_DIMENSIONS
        except:
            return False

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

        # RESOLUTION SANITY CHECK
        # If resolution is NOT a known AI dimension, penalize heavily
        # Real phone photos often have arbitrary resolutions (e.g., 468x1040)
        is_known_ai_res = resolution in signature['typical_resolutions']
        is_ai_dim = self._is_ai_resolution(resolution)

        if is_known_ai_res:
            match_score += 20  # Exact match - strong signal
        elif is_ai_dim:
            # Dimension is a known AI size but not exact resolution
            match_score += 8   # Weak partial match
        else:
            # Resolution like 468x1040 is NOT from an AI generator
            # Apply heavy penalty - real photos have arbitrary resolutions
            match_score -= 15

        # Check noise pattern (20 points)
        noise_result = forensic_results.get('noise', {})
        noise_uniformity = noise_result.get('noise_uniformity', 0)
        noise_range = signature['noise_pattern']['uniformity_range']
        if noise_range[0] <= noise_uniformity <= noise_range[1]:
            match_score += 20
        elif abs(noise_uniformity - noise_range[0]) < 0.15:
            match_score += 6

        # Check color signature (20 points)
        color_result = forensic_results.get('color', {})
        avg_saturation = color_result.get('avg_saturation', 0)
        saturation_range = signature['color_signature']['saturation_range']
        if saturation_range[0] <= avg_saturation <= saturation_range[1]:
            match_score += 20
        elif abs(avg_saturation - saturation_range[0]) < 30:
            match_score += 6

        # Check ELA threshold (15 points)
        ela_result = forensic_results.get('ela', {})
        ela_score = ela_result.get('score', 0)
        ela_range = signature['ela_threshold']
        if ela_range[0] <= ela_score <= ela_range[1]:
            match_score += 15
        elif ela_score > ela_range[0] * 0.5:
            match_score += 5

        # Check metadata (10 points) - missing EXIF alone is weak evidence
        metadata_result = forensic_results.get('metadata', {})
        has_exif = metadata_result.get('has_exif', False)

        if signature['metadata_patterns'].get('missing_exif') and not has_exif:
            # Only strong if combined with known AI resolution
            if is_known_ai_res:
                match_score += 10
            elif is_ai_dim:
                match_score += 3
            else:
                match_score += 1  # Missing EXIF alone is very weak
        elif not signature['metadata_patterns'].get('missing_exif') and has_exif:
            match_score += 10

        # SPECTRAL FEATURE BONUS
        # If spectral analysis strongly indicates AI, boost match score
        spectral = forensic_results.get('spectral', {})
        spectral_score = spectral.get('score', 0)
        if spectral_score > 40:
            match_score += 10
        elif spectral_score > 20:
            match_score += 5

        return max(0, min(max_score, match_score))

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
