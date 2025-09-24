#!/usr/bin/env python3
"""
Fixed Main Script for Tara Person Following System

This version ensures bounding boxes and distance calculations are working.
"""

import cv2
import numpy as np
import logging
from tara_follow_system.person_detector import PersonDetector
from tara_follow_system.distance_estimator import DistanceEstimator
from tara_follow_system.movement_controller import MovementController
import os

# Suppress YOLO verbose output
os.environ['YOLO_VERBOSE'] = 'False'

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """Main function with fixed detection and drawing"""
    print("🎯 Tara Person Following - Fixed Version")
    print("=" * 50)
    
    # Initialize components with lower confidence threshold
    detector = PersonDetector(confidence_threshold=0.3)  # Lower threshold
    estimator = DistanceEstimator()
    movement_controller = MovementController()
    
    # Open camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Could not open camera")
        return
    
    print("✅ Camera opened successfully")
    print("🎮 Controls: F (follow), S (stop), Q (quit)")
    
    following = False
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
            
            # Get the largest person (target)
            target_person = detector.get_largest_person(tracked_persons)
            
            # Calculate distances for all persons
            distances = []
            for person in tracked_persons:
                distance_estimate = estimator.estimate_distance_combined(
                    person, frame.shape[1], frame.shape[0]
                )
                distances.append(distance_estimate.distance_meters)
            
            # Draw bounding boxes with distances
            frame = detector.draw_detections(frame, tracked_persons, distances)
            
            # Add system info
            info_text = f"Frame: {frame_count} | Persons: {len(tracked_persons)} | Following: {following}"
            cv2.putText(frame, info_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Add target person info if found
            if target_person and len(tracked_persons) > 0:
                target_distance = estimator.estimate_distance_combined(
                    target_person, frame.shape[1], frame.shape[0]
                )
                
                # Draw target person info box
                info_box_height = 100
                info_box_width = 280
                info_x = frame.shape[1] - info_box_width - 10
                info_y = 10
                
                # Background for info box
                cv2.rectangle(frame, 
                             (info_x, info_y), 
                             (info_x + info_box_width, info_y + info_box_height), 
                             (0, 0, 0), -1)
                cv2.rectangle(frame, 
                             (info_x, info_y), 
                             (info_x + info_box_width, info_y + info_box_height), 
                             (0, 255, 0), 2)
                
                # Target person info
                cv2.putText(frame, "TARGET PERSON", (info_x + 10, info_y + 25), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.putText(frame, f"Distance: {target_distance.distance_meters:.1f}m", 
                           (info_x + 10, info_y + 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.putText(frame, f"Confidence: {target_distance.confidence:.2f}", 
                           (info_x + 10, info_y + 70), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # Distance category
                distance_category = estimator.get_distance_category(target_distance.distance_meters)
                category_color = {
                    "too_close": (0, 0, 255),      # Red
                    "close": (0, 255, 255),        # Yellow
                    "optimal": (0, 255, 0),        # Green
                    "far": (255, 165, 0),          # Orange
                    "very_far": (255, 0, 0)        # Red
                }.get(distance_category, (255, 255, 255))
                
                cv2.putText(frame, f"Category: {distance_category.replace('_', ' ').title()}", 
                           (info_x + 10, info_y + 90), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, category_color, 2)
                
                # Movement control
                if following:
                    movement_command = movement_controller.update_target(
                        target_person, target_distance, frame.shape[1], frame.shape[0]
                    )
                    movement_controller.execute_command(movement_command)
            
            # Show frame
            cv2.imshow("Tara Person Following - Fixed", frame)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:  # Q or ESC
                break
            elif key == ord('f'):  # F for follow
                following = True
                movement_controller.start_following()
                print("🎯 Started following mode")
            elif key == ord('s'):  # S for stop
                following = False
                movement_controller.stop_following()
                print("🛑 Stopped following mode")
            
            # Print detection info every 30 frames
            if frame_count % 30 == 0:
                print(f"Frame {frame_count}: {len(tracked_persons)} persons detected")
                if target_person:
                    target_distance = estimator.estimate_distance_combined(
                        target_person, frame.shape[1], frame.shape[0]
                    )
                    print(f"  Target distance: {target_distance.distance_meters:.2f}m")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        detector.cleanup()
        movement_controller.cleanup()
        print("✅ System shutdown completed")

if __name__ == "__main__":
    main()
