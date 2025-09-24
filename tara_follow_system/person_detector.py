"""
Person Detection Module for Tara Robot

This module handles person detection and tracking using computer vision.
It provides bounding box information for distance estimation and movement control.
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict
import logging
from dataclasses import dataclass
from ultralytics import YOLO
import mediapipe as mp
import os

# Suppress YOLO verbose output globally
os.environ['YOLO_VERBOSE'] = 'False'

@dataclass
class PersonBoundingBox:
    """Data class for person bounding box information"""
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float
    person_id: Optional[int] = None
    
    @property
    def center(self) -> Tuple[int, int]:
        """Get center point of bounding box"""
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)
    
    @property
    def width(self) -> int:
        """Get width of bounding box"""
        return self.x2 - self.x1
    
    @property
    def height(self) -> int:
        """Get height of bounding box"""
        return self.y2 - self.y1
    
    @property
    def area(self) -> int:
        """Get area of bounding box"""
        return self.width * self.height

class PersonDetector:
    """
    Person detection and tracking using YOLO and MediaPipe
    
    This class provides methods to:
    1. Detect people in video frames
    2. Track detected people across frames
    3. Handle person loss scenarios
    4. Provide bounding box information for distance estimation
    """
    
    def __init__(self, 
                 model_path: str = "yolov8n.pt",
                 confidence_threshold: float = 0.5,
                 tracking_enabled: bool = True):
        """
        Initialize person detector
        
        Args:
            model_path: Path to YOLO model weights
            confidence_threshold: Minimum confidence for person detection
            tracking_enabled: Whether to enable person tracking
        """
        self.confidence_threshold = confidence_threshold
        self.tracking_enabled = tracking_enabled
        
        # Initialize YOLO model with verbose=False to suppress logs
        try:
            self.yolo_model = YOLO(model_path)
            # Suppress YOLO verbose output
            self.yolo_model.verbose = False
            logging.info(f"YOLO model loaded successfully from {model_path}")
        except Exception as e:
            logging.error(f"Failed to load YOLO model: {e}")
            raise
        
        # Initialize MediaPipe for pose detection (backup)
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        
        # Tracking variables
        self.tracked_persons = {}  # person_id -> PersonBoundingBox
        self.next_person_id = 1
        self.max_disappeared = 30  # frames before considering person lost
        self.disappeared_count = {}  # person_id -> count
        
        # Person class ID in COCO dataset
        self.PERSON_CLASS_ID = 0
        
        logging.info("PersonDetector initialized successfully")
    
    def detect_persons(self, frame: np.ndarray) -> List[PersonBoundingBox]:
        """
        Detect persons in a video frame
        
        Args:
            frame: Input video frame (BGR format)
            
        Returns:
            List of PersonBoundingBox objects for detected persons
        """
        try:
            # Run YOLO inference with verbose=False to suppress logs
            results = self.yolo_model(frame, conf=self.confidence_threshold, verbose=False)
            
            persons = []
            
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # Check if detection is a person
                        if int(box.cls) == self.PERSON_CLASS_ID:
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                            confidence = float(box.conf[0])
                            
                            person_bbox = PersonBoundingBox(
                                x1=x1, y1=y1, x2=x2, y2=y2,
                                confidence=confidence
                            )
                            persons.append(person_bbox)
            
            return persons
            
        except Exception as e:
            logging.error(f"Error in person detection: {e}")
            return []
    
    def track_persons(self, 
                     frame: np.ndarray, 
                     detected_persons: List[PersonBoundingBox]) -> List[PersonBoundingBox]:
        """
        Track detected persons across frames
        
        Args:
            frame: Current video frame
            detected_persons: List of newly detected persons
            
        Returns:
            List of PersonBoundingBox objects with tracking IDs
        """
        if not self.tracking_enabled:
            # Assign temporary IDs if tracking is disabled
            for i, person in enumerate(detected_persons):
                person.person_id = i
            return detected_persons
        
        # Update disappeared count for existing tracked persons
        for person_id in list(self.disappeared_count.keys()):
            self.disappeared_count[person_id] += 1
            
            # Remove person if disappeared too long
            if self.disappeared_count[person_id] > self.max_disappeared:
                if person_id in self.tracked_persons:
                    del self.tracked_persons[person_id]
                del self.disappeared_count[person_id]
        
        # Assign IDs to new detections
        tracked_persons = []
        
        for detected_person in detected_persons:
            person_id = self._assign_person_id(detected_person)
            detected_person.person_id = person_id
            
            # Update tracking information
            self.tracked_persons[person_id] = detected_person
            self.disappeared_count[person_id] = 0
            
            tracked_persons.append(detected_person)
        
        return tracked_persons
    
    def _assign_person_id(self, detected_person: PersonBoundingBox) -> int:
        """
        Assign ID to detected person based on proximity to existing tracked persons
        
        Args:
            detected_person: Newly detected person
            
        Returns:
            Person ID (existing or new)
        """
        if not self.tracked_persons:
            return self.next_person_id
        
        # Find closest existing person
        min_distance = float('inf')
        closest_id = None
        
        for person_id, tracked_person in self.tracked_persons.items():
            # Calculate distance between centers
            center1 = detected_person.center
            center2 = tracked_person.center
            distance = np.sqrt((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)
            
            if distance < min_distance:
                min_distance = distance
                closest_id = person_id
        
        # If closest person is within threshold, use their ID
        if min_distance < 100:  # pixels
            return closest_id
        
        # Otherwise, assign new ID
        self.next_person_id += 1
        return self.next_person_id
    
    def get_largest_person(self, persons: List[PersonBoundingBox]) -> Optional[PersonBoundingBox]:
        """
        Get the largest (closest) person from the detection list
        
        Args:
            persons: List of detected persons
            
        Returns:
            PersonBoundingBox of the largest person, or None if no persons detected
        """
        if not persons:
            return None
        
        # Return person with largest bounding box area
        return max(persons, key=lambda p: p.area)
    
    def draw_detections(self, 
                       frame: np.ndarray, 
                       persons: List[PersonBoundingBox],
                       distances: List[float] = None) -> np.ndarray:
        """
        Draw bounding boxes and information on frame
        
        Args:
            frame: Input frame
            persons: List of detected persons
            distances: Optional list of distance estimates for each person
            
        Returns:
            Frame with drawn bounding boxes and labels
        """
        frame_copy = frame.copy()
        
        for i, person in enumerate(persons):
            # Choose color based on distance (if available)
            if distances and i < len(distances):
                distance = distances[i]
                if distance < 1.0:
                    color = (0, 0, 255)  # Red for close
                elif distance < 2.0:
                    color = (0, 255, 255)  # Yellow for medium
                else:
                    color = (0, 255, 0)  # Green for far
            else:
                color = (0, 255, 0)  # Default green
            
            # Draw bounding box
            cv2.rectangle(frame_copy, 
                         (person.x1, person.y1), 
                         (person.x2, person.y2), 
                         color, 3)
            
            # Prepare label with distance information
            if distances and i < len(distances):
                distance = distances[i]
                label = f"Person {person.person_id}: {distance:.1f}m ({person.confidence:.2f})"
            else:
                label = f"Person {person.person_id}: {person.confidence:.2f}"
            
            if person.person_id is None:
                if distances and i < len(distances):
                    distance = distances[i]
                    label = f"Person: {distance:.1f}m ({person.confidence:.2f})"
                else:
                    label = f"Person: {person.confidence:.2f}"
            
            # Draw label with background
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            cv2.rectangle(frame_copy, 
                         (person.x1, person.y1 - 25), 
                         (person.x1 + label_size[0], person.y1), 
                         color, -1)
            
            cv2.putText(frame_copy, label, 
                       (person.x1, person.y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Draw center point
            center = person.center
            cv2.circle(frame_copy, center, 8, (255, 0, 0), -1)
            cv2.circle(frame_copy, center, 12, (255, 255, 255), 2)
        
        return frame_copy
    
    def is_person_centered(self, person: PersonBoundingBox, frame_width: int, frame_height: int) -> bool:
        """
        Check if person is roughly centered in the frame
        
        Args:
            person: PersonBoundingBox to check
            frame_width: Width of the frame
            frame_height: Height of the frame
            
        Returns:
            True if person is centered, False otherwise
        """
        center_x, center_y = person.center
        frame_center_x = frame_width // 2
        frame_center_y = frame_height // 2
        
        # Allow 30% deviation from center
        tolerance_x = frame_width * 0.3
        tolerance_y = frame_height * 0.3
        
        return (abs(center_x - frame_center_x) < tolerance_x and 
                abs(center_y - frame_center_y) < tolerance_y)
    
    def cleanup(self):
        """Clean up resources"""
        if hasattr(self, 'pose'):
            self.pose.close()
        logging.info("PersonDetector cleaned up")
