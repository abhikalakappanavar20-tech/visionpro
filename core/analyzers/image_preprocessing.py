"""
Image Preprocessing Module

Handles image quality enhancement and normalization before analysis.
"""

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import logging
import os

logger = logging.getLogger(__name__)


def enhance_image_for_analysis(image_path: str, is_webcam: bool = False) -> tuple:
    """
    Enhance image quality for forensic analysis.

    Args:
        image_path: Path to image file
        is_webcam: True if image is from webcam capture

    Returns:
        tuple: (enhanced_pil_image, enhanced_cv_image, metadata_dict)
    """
    try:
        # Load image
        pil_image = Image.open(image_path).convert('RGB')
        cv_image = cv2.imread(image_path)

        if pil_image is None or cv_image is None:
            raise ValueError("Failed to load image")

        metadata = {
            'original_size': pil_image.size,
            'is_webcam': is_webcam,
            'enhancements_applied': []
        }

        # For webcam images, apply different enhancements
        if is_webcam:
            # Webcam images are often softer and have compression artifacts
            # Apply mild sharpening to reduce compression blur
            pil_image = pil_image.filter(ImageFilter.UnsharpMask(radius=1, percent=120))
            metadata['enhancements_applied'].append('unsharp_mask')

            # Enhance contrast slightly
            enhancer = ImageEnhance.Contrast(pil_image)
            pil_image = enhancer.enhance(1.1)
            metadata['enhancements_applied'].append('contrast_enhance')

        # Ensure minimum resolution for analysis
        width, height = pil_image.size
        min_dimension = 512

        if width < min_dimension or height < min_dimension:
            # Calculate scaling factor
            scale = max(min_dimension / width, min_dimension / height)
            new_size = (int(width * scale), int(height * scale))

            # Use high-quality resampling
            pil_image = pil_image.resize(new_size, Image.Resampling.LANCZOS)
            cv_image = cv2.resize(cv_image, new_size, interpolation=cv2.INTER_LANCZOS4)

            metadata['enhancements_applied'].append('upscale')
            metadata['upscaled_from'] = (width, height)
            metadata['upscaled_to'] = new_size

        # Denoise slightly (helps with ELA analysis)
        if not is_webcam:
            # Only denoise non-webcam images lightly
            cv_image = cv2.fastNlMeansDenoisingColored(cv_image, None, 3, 3, 7, 21)
            metadata['enhancements_applied'].append('denoise')

        metadata['final_size'] = pil_image.size

        return pil_image, cv_image, metadata

    except Exception as e:
        logger.error(f"Image preprocessing failed: {str(e)}")
        # Return original images if preprocessing fails
        pil_image = Image.open(image_path).convert('RGB')
        cv_image = cv2.imread(image_path)
        return pil_image, cv_image, {'error': str(e)}


def validate_image_quality(image_path: str) -> dict:
    """
    Validate that image meets minimum quality requirements.

    Args:
        image_path: Path to image file

    Returns:
        dict with validation results
    """
    try:
        image = Image.open(image_path)
        cv_image = cv2.imread(image_path)

        validation = {
            'valid': True,
            'warnings': [],
            'errors': []
        }

        # Check resolution
        width, height = image.size
        if width < 256 or height < 256:
            validation['warnings'].append(f"Low resolution: {width}x{height}. Analysis may be less accurate.")
            if width < 128 or height < 128:
                validation['valid'] = False
                validation['errors'].append("Resolution too low for analysis")

        # Check if image is too blurry
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        if laplacian_var < 50:
            validation['warnings'].append("Image appears blurry. Results may be affected.")
        elif laplacian_var < 20:
            validation['valid'] = False
            validation['errors'].append("Image too blurry for analysis")

        # Check file size (very small files are likely low quality)
        file_size = os.path.getsize(image_path)
        if file_size < 10240:  # Less than 10KB
            validation['warnings'].append("Very small file size. May be highly compressed.")

        return validation

    except Exception as e:
        return {
            'valid': False,
            'errors': [f"Validation failed: {str(e)}"],
            'warnings': []
        }


def is_webcam_capture(image_path: str) -> bool:
    """
    Detect if image is likely from webcam capture.

    Checks for:
    - Missing EXIF data (canvas-created images have no EXIF)
    - Specific dimensions (common webcam resolutions)
    - File naming patterns

    Args:
        image_path: Path to image file

    Returns:
        bool: True if likely webcam capture
    """
    try:
        from PIL.ExifTags import TAGS
        import os

        # Check file name - strong indicator
        filename = os.path.basename(image_path).lower()
        if 'webcam' in filename or 'capture' in filename:
            return True

        image = Image.open(image_path)
        width, height = image.size

        # Check dimensions (common webcam resolutions) - strong indicator
        common_webcam_resolutions = [
            (640, 480), (320, 240), (1280, 720),
            (1920, 1080), (1280, 1024), (2560, 1440)
        ]
        if (width, height) in common_webcam_resolutions:
            return True

        # Check EXIF data - but ONLY for JPEG/TIFF formats
        # PNG, WEBP, GIF typically don't have EXIF, so missing EXIF is normal
        fmt = image.format.lower() if image.format else ''
        if fmt in ('jpeg', 'jpg', 'tiff', 'tif'):
            try:
                exif = image._getexif()
                if not exif or len(exif) < 5:
                    # JPEG with no EXIF is suspicious but not necessarily webcam
                    # Require additional evidence (common webcam resolution)
                    return False
            except Exception:
                # Can't read EXIF from JPEG - possible webcam/screenshot
                return False

        # For non-JPEG formats, don't assume webcam just because of missing EXIF
        return False

    except Exception:
        return False
