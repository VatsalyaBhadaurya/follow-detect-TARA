"""
Main Follow Person Task for Tara Robot

This module integrates all components to provide a complete person following system.
It handles the main task loop, coordinates between modules, and manages the overall behavior.
"""

import cv2
import numpy as np
import time
import logging
import threading
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .person_detector import PersonDetector, PersonBoundingBox
from .distance_estimator import DistanceEstimator, DistanceEstimate
from .voice_handler import VoiceCommandHandler, CommandType
from .movement_controller import MovementController, MovementState

class FollowTaskState(Enum):
    """Enumeration of follow task states"""
    IDLE = "idle"
    FOLLOWING = "following"
    SEARCHING = "searching"
    STOPPED = "stopped"
    ERROR = "error"

@dataclass
class FollowTaskConfig:
    """Configuration for the follow task"""
    # Camera settings
    camera_id: int = 0
    frame_width: int = 640
    frame_height: int = 480
    fps: int = 30
    
    # Detection settings
    confidence_threshold: float = 0.5
    tracking_enabled: bool = True
    
    # Distance settings
    safe_distance: float = 1.0
    min_distance: float = 0.5
    max_distance: float = 3.0
    
    # Movement settings
    max_linear_velocity: float = 0.5
    max_angular_velocity: float = 1.0
    
    # Voice settings
    voice_enabled: bool = True
    language: str = "en-US"
    
    # Display settings
    show_display: bool = True
    save_video: bool = False
    video_filename: str = "follow_task_output.avi"

class FollowPersonTask:
    """
    Main follow person task that coordinates all system components
    
    This class provides methods to:
    1. Initialize and coordinate all system modules
    2. Run the main task loop
    3. Handle voice commands
    4. Process video frames and detect persons
    5. Control robot movement based on person tracking
    6. Manage task state and error handling
    """
    
    def __init__(self, config: FollowTaskConfig = None):
        """
        Initialize follow person task
        
        Args:
            config: Configuration object for the task
        """
        self.config = config or FollowTaskConfig()
        
        # Initialize modules
        self.person_detector = PersonDetector(
            confidence_threshold=0.3,  # Lower threshold for better detection
            tracking_enabled=self.config.tracking_enabled
        )
        
        self.distance_estimator = DistanceEstimator(
            reference_height_meters=1.7  # Average human height
        )
        
        self.movement_controller = MovementController(
            max_linear_velocity=self.config.max_linear_velocity,
            max_angular_velocity=self.config.max_angular_velocity,
            safe_distance=self.config.safe_distance,
            min_distance=self.config.min_distance,
            max_distance=self.config.max_distance
        )
        
        # Initialize voice handler if enabled
        self.voice_handler = None
        if self.config.voice_enabled:
            try:
                self.voice_handler = VoiceCommandHandler(language=self.config.language)
                # Test if voice handler works
                if not self.voice_handler.test_microphone():
                    logging.warning("Voice handler failed, voice commands disabled")
                    self.voice_handler = None
                else:
                    self._setup_voice_callbacks()
            except Exception as e:
                logging.error(f"Voice handler initialization failed: {e}")
                logging.info("Voice commands disabled")
                self.voice_handler = None
        
        # Task state
        self.current_state = FollowTaskState.IDLE
        self.is_running = False
        self.target_person = None
        
        # Video capture
        self.cap = None
        self.video_writer = None
        
        # Performance tracking
        self.frame_count = 0
        self.start_time = None
        self.fps_counter = 0
        self.last_fps_time = time.time()
        
        # Error handling
        self.error_count = 0
        self.max_errors = 10
        
        logging.info("FollowPersonTask initialized successfully")
    
    def _setup_voice_callbacks(self):
        """Setup voice command callbacks"""
        if not self.voice_handler:
            return
        
        self.voice_handler.register_callback(CommandType.FOLLOW_ME, self._on_follow_command)
        self.voice_handler.register_callback(CommandType.STOP, self._on_stop_command)
    
    def _on_follow_command(self):
        """Handle 'follow me' voice command"""
        logging.info("Voice command received: Follow me")
        self.start_following()
    
    def _on_stop_command(self):
        """Handle 'stop' voice command"""
        logging.info("Voice command received: Stop")
        self.stop_following()
    
    def initialize(self) -> bool:
        """
        Initialize the task (camera, video writer, etc.)
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Initialize camera
            self.cap = cv2.VideoCapture(self.config.camera_id)
            if not self.cap.isOpened():
                logging.error(f"Failed to open camera {self.config.camera_id}")
                return False
            
            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.frame_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.frame_height)
            self.cap.set(cv2.CAP_PROP_FPS, self.config.fps)
            
            # Initialize video writer if needed
            if self.config.save_video:
                fourcc = cv2.VideoWriter_fourcc(*'XVID')
                self.video_writer = cv2.VideoWriter(
                    self.config.video_filename,
                    fourcc,
                    self.config.fps,
                    (self.config.frame_width, self.config.frame_height)
                )
            
            # Test voice handler if enabled
            if self.voice_handler:
                if not self.voice_handler.test_microphone():
                    logging.warning("Microphone test failed, voice commands may not work")
            
            logging.info("Task initialization completed successfully")
            return True
            
        except Exception as e:
            logging.error(f"Task initialization failed: {e}")
            return False
    
    def start_following(self):
        """Start following mode"""
        if self.current_state == FollowTaskState.FOLLOWING:
            logging.warning("Already in following mode")
            return
        
        self.current_state = FollowTaskState.FOLLOWING
        self.movement_controller.start_following()
        
        logging.info("Started following mode")
    
    def stop_following(self):
        """Stop following mode"""
        self.current_state = FollowTaskState.STOPPED
        self.movement_controller.stop_following()
        self.target_person = None
        
        logging.info("Stopped following mode")
    
    def run(self):
        """
        Main task loop
        
        This method runs the complete follow person task:
        1. Captures video frames
        2. Detects and tracks persons
        3. Estimates distances
        4. Controls robot movement
        5. Handles voice commands
        6. Updates display
        """
        if not self.initialize():
            logging.error("Failed to initialize task")
            return
        
        # Start voice handler if enabled
        if self.voice_handler:
            self.voice_handler.start_listening()
        
        self.is_running = True
        self.start_time = time.time()
        
        logging.info("Starting follow person task loop")
        
        try:
            while self.is_running:
                # Capture frame
                ret, frame = self.cap.read()
                if not ret:
                    logging.error("Failed to capture frame")
                    self.error_count += 1
                    if self.error_count > self.max_errors:
                        logging.error("Too many capture errors, stopping task")
                        break
                    continue
                
                # Process frame
                self._process_frame(frame)
                
                # Handle voice commands
                if self.voice_handler:
                    self._handle_voice_commands()
                
                # Update display
                if self.config.show_display:
                    self._update_display(frame)
                
                # Save video if enabled
                if self.video_writer:
                    self.video_writer.write(frame)
                
                # Update performance metrics
                self._update_performance_metrics()
                
                # Check for exit conditions
                if self.config.show_display:
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q') or key == 27:  # 'q' or ESC
                        break
                    elif key == ord('f'):  # 'f' for follow
                        self.start_following()
                    elif key == ord('s'):  # 's' for stop
                        self.stop_following()
                
        except KeyboardInterrupt:
            logging.info("Task interrupted by user")
        except Exception as e:
            logging.error(f"Error in task loop: {e}")
        finally:
            self._cleanup()
    
    def _process_frame(self, frame: np.ndarray):
        """
        Process a single video frame
        
        Args:
            frame: Input video frame
        """
        try:
            # Detect persons in frame
            detected_persons = self.person_detector.detect_persons(frame)
            
            # Track persons if tracking is enabled
            tracked_persons = self.person_detector.track_persons(frame, detected_persons)
            
            # Optional debug output (commented out for clean output)
            # if self.frame_count % 30 == 0:
            #     logging.info(f"Frame {self.frame_count}: {len(detected_persons)} raw detections, "
            #                f"{len(tracked_persons)} tracked persons")
            
            # Get the target person (largest/closest)
            target_person = self.person_detector.get_largest_person(tracked_persons)
            
            if target_person:
                self.target_person = target_person
                
                # Estimate distance to target person
                distance_estimate = self.distance_estimator.estimate_distance_combined(
                    target_person, 
                    frame.shape[1],  # frame width
                    frame.shape[0]   # frame height
                )
                
                # Optional debug output (commented out for clean output)
                # if self.frame_count % 30 == 0:
                #     logging.info(f"Target person found: ID={target_person.person_id}, "
                #                f"distance={distance_estimate.distance_meters:.2f}m, "
                #                f"confidence={distance_estimate.confidence:.2f}")
                
                # Update movement based on target
                if self.current_state == FollowTaskState.FOLLOWING:
                    movement_command = self.movement_controller.update_target(
                        target_person,
                        distance_estimate,
                        frame.shape[1],  # frame width
                        frame.shape[0]   # frame height
                    )
                    self.movement_controller.execute_command(movement_command)
                    
                    # Update state based on distance
                    distance_category = self.distance_estimator.get_distance_category(
                        distance_estimate.distance_meters
                    )
                    
                    if distance_category == "very_far":
                        self.current_state = FollowTaskState.SEARCHING
                        self.movement_controller.start_search_behavior()
                
                # Draw detections on frame with distance information
                distances = []
                for person in tracked_persons:
                    person_distance = self.distance_estimator.estimate_distance_combined(
                        person, frame.shape[1], frame.shape[0]
                    )
                    distances.append(person_distance.distance_meters)
                
                # Draw bounding boxes with distances
                frame = self.person_detector.draw_detections(frame, tracked_persons, distances)
                
                # Draw additional distance information for target person
                self._draw_target_distance_info(frame, distance_estimate, target_person)
            
            else:
                # No person detected - draw empty frame
                frame = self.person_detector.draw_detections(frame, [])
                
                if self.current_state == FollowTaskState.FOLLOWING:
                    self.current_state = FollowTaskState.SEARCHING
                    self.movement_controller.start_search_behavior()
                
                # Update search behavior
                if self.current_state == FollowTaskState.SEARCHING:
                    search_command = self.movement_controller.update_search_behavior()
                    self.movement_controller.execute_command(search_command)
            
            # Reset error count on successful processing
            self.error_count = 0
            
        except Exception as e:
            logging.error(f"Error processing frame: {e}")
            self.error_count += 1
    
    def _handle_voice_commands(self):
        """Handle pending voice commands"""
        if not self.voice_handler:
            return
        
        command = self.voice_handler.get_latest_command(timeout=0.01)
        if command:
            if command == CommandType.FOLLOW_ME:
                self.start_following()
            elif command == CommandType.STOP:
                self.stop_following()
    
    def _draw_target_distance_info(self, 
                                  frame: np.ndarray, 
                                  distance_estimate: DistanceEstimate,
                                  person: PersonBoundingBox):
        """
        Draw target person distance information on frame
        
        Args:
            frame: Video frame to draw on
            distance_estimate: Distance estimate information
            person: Person bounding box
        """
        # Draw target person info box
        info_box_height = 120
        info_box_width = 300
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
                     (255, 255, 255), 2)
        
        # Draw target person information
        target_text = "TARGET PERSON"
        cv2.putText(frame, target_text, (info_x + 10, info_y + 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        distance_text = f"Distance: {distance_estimate.distance_meters:.1f}m"
        confidence_text = f"Confidence: {distance_estimate.confidence:.2f}"
        method_text = f"Method: {distance_estimate.method}"
        
        cv2.putText(frame, distance_text, (info_x + 10, info_y + 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, confidence_text, (info_x + 10, info_y + 70), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, method_text, (info_x + 10, info_y + 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Draw distance category
        distance_category = self.distance_estimator.get_distance_category(
            distance_estimate.distance_meters
        )
        category_color = {
            "too_close": (0, 0, 255),      # Red
            "close": (0, 255, 255),        # Yellow
            "optimal": (0, 255, 0),        # Green
            "far": (255, 165, 0),          # Orange
            "very_far": (255, 0, 0)        # Red
        }.get(distance_category, (255, 255, 255))
        
        category_text = f"Category: {distance_category.replace('_', ' ').title()}"
        cv2.putText(frame, category_text, (info_x + 10, info_y + 110), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, category_color, 2)
        
        # Draw state information at top
        state_text = f"State: {self.current_state.value.upper()}"
        cv2.putText(frame, state_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    
    def _update_display(self, frame: np.ndarray):
        """
        Update display with current frame
        
        Args:
            frame: Video frame to display
        """
        # Add instructions
        instructions = [
            "Controls:",
            "F - Start following",
            "S - Stop following", 
            "Q/ESC - Quit"
        ]
        
        y_offset = frame.shape[0] - 80
        for i, instruction in enumerate(instructions):
            cv2.putText(frame, instruction, (10, y_offset + i * 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Display frame
        cv2.imshow("Tara Follow Person Task", frame)
    
    def _update_performance_metrics(self):
        """Update performance metrics"""
        self.frame_count += 1
        self.fps_counter += 1
        
        current_time = time.time()
        if current_time - self.last_fps_time >= 1.0:
            fps = self.fps_counter / (current_time - self.last_fps_time)
            logging.debug(f"FPS: {fps:.1f}")
            self.fps_counter = 0
            self.last_fps_time = current_time
    
    def _cleanup(self):
        """Clean up resources"""
        logging.info("Cleaning up task resources...")
        
        self.is_running = False
        
        # Stop voice handler
        if self.voice_handler:
            self.voice_handler.cleanup()
        
        # Stop movement
        self.movement_controller.cleanup()
        
        # Clean up person detector
        self.person_detector.cleanup()
        
        # Release camera
        if self.cap:
            self.cap.release()
        
        # Release video writer
        if self.video_writer:
            self.video_writer.release()
        
        # Close display
        if self.config.show_display:
            cv2.destroyAllWindows()
        
        # Calculate and log performance stats
        if self.start_time:
            total_time = time.time() - self.start_time
            avg_fps = self.frame_count / total_time if total_time > 0 else 0
            logging.info(f"Task completed. Total frames: {self.frame_count}, "
                        f"Total time: {total_time:.2f}s, Average FPS: {avg_fps:.2f}")
        
        logging.info("Task cleanup completed")
    
    def get_status(self) -> dict:
        """
        Get current task status
        
        Returns:
            Dictionary with task status information
        """
        return {
            "state": self.current_state.value,
            "is_running": self.is_running,
            "target_person": self.target_person.person_id if self.target_person else None,
            "frame_count": self.frame_count,
            "error_count": self.error_count,
            "movement_state": self.movement_controller.get_current_state().value
        }
