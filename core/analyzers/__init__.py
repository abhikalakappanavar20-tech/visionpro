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
"""

from .base_analyzer import BaseAnalyzer
from .image_forensics import ImageForensicsAnalyzer
from .video_forensics import VideoForensicsAnalyzer
from .audio_forensics import AudioForensicsAnalyzer
from .source_detector import SourceDetector
from .forensic_pipeline import ForensicPipeline
from .ml_adapter import MLModelAdapter, EnsembleAnalyzer

__all__ = [
    'BaseAnalyzer',
    'ImageForensicsAnalyzer',
    'VideoForensicsAnalyzer',
    'AudioForensicsAnalyzer',
    'SourceDetector',
    'ForensicPipeline',
    'MLModelAdapter',
    'EnsembleAnalyzer',
]
