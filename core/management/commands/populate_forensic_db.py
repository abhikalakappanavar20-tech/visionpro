"""
Django management command to populate forensic database with sample data
"""
from django.core.management.base import BaseCommand
from core.models import ForensicDatabase
from datetime import datetime, timedelta
import random


class Command(BaseCommand):
    help = 'Populate forensic database with sample data'

    def handle(self, *args, **options):
        # Clear existing data
        ForensicDatabase.objects.all().delete()
        self.stdout.write('Cleared existing forensic data')

        # Sample data
        contexts = [
            "Used in known botnet disinformation campaign",
            "Found on multiple fake news platforms",
            "Associated with coordinated influence operation",
            "Originates from known manipulation source",
            "Detected in previous scam investigations",
            "Linked to fraudulent account networks",
            "Part of political disinformation campaign",
            "Used in financial fraud schemes",
            "Associated with deepfake celebrity scams",
            "Detected in romance scam operations"
        ]

        campaigns = [
            "Operation Fake Storm 2023",
            "Disinformation Network #47",
            "Botnet Campaign Alpha",
            "Coordinated Inauthentic Behavior",
            "Unknown/Unattributed",
            "Scam Network Beta",
            "Influence Operation Gamma"
        ]

        threat_levels = ['low', 'medium', 'high', 'critical']
        content_types = ['image', 'video', 'audio']

        # Generate 50 sample entries
        for i in range(50):
            # Generate random hash
            import hashlib
            hash_input = f"sample_{i}_{random.randint(1000, 9999)}"
            content_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:64]

            # Random date within last 2 years
            days_ago = random.randint(30, 730)
            first_seen = datetime.now() - timedelta(days=days_ago)

            forensic_entry = ForensicDatabase.objects.create(
                content_hash=content_hash,
                content_type=random.choice(content_types),
                first_seen=first_seen.date(),
                usage_count=random.randint(1, 100),
                context=random.choice(contexts),
                known_campaigns=random.choice(campaigns),
                threat_level=random.choice(threat_levels)
            )

            self.stdout.write(f'Created entry: {content_hash[:16]}...')

        self.stdout.write(self.style.SUCCESS(f'\nSuccessfully created {ForensicDatabase.objects.count()} forensic database entries'))
