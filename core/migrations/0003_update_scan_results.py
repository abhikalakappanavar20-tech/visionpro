# Generated migration to update existing scan results

from django.db import migrations

def convert_scan_results(apps, schema_editor):
    """Convert suspicious/manipulated to real/fake based on confidence score"""
    MediaScan = apps.get_model('core', 'MediaScan')

    for scan in MediaScan.objects.all():
        if scan.scan_result == 'suspicious':
            # Suspicious (35-55%) becomes FAKE (any manipulation)
            scan.scan_result = 'fake'
            scan.save()
        elif scan.scan_result == 'manipulated':
            # Manipulated (55-75%) becomes FAKE
            scan.scan_result = 'fake'
            scan.save()

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0002_alter_mediascan_scan_result'),
    ]

    operations = [
        migrations.RunPython(convert_scan_results),
    ]
