#!/usr/bin/env python3
"""
Simple YOLO Detection Test

Test if YOLO is detecting persons correctly.
"""

import cv2
import numpy as np
from ultralytics import YOLO
import os

# Suppress YOLO verbose output
os.environ['YOLO_VERBOSE'] = 'False'

def test_yolo_detection():
    """Test YOLO person detection"""
    print("🔍 Testing YOLO Person Detection")
    print("=" * 40)
    
    # Load YOLO model
    try:
        model = YOLO("yolov8n.pt")
        model.verbose = False
        print("✅ YOLO model loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load YOLO model: {e}")
        return
    
    # Open camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Could not open camera")
        return
    
    print("✅ Camera opened")
    print("Press 'q' to quit")
    
    frame_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Run YOLO detection
            results = model(frame, conf=0.3, verbose=False)
            
            # Count persons
            person_count = 0
            for result in results:
                if result.boxes is not None:
                    for box in result.boxes:
                        if int(box.cls) == 0:  # Person class
                            person_count += 1
                            
                            # Draw bounding box
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                            confidence = float(box.conf[0])
                            
                            # Draw rectangle
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                            
                            # Draw label
                            label = f"Person: {confidence:.2f}"
                            cv2.putText(frame, label, (x1, y1 - 10), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Add frame info
            info_text = f"Frame: {frame_count}, Persons: {person_count}"
            cv2.putText(frame, info_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            cv2.imshow("YOLO Detection Test", frame)
            
            if frame_count % 30 == 0:  # Print every 30 frames
                print(f"Frame {frame_count}: {person_count} persons detected")
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("✅ Test completed")

if __name__ == "__main__":
    test_yolo_detection()
