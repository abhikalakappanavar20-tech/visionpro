"""
Django Management Command: Populate AI Generator Signatures

Populates the database with AI generator signatures for source detection.

Usage:
    python manage.py populate_ai_signatures
"""

from django.core.management.base import BaseCommand
from core.models import AIGeneratorSignature


class Command(BaseCommand):
    help = 'Populate database with AI generator signatures'

    def handle(self, *args, **options):
        """Execute the command."""
        self.stdout.write('Populating AI generator signatures...')

        # AI Generator signatures data
        signatures_data = [
            {
                'name': 'Midjourney v5',
                'generator_type': 'image',
                'typical_resolutions': ['1024x1024', '2048x2048', '1024x1792'],
                'noise_pattern': {
                    'uniformity_range': [0.4, 0.6],
                    'distribution': 'non-uniform',
                    'characteristics': ['patchy', 'inconsistent_across_regions']
                },
                'color_signature': {
                    'saturation_range': [140, 180],
                    'contrast_range': [50, 80],
                    'warmth': 'slightly_warm',
                    'characteristic': 'high_saturation'
                },
                'ela_threshold_min': 15.0,
                'ela_threshold_max': 35.0,
                'metadata_patterns': {
                    'missing_exif': True,
                    'software_signatures': []
                },
                'compression_artifacts': 'minimal_high_quality',
                'key_indicators': [
                    'High saturation with warm tone',
                    'Non-uniform noise distribution',
                    'Clean edges with occasional artifacts',
                    '1024x1024 or 2048x2048 resolution',
                    'No EXIF data'
                ]
            },
            {
                'name': 'DALL-E 3',
                'generator_type': 'image',
                'typical_resolutions': ['1024x1024'],
                'noise_pattern': {
                    'uniformity_range': [0.5, 0.7],
                    'distribution': 'relatively_uniform',
                    'characteristics': ['smooth', 'low_texture_detail']
                },
                'color_signature': {
                    'saturation_range': [100, 150],
                    'contrast_range': [40, 70],
                    'characteristic': 'vivid_colors'
                },
                'ela_threshold_min': 10.0,
                'ela_threshold_max': 25.0,
                'metadata_patterns': {
                    'missing_exif': True,
                    'watermark_possible': True
                },
                'compression_artifacts': 'minimal',
                'key_indicators': [
                    'Balanced vivid colors',
                    'Relatively smooth surfaces',
                    '1024x1024 resolution',
                    'Possible watermark',
                    'No EXIF data'
                ]
            },
            {
                'name': 'Stable Diffusion',
                'generator_type': 'image',
                'typical_resolutions': ['512x512', '768x768', '1024x1024'],
                'noise_pattern': {
                    'uniformity_range': [0.3, 0.5],
                    'distribution': 'inconsistent',
                    'characteristics': ['grainy', 'artifacts_in_edges']
                },
                'color_signature': {
                    'saturation_range': [120, 170],
                    'contrast_range': [60, 90],
                    'characteristic': 'high_contrast'
                },
                'ela_threshold_min': 20.0,
                'ela_threshold_max': 40.0,
                'metadata_patterns': {
                    'missing_exif': True,
                    'compression_signatures': True
                },
                'compression_artifacts': 'visible_compression_blocks',
                'key_indicators': [
                    'High contrast and saturation',
                    'Grainy noise pattern',
                    'Edge artifacts',
                    'Common resolutions: 512x512, 768x768',
                    'Compression block artifacts'
                ]
            },
            {
                'name': 'DeepFaceLab',
                'generator_type': 'manipulation',
                'typical_resolutions': ['variable'],
                'noise_pattern': {
                    'uniformity_range': [0.2, 0.4],
                    'distribution': 'inconsistent',
                    'characteristics': ['face_region_mismatch', 'boundary_artifacts']
                },
                'color_signature': {
                    'saturation_range': [80, 140],
                    'contrast_range': [30, 70],
                    'characteristic': 'skin_tone_inconsistency'
                },
                'ela_threshold_min': 30.0,
                'ela_threshold_max': 60.0,
                'metadata_patterns': {
                    'missing_exif': True,
                    'face_artifacts': True
                },
                'compression_artifacts': 'double_compression_likely',
                'key_indicators': [
                    'Face boundary artifacts',
                    'Skin tone inconsistencies',
                    'High ELA at face edges',
                    'Variable resolution',
                    'Double compression'
                ]
            },
            {
                'name': 'Faceswap',
                'generator_type': 'manipulation',
                'typical_resolutions': ['variable'],
                'noise_pattern': {
                    'uniformity_range': [0.25, 0.45],
                    'distribution': 'inconsistent',
                    'characteristics': ['lighting_inconsistency', 'boundary_artifacts']
                },
                'color_signature': {
                    'saturation_range': [90, 130],
                    'contrast_range': [40, 60],
                    'characteristic': 'skin_tone_mismatch'
                },
                'ela_threshold_min': 25.0,
                'ela_threshold_max': 55.0,
                'metadata_patterns': {
                    'missing_exif': True,
                    'face_artifacts': True
                },
                'compression_artifacts': 'moderate',
                'key_indicators': [
                    'Face lighting inconsistencies',
                    'Skin tone mismatch at boundaries',
                    'ELA highlights face edges',
                    'Variable resolution',
                    'Possible double compression'
                ]
            }
        ]

        # Clear existing signatures
        count_deleted = AIGeneratorSignature.objects.all().delete()[0]
        self.stdout.write(f'Deleted {count_deleted} existing signatures')

        # Add new signatures
        created_count = 0
        for sig_data in signatures_data:
            signature, created = AIGeneratorSignature.objects.get_or_create(
                name=sig_data['name'],
                defaults=sig_data
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'[+] Created: {signature.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'[*] Updated: {signature.name}'))

        self.stdout.write(self.style.SUCCESS(
            f'\nSuccessfully populated {created_count} AI generator signatures!'
        ))

        # Display summary
        total = AIGeneratorSignature.objects.count()
        self.stdout.write(f'\nTotal signatures in database: {total}')
