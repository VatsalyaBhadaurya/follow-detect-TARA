#!/usr/bin/env python3
"""
Debug Person Detection and Bounding Box Drawing

This script helps debug why bounding boxes and distance calculations aren't showing.
"""

import cv2
import numpy as np
import logging
from tara_follow_system.person_detector import PersonDetector
from tara_follow_system.distance_estimator import DistanceEstimator

# Setup logging
logging.basicConfig(level=logging.DEBUG)

def debug_person_detection():
    """Debug person detection and drawing"""
    print("🔍 Debugging Person Detection and Bounding Boxes")
    print("=" * 50)
    
    # Initialize components
    detector = PersonDetector(confidence_threshold=0.3)  # Lower threshold for easier detection
    estimator = DistanceEstimator()
    
    # Open camera
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Error: Could not open camera")
        return
    
    print("✅ Camera opened successfully")
    print("Press 'q' to quit, 'd' to debug detection")
    
    frame_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Failed to capture frame")
                break
            
            frame_count += 1
            
            # Detect persons
            persons = detector.detect_persons(frame)
            tracked_persons = detector.track_persons(frame, persons)
            
            print(f"\nFrame {frame_count}:")
            print(f"  Raw detections: {len(persons)}")
            print(f"  Tracked persons: {len(tracked_persons)}")
            
            # Calculate distances for each person
            distances = []
            for person in tracked_persons:
                distance_estimate = estimator.estimate_distance_combined(
                    person, frame.shape[1], frame.shape[0]
                )
                distances.append(distance_estimate.distance_meters)
                print(f"  Person {person.person_id}: {distance_estimate.distance_meters:.2f}m "
                      f"(confidence: {person.confidence:.2f}, method: {distance_estimate.method})")
            
            # Draw detections with distances
            frame_with_boxes = detector.draw_detections(frame, tracked_persons, distances)
            
            # Add debug info
            debug_text = f"Frame: {frame_count}, Persons: {len(tracked_persons)}"
            cv2.putText(frame_with_boxes, debug_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Show frame
            cv2.imshow("Debug Person Detection", frame_with_boxes)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('d'):
                print("\n🔍 Debug Info:")
                print(f"  Frame size: {frame.shape}")
                print(f"  Camera properties:")
                print(f"    Width: {cap.get(cv2.CAP_PROP_FRAME_WIDTH)}")
                print(f"    Height: {cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")
                print(f"    FPS: {cap.get(cv2.CAP_PROP_FPS)}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        detector.cleanup()
        print("✅ Debug session completed")

if __name__ == "__main__":
    debug_person_detection()
