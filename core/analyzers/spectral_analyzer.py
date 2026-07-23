"""
Spectral Analyzer - AI Image Detection via Frequency Domain Analysis

Uses 2D Fourier Transform to detect AI-generated images.
Key insight: Diffusion models and GANs leave characteristic fingerprints
in the frequency domain that differ from real photographs.

This analyzer also corrects for JPEG compression artifacts which can
mimic AI high-frequency suppression.
"""

import logging
import numpy as np
from PIL import Image
import cv2
from typing import Dict, Any
import os

from .base_analyzer import BaseAnalyzer, AnalyzerError

logger = logging.getLogger(__name__)


class SpectralAnalyzer(BaseAnalyzer):
    """
    Detect AI-generated images using frequency domain analysis.

    Real photographs have natural high-frequency noise, texture, and
    a characteristic power spectrum. AI-generated images often:
    - Suppress high frequencies (over-smoothing)
    - Have anomalous spectral peaks from upsampling
    - Show grid-like artifacts in frequency domain
    """

    def __init__(self):
        super().__init__()
        self.name = "SpectralAnalyzer"
        self.version = "1.1.0"
        self.analysis_size = 512

    def analyze(self, image_path: str) -> Dict[str, Any]:
        """Perform spectral analysis on an image."""
        try:
            img = Image.open(image_path).convert('L')
            orig_w, orig_h = img.size
            img_resized = img.resize((self.analysis_size, self.analysis_size), Image.Resampling.LANCZOS)
            gray = np.array(img_resized, dtype=np.float32) / 255.0

            # Detect compression quality / estimate JPEG artifacts
            compression_estimate = self._estimate_compression_quality(gray, image_path)

            # Compute 2D FFT
            f = np.fft.fft2(gray)
            fshift = np.fft.fftshift(f)
            magnitude = np.abs(fshift)
            magnitude_log = np.log(magnitude + 1e-10)

            # Azimuthal average
            radial_profile = self._azimuthal_average(magnitude)
            radial_log = np.log(radial_profile + 1e-10)

            # Extract features
            features = self._extract_features(magnitude, magnitude_log, radial_profile, radial_log, compression_estimate)

            # Calculate AI-likelihood score (0-100)
            score = self._calculate_ai_score(features, compression_estimate)

            # Generate findings
            indicators = self._generate_findings(features, score, compression_estimate)

            return {
                'score': float(score),
                'details': {
                    'spectral_slope': float(features['slope']),
                    'high_freq_ratio': float(features['hf_ratio']),
                    'low_freq_peak': float(features['low_freq_peak']),
                    'high_freq_mean': float(features['high_freq_mean']),
                    'spectral_entropy': float(features['spectral_entropy']),
                    'mid_freq_anomaly': float(features['mid_freq_anomaly']),
                    'grid_artifact_score': float(features['grid_artifact_score']),
                    'compression_quality': float(compression_estimate['quality']),
                    'file_size_ratio': float(compression_estimate['file_size_ratio']),
                },
                'indicators': indicators
            }

        except Exception as e:
            logger.error(f"Spectral analysis failed: {str(e)}")
            return self._fallback_analysis()

    def _estimate_compression_quality(self, gray: np.ndarray, image_path: str) -> Dict[str, float]:
        """
        Estimate image compression quality to correct spectral analysis.

        Heavily compressed JPEGs suppress high frequencies, which can be
        mistaken for AI generation.

        Returns:
            dict with compression quality estimate (0-100, higher = better quality)
        """
        try:
            file_size = os.path.getsize(image_path)
            h, w = gray.shape
            pixels = h * w

            # Bytes per pixel
            bpp = file_size / pixels

            # Typical ranges:
            # Uncompressed ~3.0 bpp, High-quality JPEG ~0.5-1.5 bpp
            # Low-quality JPEG ~0.1-0.3 bpp, Thumbnail ~0.05 bpp
            if bpp > 1.0:
                quality = 85  # High quality
            elif bpp > 0.5:
                quality = 70
            elif bpp > 0.3:
                quality = 55
            elif bpp > 0.15:
                quality = 40
            else:
                quality = 25  # Very compressed

            # Also check for JPEG blocking artifacts in DCT
            block_scores = []
            for by in range(0, h - 8, 8):
                for bx in range(0, w - 8, 8):
                    block = gray[by:by+8, bx:bx+8]
                    # Measure block boundary discontinuities
                    h_diff = np.abs(block[7, :] - block[0, :]).mean()
                    v_diff = np.abs(block[:, 7] - block[:, 0]).mean()
                    block_scores.append((h_diff + v_diff) / 2)

            avg_block_diff = np.mean(block_scores) if block_scores else 0
            # High block boundary differences = heavy quantization = low quality
            if avg_block_diff > 0.08:
                quality -= 10
            elif avg_block_diff < 0.03:
                quality += 5

            # File size ratio (file size relative to uncompressed)
            uncompressed = pixels * 3  # RGB approx
            file_size_ratio = file_size / uncompressed if uncompressed > 0 else 1.0

            return {
                'quality': max(0, min(100, quality)),
                'bpp': float(bpp),
                'avg_block_diff': float(avg_block_diff),
                'file_size_ratio': float(file_size_ratio)
            }
        except Exception:
            return {'quality': 50, 'bpp': 1.0, 'avg_block_diff': 0.05, 'file_size_ratio': 0.3}

    def _azimuthal_average(self, magnitude: np.ndarray) -> np.ndarray:
        """Compute azimuthal average of 2D power spectrum."""
        h, w = magnitude.shape
        center_y, center_x = h // 2, w // 2
        y, x = np.indices((h, w))
        r = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2).astype(int)

        max_radius = min(h, w) // 2
        radial = np.zeros(max_radius)

        for radius in range(max_radius):
            mask = r == radius
            if mask.sum() > 0:
                radial[radius] = magnitude[mask].mean()

        return radial

    def _extract_features(self, magnitude: np.ndarray, magnitude_log: np.ndarray,
                          radial: np.ndarray, radial_log: np.ndarray,
                          compression: Dict[str, float]) -> Dict[str, float]:
        """Extract spectral features for AI detection."""
        n = len(radial)
        mid = n // 2

        # 1. Spectral slope (log-log linear fit on first 50% of frequencies)
        fit_n = int(n * 0.5)
        log_r = np.log(np.arange(1, fit_n + 1))
        log_p = radial_log[:fit_n]
        slope, intercept = np.polyfit(log_r, log_p, 1)

        # 2. High-frequency energy ratio
        hf_ratio = radial[mid:].sum() / (radial[:mid].sum() + 1e-10)

        # 3. Low-frequency peak
        low_freq_peak = radial[:20].max()

        # 4. High-frequency mean
        high_freq_mean = radial[mid:].mean()

        # 5. Spectral entropy
        p = radial / (radial.sum() + 1e-10)
        spectral_entropy = -np.sum(p * np.log(p + 1e-10))

        # 6. Mid-frequency anomaly
        q1, q2, q3 = n // 4, n // 2, 3 * n // 4
        expected_mid = (radial[q1] + radial[q3]) / 2
        actual_mid = radial[q2]
        mid_freq_anomaly = (expected_mid - actual_mid) / (expected_mid + 1e-10)

        # 7. Grid artifact detection
        grid_artifact_score = self._detect_grid_artifacts(magnitude)

        # 8. High-frequency variance (real photos have more varied HF)
        hf_variance = np.var(radial[mid:])

        return {
            'slope': float(slope),
            'intercept': float(intercept),
            'hf_ratio': float(hf_ratio),
            'low_freq_peak': float(low_freq_peak),
            'high_freq_mean': float(high_freq_mean),
            'spectral_entropy': float(spectral_entropy),
            'mid_freq_anomaly': float(mid_freq_anomaly),
            'grid_artifact_score': float(grid_artifact_score),
            'hf_variance': float(hf_variance),
        }

    def _detect_grid_artifacts(self, magnitude: np.ndarray) -> float:
        """Detect grid-like artifacts in frequency domain."""
        h, w = magnitude.shape
        cy, cx = h // 2, w // 2

        horizontal = magnitude[cy, :]
        vertical = magnitude[:, cx]

        h_left = horizontal[:cx]
        h_right = horizontal[cx + 1:]
        v_top = vertical[:cy]
        v_bottom = vertical[cy + 1:]

        def peak_score(arr):
            if len(arr) < 10:
                return 0.0
            arr_norm = arr / (arr.max() + 1e-10)
            try:
                from scipy.signal import find_peaks
                peaks, props = find_peaks(arr_norm, height=0.3, distance=5)
                if len(peaks) == 0:
                    return 0.0
                avg_height = np.mean(props['peak_heights']) if 'peak_heights' in props else 0
                return min(1.0, len(peaks) * 0.1 + avg_height * 0.3)
            except Exception:
                return 0.0

        h_score = peak_score(np.concatenate([h_left, h_right]))
        v_score = peak_score(np.concatenate([v_top, v_bottom]))

        return (h_score + v_score) / 2

    def _calculate_ai_score(self, features: Dict[str, float], compression: Dict[str, float]) -> float:
        """
        Calculate AI-likelihood score from spectral features.

        Corrects for JPEG compression which suppresses high frequencies.
        """
        score = 0.0
        comp_quality = compression['quality']
        comp_factor = max(0.3, min(1.0, comp_quality / 70.0))  # 0.3 to 1.0

        slope = features['slope']
        hf_ratio = features['hf_ratio']
        low_peak = features['low_freq_peak']
        hf_variance = features['hf_variance']
        grid_score = features['grid_artifact_score']

        # SLOPE ANALYSIS (real: -0.9 to -1.3, AI: -1.45 to -1.8)
        if slope < -1.50:
            score += 20
        elif slope < -1.35:
            score += 12
        elif slope < -1.20:
            score += 5
        elif slope > -0.95:
            score -= 15  # Very shallow = very likely real

        # HIGH-FREQUENCY RATIO (corrected for compression)
        # Real: 0.03-0.08, AI: 0.01-0.03
        # For compressed images, reduce thresholds
        hf_threshold_low = 0.015 * comp_factor
        hf_threshold_mid = 0.025 * comp_factor
        hf_threshold_high = 0.045 * comp_factor

        if hf_ratio < hf_threshold_low:
            score += 18
        elif hf_ratio < hf_threshold_mid:
            score += 8
        elif hf_ratio > hf_threshold_high:
            score -= 12  # Rich HF = likely real

        # LOW-FREQUENCY PEAK (AI images often have very strong LF)
        # Normalize by image size (since we resize to 512x512)
        normalized_peak = low_peak / 10000.0
        if normalized_peak > 2.5:
            score += 15
        elif normalized_peak > 1.5:
            score += 8
        elif normalized_peak < 0.8:
            score -= 5

        # HIGH-FREQUENCY VARIANCE (real photos have more varied HF)
        if hf_variance > 500:
            score -= 8  # Varied HF = real
        elif hf_variance < 100:
            score += 5  # Uniform HF = AI-like

        # GRID ARTIFACTS (GAN-specific)
        score += grid_score * 12

        # COMPRESSION CORRECTION
        # Heavily compressed images get score reduced because
        # compression mimics AI frequency suppression
        if comp_quality < 35:
            score -= 15  # Very compressed - probably real JPEG
        elif comp_quality < 50:
            score -= 8

        # ENTROPY (real photos have more varied spectral content)
        entropy = features['spectral_entropy']
        if entropy > 5.5:
            score -= 5
        elif entropy < 3.5:
            score += 5

        return max(0.0, min(100.0, score))

    def _generate_findings(self, features: Dict[str, float], score: float, compression: Dict[str, float]) -> list:
        """Generate human-readable findings."""
        indicators = []
        comp_quality = compression['quality']

        if comp_quality < 40:
            indicators.append(f"Heavily compressed image (quality ~{comp_quality}) - spectral analysis adjusted")

        if features['slope'] < -1.50:
            indicators.append("Very steep spectral slope - strong AI suppression signature")
        elif features['slope'] < -1.35:
            indicators.append("Steep spectral slope - possible AI generation")
        elif features['slope'] > -0.95:
            indicators.append("Natural spectral slope - consistent with real photography")

        if features['hf_ratio'] < 0.015:
            indicators.append("Very low high-frequency content - strong AI indicator")
        elif features['hf_ratio'] > 0.05:
            indicators.append("Rich high-frequency detail - consistent with real photography")

        if features['grid_artifact_score'] > 0.5:
            indicators.append("Grid-like frequency artifacts - GAN generation indicator")

        if score > 50:
            indicators.append("Frequency domain analysis strongly suggests AI generation")
        elif score > 30:
            indicators.append("Frequency domain shows some AI-like characteristics")
        elif score < 15:
            indicators.append("Frequency domain consistent with natural photography")

        return indicators

    def _fallback_analysis(self) -> Dict[str, Any]:
        """Fallback when spectral analysis fails."""
        return {
            'score': 0.0,
            'details': {
                'spectral_slope': 0.0,
                'high_freq_ratio': 0.0,
                'low_freq_peak': 0.0,
                'high_freq_mean': 0.0,
                'spectral_entropy': 0.0,
                'mid_freq_anomaly': 0.0,
                'grid_artifact_score': 0.0,
                'compression_quality': 50.0,
                'file_size_ratio': 0.3,
            },
            'indicators': ['Spectral analysis failed']
        }
