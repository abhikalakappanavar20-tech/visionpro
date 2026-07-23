"""
Audio Forensics Analyzer

Analyzes audio files for deepfake detection using:
- Spectral analysis (MFCC, spectral contrast)
- Voice characteristic patterns
- Background noise analysis
- Silence pattern detection
"""

import os
import logging
from typing import Dict, Any, List
import numpy as np

try:
    import librosa
    import soundfile as sf
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    import imageio_ffmpeg
    FFMPEG_AVAILABLE = True
except ImportError:
    FFMPEG_AVAILABLE = False

from .base_analyzer import BaseAnalyzer, AnalyzerError

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


class AudioForensicsAnalyzer(BaseAnalyzer):
    """
    Audio forensics analyzer for deepfake and synthetic voice detection.

    Detects AI-generated voices, voice clones, and audio manipulation.
    """

    def __init__(self):
        """Initialize audio analyzer."""
        super().__init__()
        self.name = "AudioForensicsAnalyzer"
        self.version = "1.1.0"
        self._converted_path = None  # Track temp converted file

    def _convert_with_ffmpeg(self, audio_path: str) -> str:
        """
        Convert audio file to WAV using ffmpeg for librosa compatibility.

        Args:
            audio_path: Original audio file path

        Returns:
            Path to converted WAV file (caller must clean up)

        Raises:
            AnalyzerError: If conversion fails
        """
        if not FFMPEG_AVAILABLE:
            raise AnalyzerError("FFmpeg not available. Cannot convert audio format.")

        import tempfile
        import subprocess

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        temp_wav = tempfile.mktemp(suffix='.wav')

        try:
            # Convert to 16-bit PCM WAV at 22050Hz (librosa-friendly)
            cmd = [
                ffmpeg_exe,
                '-y',  # Overwrite output
                '-i', audio_path,
                '-ar', '22050',
                '-ac', '1',
                '-acodec', 'pcm_s16le',
                temp_wav
            ]
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60
            )
            if result.returncode != 0:
                stderr = result.stderr.decode('utf-8', errors='ignore')[:200]
                raise AnalyzerError(f"FFmpeg conversion failed: {stderr}")

            if not os.path.exists(temp_wav) or os.path.getsize(temp_wav) == 0:
                raise AnalyzerError("FFmpeg produced empty output file")

            logger.info(f"Converted audio to WAV: {temp_wav}")
            return temp_wav

        except Exception as e:
            if os.path.exists(temp_wav):
                os.remove(temp_wav)
            raise AnalyzerError(f"Audio conversion failed: {str(e)}")

    def _load_audio(self, audio_path: str):
        """
        Load audio with automatic format conversion fallback.

        Args:
            audio_path: Path to audio file

        Returns:
            tuple: (audio_samples, sample_rate, is_converted)
        """
        # Try direct librosa load first
        try:
            y, sr = librosa.load(audio_path, sr=None)
            return y, sr, False
        except Exception as direct_error:
            logger.warning(f"Direct librosa load failed: {direct_error}")

        # Fallback: convert with ffmpeg then load
        if FFMPEG_AVAILABLE:
            logger.info("Attempting ffmpeg conversion for unsupported format")
            converted_path = self._convert_with_ffmpeg(audio_path)
            try:
                y, sr = librosa.load(converted_path, sr=None)
                self._converted_path = converted_path
                return y, sr, True
            except Exception as conv_error:
                os.remove(converted_path)
                self._converted_path = None
                raise AnalyzerError(f"Failed to load even after conversion: {conv_error}")
        else:
            raise AnalyzerError(f"Cannot load audio format and ffmpeg not available: {direct_error}")

    def _cleanup_converted(self):
        """Remove temporary converted file if exists."""
        if self._converted_path and os.path.exists(self._converted_path):
            try:
                os.remove(self._converted_path)
                logger.info(f"Cleaned up converted file: {self._converted_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup converted file: {e}")
            self._converted_path = None

    def _validate_audio(self, audio_path: str) -> None:
        """
        Validate audio file.

        Args:
            audio_path: Path to audio file

        Raises:
            AnalyzerError: If audio file is invalid
        """
        if not LIBROSA_AVAILABLE:
            raise AnalyzerError("Librosa not available. Cannot analyze audio.")

        if not os.path.exists(audio_path):
            raise AnalyzerError(f"Audio file not found: {audio_path}")

        # Check file size (audio files should be reasonable size)
        file_size = os.path.getsize(audio_path)
        if file_size == 0:
            raise AnalyzerError("Audio file is empty")
        if file_size > 500 * 1024 * 1024:  # 500MB limit
            logger.warning(f"Audio file very large: {file_size / 1024 / 1024:.1f}MB - may take longer to analyze")

        # Try to load small portion of audio to validate format
        try:
            # Load first 30 seconds for validation
            y, sr = librosa.load(audio_path, sr=None, duration=30.0)
            if len(y) == 0:
                raise AnalyzerError("Could not extract audio samples")
            logger.info(f"Audio validation passed: {len(y)} samples at {sr}Hz")
        except Exception as e:
            # If direct load fails, try ffmpeg conversion for validation
            if FFMPEG_AVAILABLE:
                try:
                    converted = self._convert_with_ffmpeg(audio_path)
                    y, sr = librosa.load(converted, sr=None, duration=30.0)
                    os.remove(converted)
                    if len(y) == 0:
                        raise AnalyzerError("Could not extract audio samples after conversion")
                    logger.info(f"Audio validation passed after conversion: {len(y)} samples at {sr}Hz")
                except AnalyzerError:
                    raise
                except Exception as conv_err:
                    logger.error(f"Audio validation error (even after conversion): {str(conv_err)}")
                    raise AnalyzerError(f"Cannot load audio file: {str(conv_err)}")
            else:
                logger.error(f"Audio validation error: {str(e)}")
                raise AnalyzerError(f"Cannot load audio file: {str(e)}")

    def analyze(self, audio_path: str) -> Dict[str, Any]:
        """
        Analyze audio for deepfake detection.

        Args:
            audio_path: Path to audio file

        Returns:
            dict with analysis results:
                - score: Overall manipulation score (0-100)
                - details: Detailed analysis metrics
                - indicators: List of manipulation indicators
        """
        try:
            self._validate_audio(audio_path)
            logger.info(f"Starting audio forensics analysis: {audio_path}")

            # Load full audio file for analysis (with format conversion fallback)
            try:
                y, sr, was_converted = self._load_audio(audio_path)
                duration = len(y) / sr
                if was_converted:
                    logger.info(f"Audio loaded after conversion: {duration:.2f}s at {sr}Hz")
                else:
                    logger.info(f"Audio loaded: {duration:.2f}s at {sr}Hz")
            except Exception as load_error:
                logger.error(f"Cannot load audio file: {str(load_error)}")
                self._cleanup_converted()
                raise AnalyzerError(f"Failed to load audio file: {str(load_error)}")

            if len(y) == 0 or duration == 0:
                self._cleanup_converted()
                raise AnalyzerError("Audio file is empty or has no valid samples")

            try:
                # Step 1: Spectral analysis
                spectral_analysis = self._analyze_spectral_features(y, sr)

                # Step 2: Voice characteristics
                voice_analysis = self._analyze_voice_characteristics(y, sr)

                # Step 3: Background noise analysis
                noise_analysis = self._analyze_background_noise(y, sr)

                # Step 4: Silence pattern analysis
                silence_analysis = self._analyze_silence_patterns(y, sr)

                # Step 5: Calculate overall score
                overall_score = self._calculate_overall_score(
                    spectral_analysis,
                    voice_analysis,
                    noise_analysis,
                    silence_analysis
                )

                # Step 6: Compile indicators
                indicators = self._compile_indicators(
                    spectral_analysis,
                    voice_analysis,
                    noise_analysis,
                    silence_analysis,
                    overall_score
                )

                logger.info(f"Audio analysis complete: {overall_score:.2f}%")

                result = {
                    'score': overall_score,
                    'details': {
                        'duration': duration,
                        'sample_rate': sr,
                        'spectral_features': spectral_analysis,
                        'voice_characteristics': voice_analysis,
                        'background_noise': noise_analysis,
                        'silence_analysis': silence_analysis
                    },
                    'indicators': indicators
                }

                self._cleanup_converted()
                return _convert_to_native(result)

            except Exception as analysis_error:
                logger.error(f"Error during analysis steps: {str(analysis_error)}")
                self._cleanup_converted()
                # Return fallback with partial results
                return {
                    'score': 25.0,  # Neutral score for audio
                    'details': {
                        'duration': duration if 'duration' in locals() else 0.0,
                        'sample_rate': sr if 'sr' in locals() else 0,
                        'spectral_features': {},
                        'voice_characteristics': {},
                        'background_noise': {},
                        'silence_analysis': {}
                    },
                    'indicators': ['Analysis encountered partial error - used limited analysis']
                }

        except Exception as e:
            logger.error(f"Audio forensics analysis failed: {str(e)}")
            self._cleanup_converted()
            return self._fallback_analysis()

    def _analyze_spectral_features(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """
        Analyze spectral features of audio.

        AI-generated audio has different spectral characteristics than human speech.

        Args:
            y: Audio time series
            sr: Sample rate

        Returns:
            Spectral feature analysis
        """
        # Extract MFCCs (Mel-frequency cepstral coefficients)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)

        # MFCC statistics
        mfcc_mean = np.mean(mfcc, axis=1)
        mfcc_std = np.std(mfcc, axis=1)

        # Spectral contrast
        spectral_contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
        contrast_mean = np.mean(spectral_contrast)
        contrast_std = np.std(spectral_contrast)

        # Spectral centroid (brightness)
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        centroid_mean = np.mean(spectral_centroid)
        centroid_std = np.std(spectral_centroid)

        # Zero-crossing rate (voice vs non-voice)
        zcr = librosa.feature.zero_crossing_rate(y)
        zcr_mean = np.mean(zcr)

        # Calculate anomaly scores
        # Synthetic audio often has:
        # - Lower MFCC variation (too smooth)
        # - Higher spectral centroid (brighter)
        # - Different zero-crossing rate

        mfcc_anomaly = 100 - min(100, mfcc_std.mean() * 500)  # Low variation = anomaly
        centroid_anomaly = min(100, (centroid_mean - 2000) / 30)  # High centroid = anomaly
        zcr_anomaly = abs(zcr_mean - 0.1) * 200  # Deviation from typical speech

        spectral_score = (mfcc_anomaly * 0.4 + centroid_anomaly * 0.3 + zcr_anomaly * 0.3)
        spectral_score = max(0, min(100, spectral_score))

        return {
            'mfcc_mean': mfcc_mean.tolist()[:5],  # Store first 5
            'mfcc_std_mean': float(mfcc_std.mean()),
            'spectral_contrast_mean': float(contrast_mean),
            'spectral_centroid_mean': float(centroid_mean),
            'zero_crossing_rate': float(zcr_mean),
            'spectral_anomaly_score': float(spectral_score)
        }

    def _analyze_voice_characteristics(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """
        Analyze voice characteristics for synthetic patterns.

        Args:
            y: Audio time series
            sr: Sample rate

        Returns:
            Voice characteristic analysis
        """
        # Extract pitch (fundamental frequency)
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        pitch_values = []
        for t in range(pitches.shape[1]):
            index = magnitudes[:, t].argmax()
            pitch = pitches[index, t]
            if pitch > 0:
                pitch_values.append(pitch)

        # Pitch statistics
        if pitch_values:
            pitch_mean = np.mean(pitch_values)
            pitch_std = np.std(pitch_values)
            pitch_range = max(pitch_values) - min(pitch_values)
        else:
            pitch_mean = 0
            pitch_std = 0
            pitch_range = 0

        # RMS energy (loudness)
        rms = librosa.feature.rms(y=y)
        rms_mean = np.mean(rms)
        rms_std = np.std(rms)

        # Detect voice characteristics anomalies
        # Synthetic voices often have:
        # - Lower pitch variation (monotone)
        # - Unusual pitch range
        # - Inconsistent energy patterns

        pitch_variation_score = 100 - min(100, pitch_std / 5)  # Low variation = anomaly
        energy_consistency = 100 - min(100, rms_std * 100)  # Low variation = anomaly

        voice_score = (pitch_variation_score * 0.6 + energy_consistency * 0.4)

        return {
            'pitch_mean': float(pitch_mean),
            'pitch_std': float(pitch_std),
            'pitch_range': float(pitch_range),
            'rms_mean': float(rms_mean),
            'rms_std': float(rms_std),
            'voice_anomaly_score': float(voice_score)
        }

    def _analyze_background_noise(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """
        Analyze background noise patterns.

        AI-generated audio often has unnatural noise characteristics.

        Args:
            y: Audio time series
            sr: Sample rate

        Returns:
            Background noise analysis
        """
        # Calculate spectral flatness (measure of noise-like vs tone-like)
        spectral_flatness = librosa.feature.spectral_flatness(y=y)
        flatness_mean = np.mean(spectral_flatness)

        # Noise floor (minimum energy in frequency bands)
        D = librosa.amplitude_to_db(np.abs(librosa.stft(y)), ref=np.max)
        noise_floor = np.mean(D[D > -50])  # Average of non-silent frames

        # Detect noise anomalies
        # Synthetic audio often has:
        # - Higher spectral flatness (more noise-like)
        # - Unusual noise floor

        flatness_anomaly = min(100, flatness_mean * 200)
        noise_anomaly_score = flatness_anomaly

        return {
            'spectral_flatness': float(flatness_mean),
            'noise_floor_db': float(noise_floor),
            'noise_anomaly_score': float(noise_anomaly_score)
        }

    def _analyze_silence_patterns(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """
        Analyze silence patterns in audio.

        Synthetic audio often has unnatural silence distribution.

        Args:
            y: Audio time series
            sr: Sample rate

        Returns:
            Silence pattern analysis
        """
        # Detect non-silent frames
        intervals = librosa.effects.split(y, top_db=30)

        # Calculate total silence duration
        total_duration = len(y) / sr
        voice_duration = sum((end - start) / sr for start, end in intervals)
        silence_duration = total_duration - voice_duration
        silence_ratio = silence_duration / total_duration if total_duration > 0 else 0

        # Count silence segments
        num_silence_segments = len(intervals) - 1

        # Average silence length
        if num_silence_segments > 0:
            avg_silence_length = silence_duration / num_silence_segments
        else:
            avg_silence_length = 0

        # Detect silence anomalies
        # Natural speech has:
        # - 10-30% silence ratio
        # - Varied silence lengths
        # Synthetic audio often has:
        # - Too little silence (< 10%)
        # - Too uniform silence lengths

        silence_ratio_anomaly = 0
        if silence_ratio < 0.1:
            silence_ratio_anomaly = 50  # Too little silence
        elif silence_ratio > 0.4:
            silence_ratio_anomaly = 30  # Too much silence

        silence_score = silence_ratio_anomaly

        return {
            'silence_ratio': float(silence_ratio),
            'num_silence_segments': int(num_silence_segments),
            'avg_silence_length': float(avg_silence_length),
            'silence_anomaly_score': float(silence_score)
        }

    def _calculate_overall_score(
        self,
        spectral_analysis: Dict[str, Any],
        voice_analysis: Dict[str, Any],
        noise_analysis: Dict[str, Any],
        silence_analysis: Dict[str, Any]
    ) -> float:
        """
        Calculate overall manipulation score from all analyses.

        Args:
            spectral_analysis: Spectral feature results
            voice_analysis: Voice characteristic results
            noise_analysis: Background noise results
            silence_analysis: Silence pattern results

        Returns:
            Overall score (0-100)
        """
        # Weighted combination:
        # Spectral features: 40%
        # Voice characteristics: 30%
        # Background noise: 20%
        # Silence patterns: 10%

        spectral_score = spectral_analysis['spectral_anomaly_score']
        voice_score = voice_analysis['voice_anomaly_score']
        noise_score = noise_analysis['noise_anomaly_score']
        silence_score = silence_analysis['silence_anomaly_score']

        overall = (
            spectral_score * 0.40 +
            voice_score * 0.30 +
            noise_score * 0.20 +
            silence_score * 0.10
        )

        return round(overall, 2)

    def _compile_indicators(
        self,
        spectral_analysis: Dict[str, Any],
        voice_analysis: Dict[str, Any],
        noise_analysis: Dict[str, Any],
        silence_analysis: Dict[str, Any],
        overall_score: float
    ) -> List[str]:
        """
        Compile list of manipulation indicators.

        Args:
            spectral_analysis: Spectral feature results
            voice_analysis: Voice characteristic results
            noise_analysis: Background noise results
            silence_analysis: Silence pattern results
            overall_score: Overall score

        Returns:
            List of indicator strings
        """
        indicators = []

        # Spectral indicators
        if spectral_analysis['spectral_anomaly_score'] > 60:
            indicators.append("Unusual spectral patterns detected")
        if spectral_analysis['zero_crossing_rate'] < 0.05:
            indicators.append("Atypical voice characteristics")
        if spectral_analysis['mfcc_std_mean'] < 5:
            indicators.append("Overly smooth audio (possible AI generation)")

        # Voice indicators
        if voice_analysis['pitch_std'] < 10:
            indicators.append("Low pitch variation (monotone pattern)")
        if voice_analysis['rms_std'] < 0.01:
            indicators.append("Unusual energy consistency")

        # Noise indicators
        if noise_analysis['spectral_flatness'] > 0.3:
            indicators.append("High noise-like characteristics")
        if noise_analysis['noise_floor_db'] < -40:
            indicators.append("Abnormal noise floor")

        # Silence indicators
        if silence_analysis['silence_ratio'] < 0.1:
            indicators.append("Unusually low silence ratio")
        if silence_analysis['silence_ratio'] > 0.4:
            indicators.append("Excessive silence detected")

        # Overall indicators
        if overall_score > 70:
            indicators.append("High probability of synthetic/AI-generated audio")
        elif overall_score < 30:
            indicators.append("Characteristics consistent with natural speech")

        return indicators

    def _fallback_analysis(self) -> Dict[str, Any]:
        """
        Fallback analysis when audio processing fails.

        Returns:
            Neutral/unknown analysis result with all required keys
        """
        return {
            'score': 50.0,
            'details': {
                'duration': 0.0,
                'sample_rate': 44100,
                'spectral_features': {
                    'mfcc_mean': [0.0] * 5,
                    'mfcc_std_mean': 0.0,
                    'spectral_contrast_mean': 0.0,
                    'spectral_centroid_mean': 0.0,
                    'zero_crossing_rate': 0.0,
                    'spectral_anomaly_score': 0.0
                },
                'voice_characteristics': {
                    'pitch_mean': 0.0,
                    'pitch_std': 0.0,
                    'pitch_range': 0.0,
                    'rms_mean': 0.0,
                    'rms_std': 0.0,
                    'voice_anomaly_score': 0.0
                },
                'background_noise': {
                    'spectral_flatness': 0.0,
                    'noise_floor_db': -60.0,
                    'noise_anomaly_score': 0.0
                },
                'silence_analysis': {
                    'silence_ratio': 0.0,
                    'num_silence_segments': 0,
                    'avg_silence_length': 0.0,
                    'silence_anomaly_score': 0.0
                }
            },
            'indicators': ['Audio analysis not available - using fallback']
        }
