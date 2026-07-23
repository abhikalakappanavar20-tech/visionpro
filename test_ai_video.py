#!/usr/bin/env python
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'VeriVision.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from core.analyzers import ForensicPipeline

video_path = "media/videos/WhatsApp_Video_2026-05-11_at_10.23.05_PM.mp4"

pipeline = ForensicPipeline()
result = pipeline.analyze_video(video_path, source='upload')

print(f"RESULT: {result['scan_result'].upper()} ({result['confidence_score']}% confidence)")
print(f"Trust Score: {result['trust_score']}")
print(f"Sources: {[(s['source'], s['confidence']) for s in result.get('source_detection', [])][:5]}")

details = result.get('forensic_details', {})
va = details.get('video_analysis', {})
print(f"\nFrame Analysis Avg Score: {va.get('frame_analysis', {}).get('average_score')}")
print(f"Frame Scores: {va.get('frame_analysis', {}).get('frame_scores')}")
print(f"Temporal Consistency: {va.get('temporal_consistency', {}).get('consistency_score')}")
print(f"Face Tracking - Faces: {va.get('face_tracking', {}).get('faces_detected')}")
print(f"Face Tracking - Anomalies: {va.get('face_tracking', {}).get('movement_anomalies')}")
print(f"Motion - Frozen Frames: {va.get('motion_analysis', {}).get('frozen_frames')}")
print(f"Motion - Avg Motion: {va.get('motion_analysis', {}).get('avg_motion')}")
