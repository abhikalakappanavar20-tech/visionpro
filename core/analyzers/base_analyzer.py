"""
Base Analyzer - Abstract class for all forensic analyzers

All analyzers must inherit from BaseAnalyzer and implement the analyze() method.
This provides a consistent interface for the forensic pipeline.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BaseAnalyzer(ABC):
    """
    Abstract base class for all forensic analyzers.

    Provides common functionality and enforces consistent interface
    across all analysis components.
    """

    def __init__(self):
        self.name = self.__class__.__name__
        self.version = "1.0.0"

    @abstractmethod
    def analyze(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze an image and return forensic results.

        Args:
            image_path: Path to the image file to analyze

        Returns:
            Dictionary containing analysis results with at least:
                - score: float (0-100) indicating manipulation likelihood
                - details: dict with specific analysis details
                - indicators: list of manipulation indicators found

        Raises:
            FileNotFoundError: If image_path doesn't exist
            ValueError: If image file is invalid or corrupted
        """
        pass

    def _validate_image(self, image_path: str) -> None:
        """
        Validate that the image file exists and is readable.

        Args:
            image_path: Path to image file

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is invalid
        """
        from pathlib import Path

        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {image_path}")

    def _calculate_score(self, value: float, min_val: float, max_val: float) -> float:
        """
        Normalize a value to a 0-100 score.

        Args:
            value: The value to normalize
            min_val: Minimum expected value
            max_val: Maximum expected value

        Returns:
            Normalized score between 0 and 100
        """
        if max_val == min_val:
            return 50.0

        normalized = (value - min_val) / (max_val - min_val)
        return max(0.0, min(100.0, normalized * 100))

    def _log_analysis(self, result: Dict[str, Any]) -> None:
        """
        Log analysis results for debugging and monitoring.

        Args:
            result: Analysis result dictionary
        """
        logger.info(f"{self.name} analysis complete: score={result.get('score', 'N/A')}")
        if result.get('indicators'):
            logger.debug(f"Indicators found: {result['indicators']}")


class AnalyzerError(Exception):
    """Base exception for analyzer errors."""
    pass


class ImageLoadError(AnalyzerError):
    """Raised when image fails to load."""
    pass


class VideoLoadError(AnalyzerError):
    """Raised when video file fails to load."""
    pass


class AudioLoadError(AnalyzerError):
    """Raised when audio file fails to load."""
    pass


class AnalysisError(AnalyzerError):
    """Raised when analysis fails."""
    pass
