"""
AI Deepfake Detector - Real ML-Based Detection

Uses pre-trained models from Hugging Face for genuine deepfake detection:
- Image: ResNet-18 trained on FaceForensics++ (abraraltaf92/deepfake-detection-models)
- Video: R3D-18 for temporal deepfake detection
- Audio: Wav2Vec2 for synthetic speech detection (garystafford/wav2vec2-deepfake-voice-detector)

All models are lazy-loaded on first use to avoid slow startup.
"""

import logging
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)

# Use HF_HOME env (set to /tmp on Vercel) or fallback to project dir
_MODELS_DIR_ENV = os.environ.get('HF_HOME')
if _MODELS_DIR_ENV:
    MODELS_DIR = Path(_MODELS_DIR_ENV) / 'models'
else:
    MODELS_DIR = Path(__file__).resolve().parent.parent / 'ml_models'

# HuggingFace repo IDs
IMAGE_MODEL_REPO = 'abraraltaf92/deepfake-detection-models'
AUDIO_MODEL_REPO = 'garystafford/wav2vec2-deepfake-voice-detector'


def _lazy_import_torch():
    try:
        import torch
        return torch
    except ImportError:
        logger.warning("PyTorch not available. AI detection disabled.")
        return None


def _lazy_import_transformers():
    try:
        import transformers
        return transformers
    except ImportError:
        logger.warning("transformers not available. AI detection disabled.")
        return None


def _lazy_import_facenet():
    try:
        from facenet_pytorch import MTCNN
        return MTCNN
    except ImportError:
        logger.warning("facenet-pytorch not available. Face detection disabled.")
        return None


class ImageAIDetector:
    """
    Real deepfake detection for images using a pre-trained ResNet-18.

    Downloads model weights from Hugging Face on first use.
    Uses MTCNN for face extraction, then classifies each face.
    """

    def __init__(self, device: str = None):
        self.device = device
        self.model = None
        self.model_loaded = False
        self.mtcnn = None
        self._load_lock = False

    def _ensure_loaded(self):
        if self.model_loaded or self._load_lock:
            return
        self._load_lock = True
        try:
            self._load_model()
        finally:
            self._load_lock = False

    def _load_model(self):
        torch = _lazy_import_torch()
        if torch is None:
            return

        try:
            from huggingface_hub import hf_hub_download
            import torchvision.models as tv_models
            import torchvision.transforms as transforms

            if self.device is None:
                self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

            logger.info(f"Downloading image deepfake model from {IMAGE_MODEL_REPO}...")

            # Download ResNet-18 weights
            weights_path = hf_hub_download(
                repo_id=IMAGE_MODEL_REPO,
                filename='resnet18_best.pth',
                cache_dir=str(MODELS_DIR),
            )

            # Build ResNet-18 with binary classification head
            model = tv_models.resnet18(pretrained=False)
            num_ftrs = model.fc.in_features
            model.fc = torch.nn.Linear(num_ftrs, 2)

            # Load trained weights
            state_dict = torch.load(weights_path, map_location='cpu', weights_only=True)
            if 'model_state_dict' in state_dict:
                state_dict = state_dict['model_state_dict']
            elif 'state_dict' in state_dict:
                state_dict = state_dict['state_dict']

            # Handle DataParallel keys
            cleaned = {}
            for k, v in state_dict.items():
                cleaned[k.replace('module.', '')] = v
            model.load_state_dict(cleaned, strict=False)

            model = model.to(self.device)
            model.eval()
            self.model = model

            # Image preprocessing
            self.transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                     std=[0.229, 0.224, 0.225])
            ])

            # MTCNN for face detection
            MTCNN = _lazy_import_facenet()
            if MTCNN is not None:
                self.mtcnn = MTCNN(keep_all=True, device=self.device,
                                   min_face_size=40, thresholds=[0.6, 0.7, 0.7])

            self.model_loaded = True
            logger.info("Image AI detector loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load image AI model: {e}")
            self.model_loaded = False

    def analyze(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze an image for deepfake content.

        Returns:
            dict with score (0-100 manipulation likelihood), details, indicators
        """
        self._ensure_loaded()

        if not self.model_loaded:
            return {
                'score': 50.0,
                'details': {'model_loaded': False, 'message': 'AI model not available'},
                'indicators': ['AI image detection unavailable - model not loaded']
            }

        torch = _lazy_import_torch()
        from PIL import Image

        try:
            image = Image.open(image_path).convert('RGB')
            faces = self._extract_faces(image, image_path)

            if not faces:
                # No faces found - analyze full image
                score = self._classify_image(image)
                return {
                    'score': score,
                    'details': {
                        'model': 'ResNet-18 (FaceForensics++)',
                        'faces_detected': 0,
                        'face_scores': [],
                        'full_image_score': score,
                        'device': self.device,
                    },
                    'indicators': self._make_indicators(score, 0)
                }

            # Analyze each face
            face_scores = []
            for i, face_tensor in enumerate(faces):
                face_score = self._classify_tensor(face_tensor)
                face_scores.append(round(face_score, 2))

            # Aggregate: weighted toward highest-scoring face (most suspicious)
            avg_score = np.mean(face_scores)
            max_score = np.max(face_scores)
            combined = 0.6 * max_score + 0.4 * avg_score

            return {
                'score': round(float(combined), 2),
                'details': {
                    'model': 'ResNet-18 (FaceForensics++)',
                    'faces_detected': len(faces),
                    'face_scores': face_scores,
                    'avg_face_score': round(float(avg_score), 2),
                    'max_face_score': round(float(max_score), 2),
                    'device': self.device,
                },
                'indicators': self._make_indicators(combined, len(faces))
            }

        except Exception as e:
            logger.error(f"Image AI analysis failed: {e}")
            return {
                'score': 50.0,
                'details': {'error': str(e)},
                'indicators': [f'AI analysis error: {e}']
            }

    def _extract_faces(self, pil_image, image_path: str):
        """Extract face tensors using MTCNN or fallback to full image."""
        torch = _lazy_import_torch()
        if torch is None:
            return []

        if self.mtcnn is not None:
            try:
                faces = self.mtcnn(pil_image)
                if faces is not None and len(faces) > 0:
                    return [faces[i].unsqueeze(0).to(self.device) for i in range(len(faces))]
            except Exception as e:
                logger.debug(f"MTCNN face extraction failed: {e}")

        # Fallback: use full image as single "face"
        tensor = self.transform(pil_image).unsqueeze(0).to(self.device)
        return [tensor]

    def _classify_image(self, pil_image) -> float:
        """Classify a full image."""
        torch = _lazy_import_torch()
        tensor = self.transform(pil_image).unsqueeze(0).to(self.device)
        return self._classify_tensor(tensor)

    def _classify_tensor(self, tensor) -> float:
        """Run model inference on a tensor, return fake probability 0-100."""
        torch = _lazy_import_torch()
        with torch.no_grad():
            output = self.model(tensor)
            probs = torch.softmax(output, dim=1)
            fake_prob = probs[0][1].item()  # index 1 = fake
            return fake_prob * 100.0

    def _make_indicators(self, score: float, num_faces: int) -> List[str]:
        indicators = []
        if num_faces > 0:
            indicators.append(f"Detected {num_faces} face(s) for analysis")
        if score > 80:
            indicators.append("Strong AI-generated content indicators")
        elif score > 60:
            indicators.append("Moderate manipulation indicators detected")
        elif score > 40:
            indicators.append("Weak manipulation signals - uncertain")
        else:
            indicators.append("Content appears authentic")
        return indicators


class VideoAIDetector:
    """
    Deepfake detection for video using per-frame ResNet-18 analysis
    with temporal consistency checks.
    """

    def __init__(self, device: str = None):
        self.image_detector = ImageAIDetector(device=device)
        self.device = device or self.image_detector.device

    def analyze(self, video_path: str, max_frames: int = 20) -> Dict[str, Any]:
        """
        Analyze video by extracting key frames and running image detection.

        Returns:
            dict with score, details, indicators
        """
        torch = _lazy_import_torch()
        if torch is None:
            return {
                'score': 50.0,
                'details': {'message': 'PyTorch not available'},
                'indicators': ['Video AI detection unavailable']
            }

        try:
            import cv2

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return {
                    'score': 50.0,
                    'details': {'error': 'Cannot open video'},
                    'indicators': ['Video file could not be opened']
                }

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            duration = total_frames / fps if fps > 0 else 0

            # Extract evenly-spaced frames
            frame_indices = np.linspace(0, max(0, total_frames - 1), min(max_frames, total_frames), dtype=int)

            frame_scores = []
            for idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
                ret, frame = cap.read()
                if not ret:
                    continue

                # Convert BGR to RGB
                from PIL import Image
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_frame = Image.fromarray(rgb)

                # Run image detector on this frame
                result = self.image_detector.analyze(pil_frame)
                frame_scores.append(result['score'])

            cap.release()

            if not frame_scores:
                return {
                    'score': 50.0,
                    'details': {'error': 'No frames extracted'},
                    'indicators': ['Could not extract frames from video']
                }

            # Temporal analysis
            avg_score = np.mean(frame_scores)
            max_score = np.max(frame_scores)
            std_score = np.std(frame_scores)

            # Consistency check: AI videos often have suspiciously uniform scores
            consistency = 100 - min(100, std_score * 5)

            # Combine: high max + high avg + high consistency = likely fake
            temporal_bonus = 0
            if consistency > 85 and avg_score > 55:
                temporal_bonus = 10
            if consistency > 90 and max_score > 70:
                temporal_bonus += 5

            combined = min(100, 0.5 * max_score + 0.3 * avg_score + 0.2 * (avg_score + temporal_bonus))

            return {
                'score': round(float(combined), 2),
                'details': {
                    'model': 'ResNet-18 frame-by-frame + temporal analysis',
                    'total_frames': total_frames,
                    'analyzed_frames': len(frame_scores),
                    'duration_seconds': round(duration, 2),
                    'fps': round(fps, 2),
                    'frame_scores': [round(s, 2) for s in frame_scores],
                    'avg_frame_score': round(float(avg_score), 2),
                    'max_frame_score': round(float(max_score), 2),
                    'score_std': round(float(std_score), 2),
                    'temporal_consistency': round(consistency, 2),
                    'temporal_bonus': temporal_bonus,
                    'device': self.device,
                },
                'indicators': self._make_indicators(combined, len(frame_scores), consistency)
            }

        except Exception as e:
            logger.error(f"Video AI analysis failed: {e}")
            return {
                'score': 50.0,
                'details': {'error': str(e)},
                'indicators': [f'Video AI analysis error: {e}']
            }

    def _make_indicators(self, score, num_frames, consistency):
        indicators = [f"Analyzed {num_frames} key frames"]
        if consistency > 85:
            indicators.append("Highly consistent frame scores (possible synthetic)")
        if score > 75:
            indicators.append("Strong deepfake indicators across video frames")
        elif score > 55:
            indicators.append("Moderate manipulation signals in video")
        else:
            indicators.append("Video appears authentic")
        return indicators


class AudioAIDetector:
    """
    Deepfake audio detection using Wav2Vec2.

    Uses garystafford/wav2vec2-deepfake-voice-detector from Hugging Face.
    """

    def __init__(self, device: str = None):
        self.device = device
        self.model = None
        self.feature_extractor = None
        self.model_loaded = False
        self._load_lock = False

    def _ensure_loaded(self):
        if self.model_loaded or self._load_lock:
            return
        self._load_lock = True
        try:
            self._load_model()
        finally:
            self._load_lock = False

    def _load_model(self):
        torch = _lazy_import_torch()
        transformers = _lazy_import_transformers()
        if torch is None or transformers is None:
            return

        try:
            from transformers import AutoModelForAudioClassification, AutoFeatureExtractor

            if self.device is None:
                self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

            logger.info(f"Downloading audio deepfake model from {AUDIO_MODEL_REPO}...")

            self.feature_extractor = AutoFeatureExtractor.from_pretrained(AUDIO_MODEL_REPO)
            self.model = AutoModelForAudioClassification.from_pretrained(AUDIO_MODEL_REPO)
            self.model = self.model.to(self.device)
            self.model.eval()

            self.model_loaded = True
            logger.info("Audio AI detector loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load audio AI model: {e}")
            self.model_loaded = False

    def analyze(self, audio_path: str) -> Dict[str, Any]:
        """
        Analyze audio for synthetic/deepfake speech.

        Returns:
            dict with score (0-100 fake likelihood), details, indicators
        """
        self._ensure_loaded()

        if not self.model_loaded:
            return {
                'score': 50.0,
                'details': {'model_loaded': False, 'message': 'Audio AI model not available'},
                'indicators': ['AI audio detection unavailable - model not loaded']
            }

        torch = _lazy_import_torch()

        try:
            import librosa
            import soundfile as sf

            # Load audio at 16kHz (required by Wav2Vec2)
            target_sr = 16000
            max_duration = 30  # seconds

            try:
                waveform, sr = librosa.load(audio_path, sr=target_sr, duration=max_duration)
            except Exception:
                # Fallback: try soundfile directly
                data, sr = sf.read(audio_path)
                if sr != target_sr:
                    import scipy.signal
                    data = scipy.signal.resample(data, int(len(data) * target_sr / sr))
                waveform = data
                sr = target_sr

            duration = len(waveform) / sr

            # Process in chunks if audio is long (Wav2Vec2 has token limit)
            chunk_length = 4 * target_sr  # 4 seconds
            chunks = []
            for start in range(0, len(waveform), chunk_length):
                chunk = waveform[start:start + chunk_length]
                if len(chunk) < chunk_length:
                    chunk = np.pad(chunk, (0, chunk_length - len(chunk)))
                chunks.append(chunk)

            # Analyze each chunk
            fake_probs = []
            for chunk in chunks:
                inputs = self.feature_extractor(
                    chunk,
                    sampling_rate=target_sr,
                    return_tensors='pt',
                    padding=True
                )
                input_values = inputs['input_values'].to(self.device)

                with torch.no_grad():
                    outputs = self.model(input_values)
                    probs = torch.softmax(outputs.logits, dim=1)
                    # Assuming label 1 = fake/synthetic
                    if hasattr(self.model.config, 'id2label'):
                        labels = self.model.config.id2label
                        fake_idx = 1 if labels.get(1, '').lower() in ['fake', 'spoof', 'synthetic', 'deepfake'] else 0
                    else:
                        fake_idx = 1
                    fake_prob = probs[0][fake_idx].item()
                    fake_probs.append(fake_prob)

            # Aggregate chunk results
            avg_fake = np.mean(fake_probs) * 100
            max_fake = np.max(fake_probs) * 100

            # Weight toward the most suspicious chunk
            combined = 0.7 * max_fake + 0.3 * avg_fake

            return {
                'score': round(float(combined), 2),
                'details': {
                    'model': 'Wav2Vec2 (deepfake voice detector)',
                    'duration_seconds': round(duration, 2),
                    'sample_rate': sr,
                    'chunks_analyzed': len(chunks),
                    'chunk_fake_probs': [round(float(p) * 100, 2) for p in fake_probs],
                    'avg_fake_probability': round(float(avg_fake), 2),
                    'max_fake_probability': round(float(max_fake), 2),
                    'device': self.device,
                },
                'indicators': self._make_indicators(combined, duration, len(chunks))
            }

        except Exception as e:
            logger.error(f"Audio AI analysis failed: {e}")
            return {
                'score': 50.0,
                'details': {'error': str(e)},
                'indicators': [f'Audio AI analysis error: {e}']
            }

    def _make_indicators(self, score, duration, num_chunks):
        indicators = [f"Analyzed {duration:.1f}s audio in {num_chunks} chunk(s)"]
        if score > 80:
            indicators.append("Strong synthetic speech indicators detected")
        elif score > 60:
            indicators.append("Moderate AI voice cloning signals")
        elif score > 40:
            indicators.append("Weak manipulation signals - uncertain")
        else:
            indicators.append("Audio appears to be natural human speech")
        return indicators
