"""
Management command to pre-download AI models from Hugging Face.

Usage:
    python manage.py download_ai_models
    python manage.py download_ai_models --image-only
    python manage.py download_ai_models --audio-only
"""

import os
import sys
from pathlib import Path
from django.core.management.base import BaseCommand

MODELS_DIR = Path(__file__).resolve().parent.parent.parent.parent / 'ml_models'


class Command(BaseCommand):
    help = 'Download AI deepfake detection models from Hugging Face'

    def add_arguments(self, parser):
        parser.add_argument('--image-only', action='store_true', help='Download only image model')
        parser.add_argument('--audio-only', action='store_true', help='Download only audio model')
        parser.add_argument('--force', action='store_true', help='Re-download even if cached')

    def handle(self, *args, **options):
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        (MODELS_DIR / '.gitkeep').touch(exist_ok=True)

        do_image = not options['audio_only']
        do_audio = not options['image_only']

        if do_image:
            self._download_image_model(options['force'])
        if do_audio:
            self._download_audio_model(options['force'])

        self.stdout.write(self.style.SUCCESS('All requested models downloaded successfully.'))

    def _download_image_model(self, force):
        self.stdout.write('Downloading image deepfake detection model...')
        try:
            from huggingface_hub import hf_hub_download

            path = hf_hub_download(
                repo_id='abraraltaf92/deepfake-detection-models',
                filename='resnet18_best.pth',
                cache_dir=str(MODELS_DIR),
                force_download=force,
            )
            self.stdout.write(self.style.SUCCESS(f'  Image model saved to: {path}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  Failed to download image model: {e}'))
            self.stdout.write(self.style.WARNING('  Image AI detection will use fallback on first use.'))

    def _download_audio_model(self, force):
        self.stdout.write('Downloading audio deepfake detection model...')
        try:
            from transformers import AutoModelForAudioClassification, AutoFeatureExtractor

            repo = 'garystafford/wav2vec2-deepfake-voice-detector'

            AutoFeatureExtractor.from_pretrained(repo)
            AutoModelForAudioClassification.from_pretrained(repo)

            self.stdout.write(self.style.SUCCESS(f'  Audio model downloaded from: {repo}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  Failed to download audio model: {e}'))
            self.stdout.write(self.style.WARNING('  Audio AI detection will use fallback on first use.'))
