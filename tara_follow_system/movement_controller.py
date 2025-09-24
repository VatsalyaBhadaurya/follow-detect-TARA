"""
Movement Controller for Tara Robot

This module handles robot movement control for person following.
It implements smooth following behavior with safe distance maintenance.
"""

import numpy as np
import time
import logging
from typing import Tuple, Optional, Dict
from dataclasses import dataclass
from enum import Enum
import threading

class MovementState(Enum):
    """Enumeration of movement states"""
    STOPPED = "stopped"
    FOLLOWING = "following"
    SEARCHING = "searching"
    APPROACHING = "approaching"
    BACKING_UP = "backing_up"

@dataclass
class MovementCommand:
    """Data class for movement commands"""
    linear_velocity: float  # m/s (forward/backward)
    angular_velocity: float  # rad/s (left/right)
    duration: float  # seconds
    priority: int = 1  # 1=normal, 2=high (stop commands)

class PIDController:
    """
    Proportional-Integral-Derivative controller for smooth movement
    """
    
    def __init__(self, kp: float = 1.0, ki: float = 0.0, kd: float = 0.1):
        """
        Initialize PID controller
        
        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        
        self.previous_error = 0.0
        self.integral = 0.0
        self.last_time = time.time()
    
    def compute(self, setpoint: float, current_value: float) -> float:
        """
        Compute PID output
        
        Args:
            setpoint: Desired value
            current_value: Current measured value
            
        Returns:
            PID controller output
        """
        current_time = time.time()
        dt = current_time - self.last_time
        
        if dt <= 0:
            dt = 0.01  # Prevent division by zero
        
        # Calculate error
        error = setpoint - current_value
        
        # Proportional term
        proportional = self.kp * error
        
        # Integral term
        self.integral += error * dt
        integral = self.ki * self.integral
        
        # Derivative term
        derivative = self.kd * (error - self.previous_error) / dt
        
        # Calculate output
        output = proportional + integral + derivative
        
        # Update for next iteration
        self.previous_error = error
        self.last_time = current_time
        
        return output
    
    def reset(self):
        """Reset PID controller state"""
        self.previous_error = 0.0
        self.integral = 0.0
        self.last_time = time.time()

class MovementController:
    """
    Movement controller for person following behavior
    
    This class provides methods to:
    1. Control robot movement based on person position and distance
    2. Maintain safe following distance
    3. Implement smooth movement with PID control
    4. Handle search behavior when person is lost
    """
    
    def __init__(self, 
                 max_linear_velocity: float = 0.5,  # m/s
                 max_angular_velocity: float = 1.0,  # rad/s
                 safe_distance: float = 1.0,  # meters
                 min_distance: float = 0.5,  # meters
                 max_distance: float = 3.0,  # meters
                 search_angular_velocity: float = 0.3):  # rad/s
        """
        Initialize movement controller
        
        Args:
            max_linear_velocity: Maximum forward/backward speed
            max_angular_velocity: Maximum turning speed
            safe_distance: Optimal following distance
            min_distance: Minimum safe distance
            max_distance: Maximum following distance
            search_angular_velocity: Angular velocity during search
        """
        self.max_linear_velocity = max_linear_velocity
        self.max_angular_velocity = max_angular_velocity
        self.safe_distance = safe_distance
        self.min_distance = min_distance
        self.max_distance = max_distance
        self.search_angular_velocity = search_angular_velocity
        
        # PID controllers
        self.distance_pid = PIDController(kp=0.8, ki=0.1, kd=0.2)
        self.angle_pid = PIDController(kp=1.2, ki=0.0, kd=0.3)
        
        # State management
        self.current_state = MovementState.STOPPED
        self.is_following = False
        self.target_person_id = None
        
        # Movement parameters
        self.current_velocity = (0.0, 0.0)  # (linear, angular)
        self.last_command_time = time.time()
        
        # Search behavior
        self.search_direction = 1  # 1 for clockwise, -1 for counterclockwise
        self.search_start_time = None
        
        # Safety parameters
        self.emergency_stop_distance = 0.3  # meters
        self.command_timeout = 2.0  # seconds
        
        # Threading for continuous movement
        self.movement_thread: Optional[threading.Thread] = None
        self.is_running = False
        
        logging.info("MovementController initialized successfully")
    
    def start_following(self, person_id: Optional[int] = None):
        """
        Start following mode
        
        Args:
            person_id: ID of person to follow (None for any person)
        """
        self.is_following = True
        self.target_person_id = person_id
        self.current_state = MovementState.FOLLOWING
        
        # Reset PID controllers
        self.distance_pid.reset()
        self.angle_pid.reset()
        
        logging.info(f"Started following mode for person {person_id}")
    
    def stop_following(self):
        """Stop following mode and halt movement"""
        self.is_following = False
        self.target_person_id = None
        self.current_state = MovementState.STOPPED
        
        # Stop immediately
        self._execute_movement_command(0.0, 0.0)
        
        logging.info("Stopped following mode")
    
    def update_target(self, 
                     person_bbox, 
                     distance_estimate,
                     frame_width: int, 
                     frame_height: int) -> MovementCommand:
        """
        Update movement based on target person position and distance
        
        Args:
            person_bbox: PersonBoundingBox of target person
            distance_estimate: DistanceEstimate object
            frame_width: Width of video frame
            frame_height: Height of video frame
            
        Returns:
            MovementCommand for robot movement
        """
        if not self.is_following:
            return MovementCommand(0.0, 0.0, 0.0)
        
        try:
            # Get person position in frame
            person_center_x, person_center_y = person_bbox.center
            frame_center_x = frame_width // 2
            frame_center_y = frame_height // 2
            
            # Calculate angular error (how far off center)
            angular_error = (person_center_x - frame_center_x) / frame_width
            
            # Calculate distance error
            distance_error = distance_estimate.distance_meters - self.safe_distance
            
            # Safety check - emergency stop if too close
            if distance_estimate.distance_meters < self.emergency_stop_distance:
                logging.warning("Emergency stop - person too close!")
                return MovementCommand(0.0, 0.0, 0.0, priority=2)
            
            # PID control for distance
            linear_velocity = self.distance_pid.compute(0.0, distance_error)
            
            # PID control for angle
            angular_velocity = self.angle_pid.compute(0.0, angular_error)
            
            # Limit velocities
            linear_velocity = np.clip(linear_velocity, -self.max_linear_velocity, self.max_linear_velocity)
            angular_velocity = np.clip(angular_velocity, -self.max_angular_velocity, self.max_angular_velocity)
            
            # Apply smooth acceleration/deceleration
            linear_velocity, angular_velocity = self._apply_smooth_control(linear_velocity, angular_velocity)
            
            # Update state based on distance
            self._update_movement_state(distance_estimate.distance_meters)
            
            return MovementCommand(
                linear_velocity=linear_velocity,
                angular_velocity=angular_velocity,
                duration=0.1
            )
            
        except Exception as e:
            logging.error(f"Error updating movement target: {e}")
            return MovementCommand(0.0, 0.0, 0.0)
    
    def start_search_behavior(self):
        """Start search behavior when person is lost"""
        self.current_state = MovementState.SEARCHING
        self.search_start_time = time.time()
        self.search_direction = 1  # Start with clockwise
        
        logging.info("Started search behavior")
    
    def update_search_behavior(self) -> MovementCommand:
        """
        Update search behavior movement
        
        Returns:
            MovementCommand for search movement
        """
        if self.current_state != MovementState.SEARCHING:
            return MovementCommand(0.0, 0.0, 0.0)
        
        # Simple search pattern: rotate back and forth
        search_time = time.time() - self.search_start_time if self.search_start_time else 0
        
        # Change direction every 2 seconds
        if search_time > 2.0:
            self.search_direction *= -1
            self.search_start_time = time.time()
        
        # Return search movement command
        return MovementCommand(
            linear_velocity=0.0,
            angular_velocity=self.search_angular_velocity * self.search_direction,
            duration=0.1
        )
    
    def _apply_smooth_control(self, 
                            target_linear: float, 
                            target_angular: float) -> Tuple[float, float]:
        """
        Apply smooth acceleration/deceleration to movement commands
        
        Args:
            target_linear: Target linear velocity
            target_angular: Target angular velocity
            
        Returns:
            Smoothed (linear, angular) velocities
        """
        # Get current velocities
        current_linear, current_angular = self.current_velocity
        
        # Maximum acceleration (change per update)
        max_acceleration = 0.1  # m/s per update
        max_angular_acceleration = 0.2  # rad/s per update
        
        # Calculate smooth transitions
        linear_diff = target_linear - current_linear
        angular_diff = target_angular - current_angular
        
        # Limit acceleration
        if abs(linear_diff) > max_acceleration:
            linear_diff = np.sign(linear_diff) * max_acceleration
        
        if abs(angular_diff) > max_angular_acceleration:
            angular_diff = np.sign(angular_diff) * max_angular_acceleration
        
        # Update velocities
        new_linear = current_linear + linear_diff
        new_angular = current_angular + angular_diff
        
        # Update current velocity
        self.current_velocity = (new_linear, new_angular)
        
        return new_linear, new_angular
    
    def _update_movement_state(self, distance: float):
        """
        Update movement state based on distance to target
        
        Args:
            distance: Distance to target person in meters
        """
        if distance < self.min_distance:
            self.current_state = MovementState.BACKING_UP
        elif distance < self.safe_distance:
            self.current_state = MovementState.APPROACHING
        elif distance > self.max_distance:
            self.current_state = MovementState.SEARCHING
        else:
            self.current_state = MovementState.FOLLOWING
    
    def _execute_movement_command(self, linear_velocity: float, angular_velocity: float):
        """
        Execute movement command (to be implemented based on robot hardware)
        
        Args:
            linear_velocity: Linear velocity in m/s
            angular_velocity: Angular velocity in rad/s
        """
        # This is a placeholder - actual implementation would depend on
        # the robot's movement system (ROS, serial commands, etc.)
        
        # Log movement command
        if abs(linear_velocity) > 0.01 or abs(angular_velocity) > 0.01:
            logging.debug(f"Movement command: linear={linear_velocity:.3f} m/s, "
                         f"angular={angular_velocity:.3f} rad/s")
        
        # Update last command time
        self.last_command_time = time.time()
    
    def execute_command(self, command: MovementCommand):
        """
        Execute a movement command
        
        Args:
            command: MovementCommand to execute
        """
        self._execute_movement_command(command.linear_velocity, command.angular_velocity)
    
    def get_current_state(self) -> MovementState:
        """
        Get current movement state
        
        Returns:
            Current MovementState
        """
        return self.current_state
    
    def is_emergency_stop_needed(self, distance: float) -> bool:
        """
        Check if emergency stop is needed
        
        Args:
            distance: Current distance to obstacle/person
            
        Returns:
            True if emergency stop is needed
        """
        return distance < self.emergency_stop_distance
    
    def get_safe_distance(self) -> float:
        """
        Get the safe following distance
        
        Returns:
            Safe distance in meters
        """
        return self.safe_distance
    
    def set_safe_distance(self, distance: float):
        """
        Set the safe following distance
        
        Args:
            distance: New safe distance in meters
        """
        if distance > 0:
            self.safe_distance = distance
            logging.info(f"Safe distance set to {distance} meters")
    
    def adjust_pid_parameters(self, 
                            distance_kp: float = None,
                            distance_ki: float = None,
                            distance_kd: float = None,
                            angle_kp: float = None,
                            angle_ki: float = None,
                            angle_kd: float = None):
        """
        Adjust PID controller parameters for fine-tuning
        
        Args:
            distance_kp/ki/kd: Distance PID parameters
            angle_kp/ki/kd: Angle PID parameters
        """
        if distance_kp is not None:
            self.distance_pid.kp = distance_kp
        if distance_ki is not None:
            self.distance_pid.ki = distance_ki
        if distance_kd is not None:
            self.distance_pid.kd = distance_kd
        
        if angle_kp is not None:
            self.angle_pid.kp = angle_kp
        if angle_ki is not None:
            self.angle_pid.ki = angle_ki
        if angle_kd is not None:
            self.angle_pid.kd = angle_kd
        
        logging.info("PID parameters updated")
    
    def cleanup(self):
        """Clean up resources and stop movement"""
        self.stop_following()
        logging.info("MovementController cleaned up")
