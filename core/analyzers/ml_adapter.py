"""
ML Adapter - Machine Learning Model Integration

This module provides integration with pre-trained deep learning models
for deepfake detection.

Supported models:
- FaceNet-PyTorch (face recognition for face swap detection)
- Future: FaceForensics++, XceptionNet, EfficientNet
"""

import logging
import os
from typing import Dict, Any
import numpy as np

try:
    import torch
    import torchvision.transforms as transforms
    from PIL import Image
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    from facenet_pytorch import InceptionResnetV1
    FACENET_AVAILABLE = True
except ImportError:
    FACENET_AVAILABLE = False

from .base_analyzer import BaseAnalyzer, AnalyzerError

logger = logging.getLogger(__name__)


class MLModelAdapter(BaseAnalyzer):
    """
    Adapter for machine learning models.

    Provides integration with pre-trained PyTorch models for
    deepfake detection.
    """

    def __init__(self, model_type: str = 'facenet', device: str = None):
        """
        Initialize ML adapter.

        Args:
            model_type: Type of model to load ('facenet', etc.)
            device: Device to run model on ('cuda', 'cpu', or None for auto)
        """
        super().__init__()
        self.model_type = model_type
        self.device = device or ('cuda' if TORCH_AVAILABLE and torch.cuda.is_available() else 'cpu')
        self.model = None
        self.model_loaded = False

        self._load_model()

    def _load_model(self):
        """
        Load the pre-trained model.

        Raises:
            AnalyzerError: If model loading fails
        """
        if not TORCH_AVAILABLE:
            logger.warning("PyTorch not available. ML analysis disabled.")
            return

        try:
            if self.model_type == 'facenet':
                if not FACENET_AVAILABLE:
                    logger.warning("FaceNet-PyTorch not available. Install with: pip install facenet-pytorch")
                    return

                logger.info(f"Loading FaceNet model on device: {self.device}")
                self.model = InceptionResnetV1(pretrained='vggface2').eval()
                self.model = self.model.to(self.device)
                self.model_loaded = True
                logger.info("FaceNet model loaded successfully")

            else:
                logger.warning(f"Unknown model type: {self.model_type}")

        except Exception as e:
            logger.error(f"Failed to load ML model: {str(e)}")
            self.model_loaded = False

    def analyze(self, image_path: str) -> Dict[str, Any]:
        """
        Run ML prediction on an image.

        Args:
            image_path: Path to image file

        Returns:
            dict with prediction results:
                - score: Manipulation likelihood (0-100)
                - details: Analysis details
                - indicators: List of indicators
        """
        if not self.model_loaded:
            return self._fallback_analysis()

        try:
            # Preprocess image
            image_tensor = self._preprocess_image(image_path)

            # Run inference
            with torch.no_grad():
                embedding = self.model(image_tensor)

            # Analyze embedding for anomalies
            # Face embeddings with unusual patterns may indicate manipulation
            anomaly_score = self._detect_embedding_anomaly(embedding)

            # Calculate manipulation score
            # Unusual embeddings -> higher manipulation score
            score = min(100, max(0, anomaly_score * 100))

            indicators = []
            if score > 60:
                indicators.append("Unusual face embedding detected")
            if score > 70:
                indicators.append("Possible face swap or manipulation")

            return {
                'score': float(score),
                'details': {
                    'model_type': self.model_type,
                    'embedding_norm': float(torch.norm(embedding).cpu()),
                    'device': self.device,
                    'model_loaded': True
                },
                'indicators': indicators
            }

        except Exception as e:
            logger.error(f"ML analysis failed: {str(e)}")
            return self._fallback_analysis()

    def _preprocess_image(self, image_path: str) -> torch.Tensor:
        """
        Preprocess image for ML model.

        Args:
            image_path: Path to image

        Returns:
            Preprocessed image tensor
        """
        # Load and transform image
        image = Image.open(image_path).convert('RGB')

        # FaceNet expects 160x160 RGB images
        transform = transforms.Compose([
            transforms.Resize((160, 160)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
        ])

        image_tensor = transform(image).unsqueeze(0)
        return image_tensor.to(self.device)

    def _detect_embedding_anomaly(self, embedding: torch.Tensor) -> float:
        """
        Detect if face embedding is anomalous.

        Real faces tend to have certain embedding characteristics.
        Manipulated faces may have unusual patterns.

        Args:
            embedding: Face embedding tensor

        Returns:
            Anomaly score (0-1)
        """
        # Calculate embedding statistics
        embedding_np = embedding.cpu().numpy().flatten()
        embedding_norm = np.linalg.norm(embedding_np)
        embedding_mean = np.mean(embedding_np)
        embedding_std = np.std(embedding_np)

        # Typical face embeddings have:
        # - Norm around 1-2 (normalized)
        # - Mean near 0
        # - Specific std range

        # Anomaly indicators:
        # 1. Unusual norm
        norm_anomaly = abs(embedding_norm - 1.0) / 2.0  # Deviation from expected

        # 2. Unusual mean
        mean_anomaly = abs(embedding_mean) / 0.5

        # 3. Unusual std
        std_anomaly = abs(embedding_std - 0.3) / 0.3

        # Combine anomaly scores
        anomaly_score = (norm_anomaly * 0.4 + mean_anomaly * 0.3 + std_anomaly * 0.3)

        return min(1.0, max(0.0, anomaly_score))

    def _fallback_analysis(self) -> Dict[str, Any]:
        """
        Fallback analysis when ML model is not available.

        Returns:
            Neutral/unknown analysis result
        """
        return {
            'score': 50.0,
            'details': {
                'model_loaded': False,
                'message': 'ML model not loaded. Using forensic analysis only.',
                'torch_available': TORCH_AVAILABLE,
                'facenet_available': FACENET_AVAILABLE
            },
            'indicators': ['ML analysis not available']
        }


class EnsembleAnalyzer(BaseAnalyzer):
    """
    Ensemble analyzer combining multiple models.

    Can combine:
    - Multiple ML models
    - Forensic analysis + ML models
    - Different model architectures
    """

    def __init__(self):
        super().__init__()
        self.analyzers = []

    def add_analyzer(self, analyzer: BaseAnalyzer, weight: float = 1.0):
        """
        Add an analyzer to the ensemble.

        Args:
            analyzer: BaseAnalyzer instance
            weight: Weight for this analyzer's predictions (default: 1.0)
        """
        self.analyzers.append({
            'analyzer': analyzer,
            'weight': weight
        })

    def analyze(self, image_path: str) -> dict:
        """
        Run ensemble analysis.

        Combines predictions from all analyzers using weighted average.
        """
        if not self.analyzers:
            return {
                'score': 50.0,
                'prediction': 'unknown',
                'confidence': 0.0,
                'details': {'message': 'No analyzers in ensemble'},
                'indicators': []
            }

        # Run all analyzers
        results = []
        total_weight = 0

        for item in self.analyzers:
            analyzer = item['analyzer']
            weight = item['weight']

            try:
                result = analyzer.analyze(image_path)
                results.append({
                    'score': result['score'] * weight,
                    'weight': weight
                })
                total_weight += weight
            except Exception as e:
                logger.error(f"Ensemble analyzer failed: {str(e)}")

        # Calculate weighted average
        if total_weight > 0:
            weighted_score = sum(r['score'] for r in results) / total_weight
        else:
            weighted_score = 50.0

        return {
            'score': weighted_score,
            'prediction': 'fake' if weighted_score > 50 else 'real',
            'confidence': abs(weighted_score - 50) * 2,
            'details': {
                'ensemble_size': len(self.analyzers),
                'individual_results': results
            },
            'indicators': [f"Ensemble of {len(self.analyzers)} analyzers"]
        }
