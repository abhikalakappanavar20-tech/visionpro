"""
Quick test script to check video analysis
"""
import os
import sys

# Add the project to path
sys.path.insert(0, r'c:\Users\270356\OneDrive\Desktop\BCA_Projects\VeriVisionPro')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'VeriVision.settings')

import django
django.setup()

from core.analyzers import ForensicPipeline

# Test video analysis
pipeline = ForensicPipeline()

# Test with a sample video file (replace with actual path)
test_video = r'path\to\test\video.mp4'

if os.path.exists(test_video):
    try:
        print(f"Analyzing video: {test_video}")
        result = pipeline.analyze_video(test_video)
        print(f"Success! Score: {result['confidence_score']}%")
        print(f"Result: {result['scan_result']}")
        print(f"Details keys: {result['forensic_details'].keys()}")
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
else:
    print(f"Video file not found: {test_video}")
    print("Please update the path to a real video file")
