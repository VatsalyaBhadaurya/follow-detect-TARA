#!/usr/bin/env python3
"""
Example Usage of Tara Person Following System

This script demonstrates how to use individual components of the system
for custom implementations and testing.
"""

import cv2
import numpy as np
import time
import logging
from tara_follow_system.person_detector import PersonDetector
from tara_follow_system.distance_estimator import DistanceEstimator
from tara_follow_system.voice_handler import VoiceCommandHandler, CommandType
from tara_follow_system.movement_controller import MovementController

# Setup logging
logging.basicConfig(level=logging.INFO)

def example_person_detection():
    """Example of person detection and tracking"""
    print("=== Person Detection Example ===")
    
    # Initialize person detector
    detector = PersonDetector(confidence_threshold=0.5)
    
    # Open camera
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open camera")
        return
    
    print("Person detection running. Press 'q' to quit.")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Detect persons
            persons = detector.detect_persons(frame)
            
            # Track persons
            tracked_persons = detector.track_persons(frame, persons)
            
            # Get largest person
            largest_person = detector.get_largest_person(tracked_persons)
            
            # Draw detections
            frame = detector.draw_detections(frame, tracked_persons)
            
            # Display info
            if largest_person:
                print(f"Largest person: ID={largest_person.person_id}, "
                      f"Area={largest_person.area}, Center={largest_person.center}")
            
            cv2.imshow("Person Detection", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        detector.cleanup()

def example_distance_estimation():
    """Example of distance estimation"""
    print("=== Distance Estimation Example ===")
    
    # Initialize distance estimator
    estimator = DistanceEstimator()
    
    # Open camera
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open camera")
        return
    
    # Initialize person detector
    detector = PersonDetector(confidence_threshold=0.5)
    
    print("Distance estimation running. Press 'q' to quit.")
    print("Commands: 'c' to add calibration point, 's' to save calibration")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Detect persons
            persons = detector.detect_persons(frame)
            tracked_persons = detector.track_persons(frame, persons)
            largest_person = detector.get_largest_person(tracked_persons)
            
            if largest_person:
                # Estimate distance using different methods
                size_estimate = estimator.estimate_distance_size_based(
                    largest_person, frame.shape[0]
                )
                position_estimate = estimator.estimate_distance_position_based(
                    largest_person, frame.shape[1], frame.shape[0]
                )
                combined_estimate = estimator.estimate_distance_combined(
                    largest_person, frame.shape[1], frame.shape[0]
                )
                
                # Draw distance info
                cv2.putText(frame, f"Size: {size_estimate.distance_meters:.2f}m", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                cv2.putText(frame, f"Position: {position_estimate.distance_meters:.2f}m", 
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, f"Combined: {combined_estimate.distance_meters:.2f}m", 
                           (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                print(f"Distance estimates - Size: {size_estimate.distance_meters:.2f}m, "
                      f"Position: {position_estimate.distance_meters:.2f}m, "
                      f"Combined: {combined_estimate.distance_meters:.2f}m")
            
            # Draw detections
            frame = detector.draw_detections(frame, tracked_persons)
            cv2.imshow("Distance Estimation", frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('c') and largest_person:
                # Add calibration point (you would enter actual distance)
                actual_distance = float(input("Enter actual distance in meters: "))
                estimator.add_calibration_point(largest_person, actual_distance, 
                                              frame.shape[1], frame.shape[0])
                print(f"Added calibration point: {actual_distance}m")
            elif key == ord('s'):
                estimator.calibrate_from_data()
                estimator.save_calibration("example_calibration.json")
                print("Calibration saved")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        detector.cleanup()

def example_voice_commands():
    """Example of voice command recognition"""
    print("=== Voice Commands Example ===")
    
    # Initialize voice handler
    voice_handler = VoiceCommandHandler()
    
    # Register callbacks
    def on_follow():
        print("Follow command received!")
    
    def on_stop():
        print("Stop command received!")
    
    voice_handler.register_callback(CommandType.FOLLOW_ME, on_follow)
    voice_handler.register_callback(CommandType.STOP, on_stop)
    
    # Test microphone
    if not voice_handler.test_microphone():
        print("Microphone test failed. Voice commands may not work.")
        return
    
    print("Voice commands running. Say 'follow me' or 'stop'.")
    print("Press Ctrl+C to quit.")
    
    try:
        voice_handler.start_listening()
        
        while True:
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("Stopping voice commands...")
    
    finally:
        voice_handler.cleanup()

def example_movement_control():
    """Example of movement control simulation"""
    print("=== Movement Control Example ===")
    
    # Initialize movement controller
    movement_controller = MovementController(safe_distance=1.0)
    
    # Simulate person following
    print("Simulating person following...")
    
    # Start following
    movement_controller.start_following()
    
    # Simulate different scenarios
    scenarios = [
        {"distance": 2.0, "angle_error": 0.0, "description": "Person far and centered"},
        {"distance": 1.5, "angle_error": 0.1, "description": "Person closer, slight left"},
        {"distance": 1.0, "angle_error": 0.0, "description": "Person at safe distance"},
        {"distance": 0.8, "angle_error": -0.1, "description": "Person too close, slight right"},
        {"distance": 0.3, "angle_error": 0.0, "description": "Emergency stop scenario"},
    ]
    
    for i, scenario in enumerate(scenarios):
        print(f"\nScenario {i+1}: {scenario['description']}")
        print(f"  Distance: {scenario['distance']}m, Angle error: {scenario['angle_error']}")
        
        # Create mock person bbox and distance estimate
        from tara_follow_system.person_detector import PersonBoundingBox
        from tara_follow_system.distance_estimator import DistanceEstimate
        
        # Mock bounding box (person centered with some offset)
        center_x = 320 + int(scenario['angle_error'] * 100)
        mock_bbox = PersonBoundingBox(
            x1=center_x - 50, y1=200, x2=center_x + 50, y2=400,
            confidence=0.9
        )
        
        mock_distance = DistanceEstimate(
            distance_meters=scenario['distance'],
            confidence=0.8,
            method='combined',
            bounding_box_area=10000,
            person_height_pixels=200
        )
        
        # Update movement
        command = movement_controller.update_target(
            mock_bbox, mock_distance, 640, 480
        )
        
        print(f"  Movement command: linear={command.linear_velocity:.3f} m/s, "
              f"angular={command.angular_velocity:.3f} rad/s")
        print(f"  State: {movement_controller.get_current_state().value}")
        
        time.sleep(1)
    
    # Stop following
    movement_controller.stop_following()
    print("\nStopped following.")

def main():
    """Main function to run examples"""
    print("Tara Person Following System - Examples")
    print("======================================")
    
    while True:
        print("\nAvailable examples:")
        print("1. Person Detection")
        print("2. Distance Estimation")
        print("3. Voice Commands")
        print("4. Movement Control")
        print("5. Exit")
        
        choice = input("\nSelect example (1-5): ").strip()
        
        if choice == '1':
            example_person_detection()
        elif choice == '2':
            example_distance_estimation()
        elif choice == '3':
            example_voice_commands()
        elif choice == '4':
            example_movement_control()
        elif choice == '5':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please select 1-5.")

if __name__ == "__main__":
    main()
