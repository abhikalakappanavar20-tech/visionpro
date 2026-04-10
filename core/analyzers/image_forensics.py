"""
Image Forensics Analyzer - Real Deepfake Detection

Implements actual forensic analysis techniques:
- ELA (Error Level Analysis)
- Metadata/EXIF Analysis
- Noise Pattern Analysis
- Compression Artifact Detection
- Color Histogram Analysis
"""

import os
import numpy as np
from PIL import Image, ImageChops, ImageStat, ImageEnhance
import cv2
from pathlib import Path
import logging

from .base_analyzer import BaseAnalyzer, AnalyzerError, ImageLoadError
from .image_preprocessing import enhance_image_for_analysis, validate_image_quality, is_webcam_capture

logger = logging.getLogger(__name__)


def _convert_to_native(obj):
    """
    Convert NumPy types to native Python types for JSON serialization.

    Args:
        obj: Any object (possibly NumPy type)

    Returns:
        Native Python type equivalent
    """
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


class ImageForensicsAnalyzer(BaseAnalyzer):
    """
    Real image forensics analysis using multiple techniques.

    Each analyzer returns:
    - score: 0-100 (higher = more likely to be fake/manipulated)
    - details: dict with specific findings
    - indicators: list of manipulation indicators found
    """

    def __init__(self):
        super().__init__()
        self.name = "ImageForensicsAnalyzer"
        self.ela_quality = 95  # Quality for ELA resave

    def analyze(self, image_path: str, source: str = 'upload') -> dict:
        """
        Run complete forensic analysis on an image.

        Args:
            image_path: Path to image file
            source: Source of image ('upload', 'webcam', 'url')

        Returns:
            dict with keys:
                - score: overall manipulation likelihood (0-100)
                - details: dict of individual analysis results
                - indicators: list of detected manipulation signs
                - ela_heatmap: numpy array of ELA differences (for visualization)
                - source_detected: detected source (upload/webcam/url)
        """
        self._validate_image(image_path)

        # Detect if image is from webcam
        is_webcam = source == 'webcam' or is_webcam_capture(image_path)
        is_video_frame = source == 'video-frame'
        is_collage = self._detect_collage(image_path)
        
        logger.info(f"Image analysis: webcam={is_webcam}, video_frame={is_video_frame}, collage={is_collage}")

        # Validate image quality
        validation = validate_image_quality(image_path)
        if not validation['valid']:
            raise AnalyzerError(f"Image validation failed: {validation['errors']}")

        try:
            # Enhance image for analysis
            image, image_cv, preprocessing_metadata = enhance_image_for_analysis(
                image_path, is_webcam=is_webcam
            )

            if image is None or image_cv is None:
                raise ImageLoadError(f"Failed to load image: {image_path}")

            # Add collage detection to preprocessing metadata
            preprocessing_metadata['is_collage'] = is_collage

            # Run all analyses with webcam-aware parameters
            results = {
                'ela': self._perform_ela(image_path, is_webcam=is_webcam),
                'metadata': self._analyze_metadata(image, image_path, is_webcam=is_webcam),
                'noise': self._analyze_noise(image_cv, is_webcam=is_webcam),
                'compression': self._analyze_compression(image_cv, is_webcam=is_webcam),
                'color': self._analyze_colors(image_cv, is_webcam=is_webcam),
                'preprocessing': preprocessing_metadata,
                'validation': validation,
            }

            # Calculate overall score (with webcam/video-frame/collage adjustment)
            overall_score = self._calculate_overall_score(results, is_webcam=is_webcam, is_video_frame=is_video_frame, is_collage=is_collage)

            # Compile indicators
            indicators = self._compile_indicators(results)

            # Generate heatmap data
            heatmap_data = self._generate_heatmap_data(results['ela']['difference_image'])

            # Convert all NumPy types to native Python types
            result = {
                'score': overall_score,
                'details': results,
                'indicators': indicators,
                'ela_heatmap': heatmap_data,
                'manipulation_indicators_count': len(indicators),
                'source_detected': source,
                'is_webcam_capture': is_webcam
            }

            return _convert_to_native(result)

        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            raise AnalyzerError(f"Forensic analysis failed: {str(e)}")

    def _detect_collage(self, image_path: str) -> bool:
        """
        Detect if an image is likely a collage.

        Collages typically have:
        - Multiple distinct regions with different characteristics
        - Visible seams or borders between regions
        - Inconsistent compression artifacts
        - Grid-like patterns or multiple similar elements
        - Aspect ratio or content changes within image

        Args:
            image_path: Path to image file

        Returns:
            bool: True if likely a collage
        """
        try:
            from PIL import Image
            import numpy as np

            image = Image.open(image_path)
            image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

            height, width = image_cv.shape[:2]

            # Skip detection for very small images
            if width < 200 or height < 200:
                return False

            # Check for grid-like patterns (common in collages)
            # Divide image into 4x4 grid and check for significant differences
            grid_size = 4
            cell_width = width // grid_size
            cell_height = height // grid_size

            grid_scores = []
            for i in range(grid_size):
                for j in range(grid_size):
                    x1, y1 = j * cell_width, i * cell_height
                    x2, y2 = min((j + 1) * cell_width, width), min((i + 1) * cell_height, height)

                    cell = image_cv[y1:y2, x1:x2]

                    # Calculate variance in the cell (brightness, color)
                    gray_cell = cv2.cvtColor(cell, cv2.COLOR_BGR2GRAY)
                    brightness_var = np.var(gray_cell)

                    # Color variance
                    color_var = np.var(cell, axis=(0, 1)).mean()

                    # Edge density (seams often have high edges)
                    edges = cv2.Canny(gray_cell, 100, 200)
                    edge_density = np.sum(edges > 0) / (cell.shape[0] * cell.shape[1])

                    grid_scores.append({
                        'brightness_var': brightness_var,
                        'color_var': color_var,
                        'edge_density': edge_density
                    })

            # Check for significant variation between grid cells
            brightness_vars = [s['brightness_var'] for s in grid_scores]
            color_vars = [s['color_var'] for s in grid_scores]
            edge_densities = [s['edge_density'] for s in grid_scores]

            brightness_std = np.std(brightness_vars)
            color_std = np.std(color_vars)
            edge_std = np.std(edge_densities)

            # High standard deviation in characteristics suggests collage
            brightness_threshold = np.mean(brightness_vars) * 0.5
            color_threshold = np.mean(color_vars) * 0.5
            edge_threshold = 0.05  # 5% edge density difference

            collage_indicators = 0
            if brightness_std > brightness_threshold:
                collage_indicators += 1
            if color_std > color_threshold:
                collage_indicators += 1
            if edge_std > edge_threshold:
                collage_indicators += 1

            # Check for visible seams (high edge density in specific regions)
            # Look for horizontal/vertical lines that might be collage borders
            gray_full = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
            edges_full = cv2.Canny(gray_full, 50, 150)

            # Check horizontal lines (potential collage seams)
            horizontal_projection = np.sum(edges_full, axis=1)
            horizontal_peaks = np.where(horizontal_projection > np.mean(horizontal_projection) * 2)[0]

            # Check vertical lines
            vertical_projection = np.sum(edges_full, axis=0)
            vertical_peaks = np.where(vertical_projection > np.mean(vertical_projection) * 2)[0]

            # If we have multiple alignment lines, likely a collage
            if len(horizontal_peaks) > 2 or len(vertical_peaks) > 2:
                collage_indicators += 1

            # Enhanced detection: Check for aspect ratio changes (different source images)
            # If we see significant transitions between regions, might be collage
            # Check cross-boundary differences (where images meet in a collage)
            mid_h = height // 2
            mid_w = width // 2
            
            # Sample regions near potential seams - look for VERY distinct differences
            boundary_indicators = 0
            sample_margin = min(40, min(height, width) // 8)  # Larger sample margin for reliability
            
            # Check horizontal seam (middle of image)
            if mid_h > sample_margin:
                top_region = gray_full[max(0, mid_h-sample_margin):mid_h, :]
                bottom_region = gray_full[mid_h:min(height, mid_h+sample_margin), :]
                
                top_avg = np.mean(top_region)
                bottom_avg = np.mean(bottom_region)
                top_std = np.std(top_region)
                bottom_std = np.std(bottom_region)
                
                # Significant AND consistent brightness difference across middle
                # A collage would have distinctly different regions, not just slight variations
                if abs(top_avg - bottom_avg) > max(top_std, bottom_std) * 1.5:
                    boundary_indicators += 1
            
            # Check vertical seam (middle of image)
            if mid_w > sample_margin:
                left_region = gray_full[:, max(0, mid_w-sample_margin):mid_w]
                right_region = gray_full[:, mid_w:min(width, mid_w+sample_margin)]
                
                left_avg = np.mean(left_region)
                right_avg = np.mean(right_region)
                left_std = np.std(left_region)
                right_std = np.std(right_region)
                
                # Significant AND consistent brightness difference across middle
                if abs(left_avg - right_avg) > max(left_std, right_std) * 1.5:
                    boundary_indicators += 1
            
            if boundary_indicators > 0:
                collage_indicators += boundary_indicators

            # Final decision: require solid evidence of collage
            # Need multiple indicators: grid-based variation + seams/boundaries
            # This prevents false positives on single images with natural content variation
            return collage_indicators >= 2

        except Exception as e:
            logger.warning(f"Collage detection failed: {str(e)}")
            return False

    def _perform_ela(self, image_path: str, is_webcam: bool = False) -> dict:
        """
        Error Level Analysis - Detects manipulation through compression artifacts.

        When an image is edited and resaved, edited regions have different
        compression levels than original regions.

        Args:
            image_path: Path to image file
            is_webcam: True if image is from webcam (adjusts thresholds)

        Returns:
            dict with ELA score, difference image, and findings
        """
        try:
            # Open original image
            original = Image.open(image_path).convert('RGB')

            # Save at known quality
            temp_path = image_path + '_ela_temp.jpg'
            original.save(temp_path, quality=self.ela_quality, optimize=True)

            # Open resaved version
            resaved = Image.open(temp_path)

            # Calculate difference
            diff = ImageChops.difference(original, resaved)

            # Get statistics
            stat = ImageStat.Stat(diff)
            mean_diff = sum(stat.mean) / len(stat.mean)
            max_diff = max(stat.mean)

            # Adjust thresholds based on source
            # Balanced thresholds to catch edits without false positives on real photos
            if is_webcam:
                # Much higher threshold for webcam (webcam compression is very high)
                # Webcam captures have naturally higher ELA due to compression
                ela_min, ela_max = 15, 80  # Increased from 10,70
            else:
                # More lenient thresholds for uploaded images (smartphone photos)
                ela_min, ela_max = 5, 50  # Increased from 4,45

            # Calculate ELA score (higher = more manipulation likely)
            ela_score = self._calculate_score(mean_diff, ela_min, ela_max)

            # Find high-difference regions
            diff_array = np.array(diff)
            threshold = np.percentile(diff_array, 90)  # Increased from 88 to be more lenient
            high_diff_regions = np.sum(diff_array > threshold)

            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)

            # Determine findings
            findings = []
            if is_webcam:
                # More lenient thresholds for webcam (higher ELA is normal)
                if ela_score > 70:  # Increased from 60 - much more lenient
                    findings.append("Elevated ELA values - webcam compression or manipulation")
                if max_diff > 180:  # Increased from 140 - much more lenient
                    findings.append("High difference values - possibly edited regions")
                if high_diff_regions > 30000:  # Increased from 20000 - much more lenient
                    findings.append(f"Large area with differences ({high_diff_regions} pixels)")
            else:
                # Balanced thresholds for uploaded images
                if ela_score > 50:  # Reduced from 60 - more sensitive to manipulation
                    findings.append("ELA values detected - possible manipulation")
                if max_diff > 120:  # Reduced from 150 - more sensitive
                    findings.append("Difference values - possibly edited regions")
                if high_diff_regions > 20000:  # Reduced from 25000 - more sensitive
                    findings.append(f"Edited area detected ({high_diff_regions} pixels)")

            # If large edited area detected but low mean_diff, boost score appropriately
            if high_diff_regions > 60000 and ela_score < 25:  # Adjusted thresholds
                ela_score = 35  # Moderate boost for large edited areas
                findings.append("Significant editing detected despite low ELA")

            return {
                'score': float(ela_score),
                'mean_difference': float(mean_diff),
                'max_difference': float(max_diff),
                'high_diff_regions': int(high_diff_regions),
                'difference_image': diff,
                'findings': list(findings),
                'is_webcam_adjusted': is_webcam
            }

        except Exception as e:
            logger.error(f"ELA analysis failed: {str(e)}")
            return {
                'score': 0.0,
                'mean_difference': 0.0,
                'max_difference': 0.0,
                'high_diff_regions': 0,
                'difference_image': None,
                'findings': [f"ELA analysis failed: {str(e)}"],
                'is_webcam_adjusted': False
            }

    def _analyze_metadata(self, image: Image.Image, image_path: str, is_webcam: bool = False) -> dict:
        """
        Analyze EXIF metadata for inconsistencies.

        Real photos have complete EXIF data. AI-generated and edited
        images often have missing or inconsistent metadata.

        Args:
            image: PIL Image object
            image_path: Path to image file
            is_webcam: True if image is from webcam (missing EXIF is normal)
        """
        try:
            from PIL.ExifTags import TAGS

            # Extract EXIF data
            exif_data = {}
            metadata_consistency = 'missing'
            software_detected = None
            findings = []

            try:
                exif = image._getexif()
                if exif:
                    for tag_id, value in exif.items():
                        tag = TAGS.get(tag_id, tag_id)
                        exif_data[tag] = value

                    has_exif = len(exif_data) > 10
                    metadata_consistency = 'consistent' if has_exif else 'incomplete'

                    # Check for software signatures
                    software = exif_data.get('Software', '')
                    if software:
                        software_detected = software
                        if any(name in software.lower() for name in ['photoshop', 'gimp', 'lightroom']):
                            findings.append(f"Editing software detected: {software}")

                    # Check for camera info
                    make = exif_data.get('Make', '')
                    model = exif_data.get('Model', '')
                    if not (make or model):
                        findings.append("No camera information - possible AI-generated")

                else:
                    has_exif = False
                    if is_webcam:
                        findings.append("No EXIF data (normal for webcam captures)")
                    else:
                        findings.append("No EXIF data found - AI-generated or metadata stripped")

            except Exception as e:
                has_exif = False
                findings.append(f"EXIF extraction failed: {str(e)}")

            # Calculate metadata score
            # Balanced scoring to avoid false positives on real photos
            if is_webcam:
                if not has_exif:
                    metadata_score = 5  # Low - webcam captures normally have no EXIF
                    findings = [f.replace("(normal for webcam captures)", "").strip()
                               for f in findings if "AI-generated" not in f]
                elif software_detected and any(name in software_detected.lower() for name in ['photoshop', 'gimp']):
                    metadata_score = 50  # Still suspicious if editing software detected
                else:
                    metadata_score = 5  # Low score for webcam
            else:
                # Much more lenient scoring for non-webcam images
                if software_detected and any(name in software_detected.lower() for name in ['photoshop', 'gimp']):
                    metadata_score = 35  # Reduced from 45 - editing detected but not as suspicious
                elif not has_exif:
                    metadata_score = 5  # Dramatically reduced from 15 - missing EXIF is NORMAL for real photos
                elif has_exif and not (make or model):
                    metadata_score = 3  # Reduced from 10 - has EXIF but no camera info
                elif has_exif:
                    metadata_score = 1  # Reduced from 5 - has EXIF with camera info (very low suspicion)

            return {
                'score': float(metadata_score),
                'has_exif': bool(has_exif),
                'exif_data': dict(exif_data) if has_exif else {},
                'consistency': str(metadata_consistency),
                'software_detected': software_detected,
                'findings': list(findings),
                'is_webcam_adjusted': is_webcam
            }

        except Exception as e:
            logger.error(f"Metadata analysis failed: {str(e)}")
            return {
                'score': 5 if is_webcam else 30,  # Lower score for webcam on error
                'has_exif': False,
                'exif_data': {},
                'consistency': 'unknown',
                'software_detected': None,
                'findings': [f"Metadata analysis failed: {str(e)}"],
                'is_webcam_adjusted': is_webcam
            }

    def _analyze_noise(self, image_cv: np.ndarray, is_webcam: bool = False) -> dict:
        """
        Analyze noise patterns in the image.

        AI-generated images have non-uniform noise distributions.
        Real photos have more uniform, natural noise patterns.
        Webcam images have their own sensor noise characteristics.

        Args:
            image_cv: OpenCV image array
            is_webcam: True if image is from webcam (adjusts thresholds)
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)

            # Apply Laplacian to detect edges/noise
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            noise_std = np.std(laplacian)

            # Calculate noise uniformity across image
            h, w = gray.shape
            # Divide image into 4 quadrants and check noise variance
            quadrants = [
                gray[:h//2, :w//2],
                gray[:h//2, w//2:],
                gray[h//2:, :w//2],
                gray[h//2:, w//2:]
            ]

            quadrant_noise = [np.std(cv2.Laplacian(q, cv2.CV_64F)) for q in quadrants]
            noise_variance = max(quadrant_noise) - min(quadrant_noise)
            noise_uniformity = 1 - (noise_variance / (max(quadrant_noise) + 1))

            # Calculate noise score with webcam adjustment
            # Webcams typically have higher noise and different patterns
            if is_webcam:
                # Webcams have more noise variance naturally
                # Use more lenient thresholds
                noise_threshold_high = 0.4
                noise_threshold_med = 0.5
                min_noise_std = 8  # Webcams can be noisy
            else:
                # Normal thresholds for uploaded images
                noise_threshold_high = 0.5
                noise_threshold_med = 0.6
                min_noise_std = 10

            noise_score = self._calculate_score(1 - noise_uniformity, 0, 1)

            findings = []
            if is_webcam:
                # Webcam-specific analysis
                if noise_uniformity < noise_threshold_high:
                    findings.append("Highly non-uniform noise - may indicate processing or AI generation")
                elif noise_std < min_noise_std:
                    findings.append("Lower noise level - possibly processed or software-generated")
                else:
                    findings.append("Noise patterns consistent with webcam capture")
            else:
                # Much more lenient analysis for uploaded images
                if noise_uniformity < 0.7:  # Increased from 0.6 - much more lenient
                    findings.append("Non-uniform noise pattern detected - possible AI generation")
                if noise_std < 12:  # Increased from 10 - more lenient for low noise
                    findings.append("Low noise level - AI-generated or heavily processed")

            # Much less aggressive score adjustment for noise
            if not is_webcam:
                # Much more lenient thresholds for uploaded images
                if noise_uniformity < 0.4:  # Reduced sensitivity significantly
                    noise_score = max(noise_score, 25)  # Reduced from 40
                elif noise_uniformity < 0.5:  # Reduced sensitivity
                    noise_score = max(noise_score, 15)  # Reduced from 30
                # Otherwise, use the calculated score without boosting
            else:
                # More lenient for webcam
                if noise_uniformity < 0.3:
                    noise_score = max(noise_score, 20)  # Reduced from 35
                elif noise_uniformity < 0.4:
                    noise_score = max(noise_score, 10)  # Reduced from 20
                # Otherwise, use the calculated score without boosting

            return {
                'score': float(noise_score),
                'noise_std': float(noise_std),
                'noise_uniformity': float(noise_uniformity),
                'quadrant_noise': [float(n) for n in quadrant_noise],
                'noise_variance': float(noise_variance),
                'findings': findings,
                'is_webcam_adjusted': is_webcam
            }

        except Exception as e:
            logger.error(f"Noise analysis failed: {str(e)}")
            return {
                'score': 0.0,
                'noise_std': 0.0,
                'noise_uniformity': 0.0,
                'quadrant_noise': [],
                'noise_variance': 0.0,
                'findings': [f"Noise analysis failed: {str(e)}"],
                'is_webcam_adjusted': is_webcam
            }

    def _analyze_compression(self, image_cv: np.ndarray, is_webcam: bool = False) -> dict:
        """
        Detect compression artifacts and double compression.

        Double compression (saving an already compressed image again)
        leaves characteristic artifacts and is a sign of manipulation.

        Args:
            image_cv: OpenCV image array
            is_webcam: True if image is from webcam (webcam images are already compressed)
        """
        try:
            # Check for JPEG blocking artifacts (8x8 blocks)
            h, w = image_cv.shape[:2]

            # Convert to grayscale and analyze DCT
            gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)

            # Detect block boundaries (every 8 pixels)
            block_edges_h = []
            block_edges_v = []

            for i in range(8, h, 8):
                # Check for sharp transitions at block boundaries
                diff = np.abs(gray[i:i+2, :] - gray[i-1:i+1, :])
                block_edges_h.append(np.mean(diff))

            for j in range(8, w, 8):
                diff = np.abs(gray[:, j:j+2] - gray[:, j-1:j+1])
                block_edges_v.append(np.mean(diff))

            # Calculate compression artifact score
            avg_block_edge = (np.mean(block_edges_h) + np.mean(block_edges_v)) / 2

            # Adjust thresholds for webcam (already compressed from video stream)
            if is_webcam:
                # Higher threshold for webcam since they're already compressed
                double_compression_threshold = 20
                artifact_threshold = 15
            else:
                # Normal thresholds
                double_compression_threshold = 15
                artifact_threshold = 10

            # Check for double compression
            has_double_compression = avg_block_edge > double_compression_threshold

            compression_score = 0
            if has_double_compression:
                compression_score = 30 if is_webcam else 40
            elif avg_block_edge > artifact_threshold:
                compression_score = 15 if is_webcam else 20

            findings = []
            if is_webcam:
                findings.append("Compression artifacts present (normal for webcam captures)")
                if has_double_compression:
                    findings.append("Additional compression detected - may indicate post-processing")
            else:
                if has_double_compression:
                    findings.append("Double compression detected - image was resaved")
                if avg_block_edge > artifact_threshold:
                    findings.append("Compression artifacts visible")

            return {
                'score': float(compression_score),
                'block_artifacts': float(avg_block_edge),
                'double_compression': bool(has_double_compression),
                'findings': list(findings),
                'is_webcam_adjusted': is_webcam
            }

        except Exception as e:
            logger.error(f"Compression analysis failed: {str(e)}")
            return {
                'score': 0.0,
                'block_artifacts': 0.0,
                'double_compression': False,
                'findings': [f"Compression analysis failed: {str(e)}"],
                'is_webcam_adjusted': is_webcam
            }

    def _analyze_colors(self, image_cv: np.ndarray, is_webcam: bool = False) -> dict:
        """
        Analyze color histogram for AI generator signatures.

        Different AI generators have characteristic color distributions.

        Args:
            image_cv: OpenCV image array
            is_webcam: True if image is from webcam (webcams have different color characteristics)
        """
        try:
            # Calculate histograms for each channel
            color_hist = []
            for i in range(3):
                hist = cv2.calcHist([image_cv], [i], None, [256], [0, 256])
                color_hist.append(hist)

            # Normalize histograms
            color_hist = [h / h.sum() for h in color_hist]

            # Analyze color distribution
            # Check for unusual saturation or contrast
            hsv = cv2.cvtColor(image_cv, cv2.COLOR_BGR2HSV)

            # Calculate saturation statistics
            saturation = hsv[:, :, 1].flatten()
            avg_saturation = np.mean(saturation)
            std_saturation = np.std(saturation)

            # Calculate value (brightness) statistics
            value = hsv[:, :, 2].flatten()
            avg_value = np.mean(value)
            std_value = np.std(value)

            # Color anomaly score
            # High saturation + low std = AI-generated characteristics
            # But webcams can have high saturation too (especially with good lighting)
            color_score = 0
            findings = []

            # Adjust thresholds for webcam
            if is_webcam:
                saturation_threshold = 170  # Higher threshold for webcam
                std_threshold = 50  # Tighter std threshold
            else:
                saturation_threshold = 150
                std_threshold = 60

            if avg_saturation > saturation_threshold and std_saturation < std_threshold:
                color_score = 20 if is_webcam else 30
                findings.append("High saturation with uniform distribution - AI-like colors")

            if std_value < 50:
                color_score += 5 if is_webcam else 10
                findings.append("Low contrast variation - possible AI generation")

            # Check for color clipping (AI generators often clip highlights/shadows)
            hist_r = color_hist[0]
            hist_g = color_hist[1]
            hist_b = color_hist[2]

            clipped_high = (hist_r[-10:].sum() + hist_g[-10:].sum() + hist_b[-10:].sum()) / 3
            clipped_low = (hist_r[:10].sum() + hist_g[:10].sum() + hist_b[:10].sum()) / 3

            # Adjust clipping threshold for webcam (webcams can clip in bright conditions)
            clipping_threshold = 0.08 if is_webcam else 0.05

            if clipped_high > clipping_threshold or clipped_low > clipping_threshold:
                add_score = 10 if is_webcam else 15
                color_score += add_score
                findings.append("Color channel clipping detected")

            if is_webcam and color_score == 0:
                findings.append("Color distribution within normal range for webcam")

            return {
                'score': min(100, color_score),
                'avg_saturation': float(avg_saturation),
                'std_saturation': float(std_saturation),
                'avg_value': float(avg_value),
                'std_value': float(std_value),
                'clipped_high': float(clipped_high),
                'clipped_low': float(clipped_low),
                'findings': findings,
                'is_webcam_adjusted': is_webcam
            }

        except Exception as e:
            logger.error(f"Color analysis failed: {str(e)}")
            return {
                'score': 0.0,
                'avg_saturation': 0.0,
                'std_saturation': 0.0,
                'avg_value': 0.0,
                'std_value': 0.0,
                'clipped_high': 0.0,
                'clipped_low': 0.0,
                'findings': [f"Color analysis failed: {str(e)}"],
                'is_webcam_adjusted': is_webcam
            }

    def _calculate_overall_score(self, results: dict, is_webcam: bool = False, is_video_frame: bool = False, is_collage: bool = False) -> float:
        """
        Calculate overall manipulation score from all analyses.

        Args:
            results: Dictionary of all analysis results
            is_webcam: True if image is from webcam (adjusts weights)
            is_video_frame: True if image is a frame from video (extra lenient)
            is_collage: True if image is detected as a collage (lenient treatment)

        Weights for video frames (most lenient - frames lack context):
        - ELA: 25% (reduced - frames have compression from video encoding)
        - Noise: 15% (reduced - video encoding affects noise patterns)
        - Color: 15% (reduced - colors change per frame)
        - Compression: 15% (reduced - all video frames are compressed)
        - Metadata: 5% (minimal - frames have no EXIF)

        Weights for collages (strict - collages are edited/manipulated content):
        - ELA: 40% (high - edited regions show ELA artifacts)
        - Noise: 20% (varied - different source images have different noise)
        - Color: 15% (reduced - color adjustments expected in edits)
        - Compression: 15% (normal - some compression in edits)
        - Metadata: 10% (low - metadata inconsistencies in edited content)

        Weights for webcam images (lenient because webcam has no EXIF):
        - ELA: 30%, Noise: 25%, Color: 20%, Compression: 15%, Metadata: 10%

        Weights for uploaded images (balanced):
        - ELA: 35%, Noise: 20%, Compression: 20%, Metadata: 15%, Color: 10%
        """
        if is_video_frame:
            # Most lenient - video frames naturally have compression and lack EXIF
            weights = {
                'metadata': 0.05,  # Minimal - frames have no EXIF by design
                'noise': 0.15,     # Reduced - video encoding affects noise
                'ela': 0.25,       # Reduced - frames are pre-compressed
                'compression': 0.15,  # Reduced - all frames compressed
                'color': 0.15      # Reduced - colors vary per frame
            }  # Total: 0.75 (intentionally low to allow easy passage)
        elif is_collage:
            # Strict for collages - they are edited/manipulated content
            # Collages should be classified as FAKE since they're not authentic
            weights = {
                'metadata': 0.10,  # Low - metadata may be inconsistent
                'noise': 0.20,     # Normal - different sources have different noise
                'ela': 0.40,       # High - detected edits show ELA artifacts
                'compression': 0.15,  # Normal - some compression in edits
                'color': 0.15      # Normal - color shifts in edited regions
            }  # Total: 1.0 (strict - penalizes detected collages)
        elif is_webcam:
            weights = {
                'metadata': 0.05,  # Very low - missing EXIF is NORMAL for webcam
                'noise': 0.25,     # Still important
                'ela': 0.30,       # Increased - main detector for webcam
                'compression': 0.15,
                'color': 0.25      # Increased - color analysis helps
            }
        else:
            # Balanced weights for uploaded images - ELA and compression are strongest indicators
            weights = {
                'metadata': 0.15,  # Increased slightly from 0.10 - still low but not zero
                'noise': 0.20,     # Increased from 0.15 - noise is a good indicator
                'ela': 0.35,       # Increased from 0.30 - ELA is the best indicator
                'compression': 0.20,  # Decreased from 0.25 - compression is good but not as strong as ELA
                'color': 0.10      # Decreased from 0.20 - color is less reliable
            }

        weighted_score = sum(
            results[key]['score'] * weights[key]
            for key in weights
        )

        # Boost score if multiple indicators found
        # Balanced boosting to avoid over-penalizing real photos
        total_indicators = sum(len(results[key].get('findings', [])) for key in results)

        if is_video_frame:
            # Minimal boosting for video frames - they're less reliable
            if total_indicators >= 8:
                weighted_score = min(100, weighted_score * 1.05)
        elif is_collage:
            # Aggressive boosting for detected collages - they're edited content
            # Multiple indicators in collages confirm the editing
            if total_indicators >= 4:
                weighted_score = min(100, weighted_score * 1.25)  # Strong boost for collages
            elif total_indicators >= 2:
                weighted_score = min(100, weighted_score * 1.15)  # Moderate boost
        elif is_webcam:
            # More conservative boosting for webcam
            if total_indicators >= 5:
                weighted_score = min(100, weighted_score * 1.15)
            elif total_indicators >= 4:
                weighted_score = min(100, weighted_score * 1.08)
        else:
            # Much more lenient boosting for uploads - real photos can have multiple minor indicators
            if total_indicators >= 5:  # Increased from 4 - need many indicators to boost
                weighted_score = min(100, weighted_score * 1.10)  # Reduced from 1.15
            elif total_indicators >= 3:  # Increased from 2 - more indicators needed
                weighted_score = min(100, weighted_score * 1.05)  # Reduced from 1.08

        # Apply soft cap to reduce false positives on real photos with normal compression

        # VIDEO FRAME: Most lenient soft cap (video frames are inherently compressed)
        if is_video_frame and 15 <= weighted_score <= 45:
            weighted_score = weighted_score * 0.40  # Reduce by 60% for video frames

        # COLLAGE: Aggressive soft cap (collages are edited/manipulated)
        elif is_collage and 35 <= weighted_score <= 65:
            # Collages should be boosted into FAKE range (>50) since they're edited
            # Push scores up to ensure they're classified as manipulated content
            weighted_score = weighted_score * 1.40  # Boost by 40% for collages

        # WEBCAM: Very lenient soft cap (webcam captures should almost always be REAL)
        elif is_webcam and 20 <= weighted_score <= 50:
            # Webcam captures often score higher due to:
            # - Higher compression baseline
            # - Missing EXIF (normal for canvas/webcam)
            # - Different noise characteristics
            weighted_score = weighted_score * 0.60  # Reduce by 40% for webcam

        # UPLOADED: Apply to uploaded images in the middle range (35-50%)
        # Real photos often score here due to natural compression and processing
        # But should still be considered real unless very high
        elif not is_video_frame and not is_webcam and 35 <= weighted_score <= 50:
            weighted_score = weighted_score * 0.75  # Reduce by 25% for this range

        # COLLAGE PENALTY: If collage detected, ensure it scores high enough to be FAKE
        # Collages are edited content and should be classified as manipulated/fake
        # Minimum score of 55 ensures collages are always classified as FAKE (> 50)
        if is_collage and weighted_score < 55:
            weighted_score = 55

        return round(weighted_score, 2)

    def _compile_indicators(self, results: dict) -> list:
        """Compile all manipulation indicators from all analyses."""
        indicators = []

        for analysis_type, analysis_result in results.items():
            findings = analysis_result.get('findings', [])
            for finding in findings:
                indicators.append(f"{analysis_type.upper()}: {finding}")

        return indicators

    def _generate_heatmap_data(self, difference_image: Image.Image) -> dict:
        """
        Generate heatmap data for visualization.

        Returns coordinates of high-difference regions for overlay.
        Always generates some hotspots for visualization purposes.
        """
        if difference_image is None:
            return {
                'hotspots': [],
                'total_hotspots': 0,
                'intensity_level': 'none'
            }

        try:
            # Convert to numpy array
            diff_array = np.array(difference_image)

            # Calculate intensity for each color channel
            intensity = np.mean(diff_array, axis=2)

            # Normalize intensity to 0-1 range
            max_intensity = np.max(intensity)
            if max_intensity > 0:
                intensity_normalized = intensity / max_intensity
            else:
                intensity_normalized = intensity

            # Find high-intensity regions (lowered threshold from 85 to 75 for more visibility)
            threshold = np.percentile(intensity, 75)
            high_intensity_mask = intensity > threshold

            # Find contours of suspicious regions
            contours, _ = cv2.findContours(
                high_intensity_mask.astype(np.uint8),
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )

            hotspots = []
            for contour in contours:
                if cv2.contourArea(contour) < 50:  # Reduced from 100 to 50
                    continue  # Skip very small regions

                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)

                # Calculate center
                center_x = x + w // 2
                center_y = y + h // 2

                # Calculate radius (max of width/height)
                radius = max(w, h) // 2

                # Calculate intensity at this region (normalized)
                region_intensity = float(np.mean(intensity_normalized[y:y+h, x:x+w]))

                # Convert to percentage coordinates
                h_img, w_img = intensity.shape
                hotspots.append({
                    'x': int((center_x / w_img) * 100),
                    'y': int((center_y / h_img) * 100),
                    'radius': min(50, int(radius)),  # Cap at 50% of image
                    'intensity': region_intensity
                })

            # If no hotspots found, create a few for visualization
            if not hotspots:
                # Create 3 representative hotspots based on image regions
                h_img, w_img = intensity.shape
                regions = [
                    (w_img // 4, h_img // 4),
                    (w_img // 2, h_img // 2),
                    (3 * w_img // 4, 3 * h_img // 4)
                ]

                for i, (rx, ry) in enumerate(regions):
                    # Sample intensity around this point
                    sample_radius = 50
                    y1, y2 = max(0, ry - sample_radius), min(h_img, ry + sample_radius)
                    x1, x2 = max(0, rx - sample_radius), min(w_img, rx + sample_radius)
                    region_intensity = float(np.mean(intensity_normalized[y1:y2, x1:x2]))

                    hotspots.append({
                        'x': int((rx / w_img) * 100),
                        'y': int((ry / h_img) * 100),
                        'radius': 15,  # Fixed radius for default hotspots
                        'intensity': region_intensity
                    })

            # Determine overall intensity level
            avg_intensity = np.mean([h['intensity'] for h in hotspots])
            if avg_intensity > 0.7:
                intensity_level = 'high'
            elif avg_intensity > 0.4:
                intensity_level = 'medium'
            else:
                intensity_level = 'low'

            return {
                'hotspots': hotspots,
                'total_hotspots': len(hotspots),
                'intensity_level': intensity_level
            }

        except Exception as e:
            logger.error(f"Heatmap generation failed: {str(e)}")
            return {
                'hotspots': [],
                'total_hotspots': 0,
                'intensity_level': 'error'
            }
