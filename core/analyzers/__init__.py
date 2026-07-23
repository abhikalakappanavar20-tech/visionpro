"""
Forensic Analysis Services for VeriVision

This module contains real image forensics analysis services:
- BaseAnalyzer: Abstract base class for all analyzers
- ImageForensicsAnalyzer: ELA, noise, metadata, compression, color analysis
- VideoForensicsAnalyzer: Frame extraction, temporal analysis, motion detection
- AudioForensicsAnalyzer: Spectral analysis, voice characteristics
- SourceDetector: AI generator signature detection
- ForensicPipeline: Orchestrates all analyzers
- MLModelAdapter: Machine learning model integration
- ImageAIDetector: Pre-trained ResNet-18 deepfake detection (Hugging Face)
- VideoAIDetector: Frame-by-frame + temporal deepfake detection
- AudioAIDetector: Wav2Vec2 synthetic speech detection (Hugging Face)
"""

from .base_analyzer import BaseAnalyzer
from .image_forensics import ImageForensicsAnalyzer
from .video_forensics import VideoForensicsAnalyzer
from .audio_forensics import AudioForensicsAnalyzer
from .source_detector import SourceDetector
from .forensic_pipeline import ForensicPipeline
from .ml_adapter import MLModelAdapter, EnsembleAnalyzer
from .spectral_analyzer import SpectralAnalyzer
from .ai_deepfake_detector import ImageAIDetector, VideoAIDetector, AudioAIDetector

__all__ = [
    'BaseAnalyzer',
    'ImageForensicsAnalyzer',
    'VideoForensicsAnalyzer',
    'AudioForensicsAnalyzer',
    'SourceDetector',
    'ForensicPipeline',
    'MLModelAdapter',
    'EnsembleAnalyzer',
    'SpectralAnalyzer',
    'ImageAIDetector',
    'VideoAIDetector',
    'AudioAIDetector',
]
