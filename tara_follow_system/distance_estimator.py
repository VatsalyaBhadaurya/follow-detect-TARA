"""
Distance Estimation Module for Tara Robot

This module estimates the distance to a detected person based on:
1. Bounding box size (larger = closer)
2. Bounding box position (center vs edges)
3. Known reference measurements for calibration
"""

import numpy as np
import cv2
from typing import Tuple, Optional, Dict
import logging
from dataclasses import dataclass
from scipy.optimize import curve_fit
import json
import os

@dataclass
class DistanceEstimate:
    """Data class for distance estimation results"""
    distance_meters: float
    confidence: float
    method: str  # 'size_based', 'position_based', 'combined'
    bounding_box_area: int
    person_height_pixels: int

class DistanceEstimator:
    """
    Distance estimation based on person bounding box analysis
    
    This class provides methods to:
    1. Estimate distance based on bounding box size
    2. Estimate distance based on bounding box position
    3. Combine multiple estimation methods for accuracy
    4. Calibrate distance estimation parameters
    """
    
    def __init__(self, 
                 camera_fov_horizontal: float = 60.0,  # degrees
                 camera_fov_vertical: float = 45.0,    # degrees
                 reference_height_meters: float = 1.7, # average human height
                 calibration_file: Optional[str] = None):
        """
        Initialize distance estimator
        
        Args:
            camera_fov_horizontal: Camera horizontal field of view in degrees
            camera_fov_vertical: Camera vertical field of view in degrees
            reference_height_meters: Reference human height in meters
            calibration_file: Path to calibration data file
        """
        self.camera_fov_horizontal = camera_fov_horizontal
        self.camera_fov_vertical = camera_fov_vertical
        self.reference_height_meters = reference_height_meters
        
        # Distance estimation parameters
        self.size_distance_params = None
        self.position_distance_params = None
        
        # Calibration data
        self.calibration_data = []
        self.is_calibrated = False
        
        # Load calibration if provided
        if calibration_file and os.path.exists(calibration_file):
            self.load_calibration(calibration_file)
        
        # Default parameters (will be updated during calibration)
        self._initialize_default_parameters()
        
        # Realistic calibration for typical webcam setup
        self._calibrate_realistic_parameters()
        
        logging.info("DistanceEstimator initialized successfully")
    
    def _calibrate_realistic_parameters(self):
        """Set realistic parameters for typical webcam distance estimation"""
        # Typical webcam parameters for 640x480 resolution
        # These values are calibrated for realistic indoor distances (0.5m - 3m)
        
        # For height-based estimation: distance = (real_height * focal_length) / pixel_height
        # Typical webcam has ~60 degree horizontal FOV, ~45 degree vertical FOV
        # For 480px height: focal_length ≈ 480 / (2 * tan(22.5°)) ≈ 580 pixels
        
        # More realistic focal length for webcam
        self.realistic_focal_length = 580.0
        
        # Realistic size-based constant (calibrated for indoor distances)
        self.realistic_size_k = 150.0
        
        logging.info("Realistic parameters calibrated for webcam distance estimation")
    
    def _initialize_default_parameters(self):
        """Initialize default distance estimation parameters"""
        # Default size-based distance estimation
        # Formula: distance = k / sqrt(bounding_box_area)
        self.default_size_k = 200.0  # More realistic calibration constant
        
        # Default position-based distance estimation
        # Based on perspective projection
        self.default_position_focal_length = 400.0  # More realistic focal length for webcam
    
    def estimate_distance_size_based(self, 
                                   person_bbox, 
                                   frame_height: int) -> DistanceEstimate:
        """
        Estimate distance based on bounding box size
        
        Args:
            person_bbox: PersonBoundingBox object
            frame_height: Height of the video frame
            
        Returns:
            DistanceEstimate object
        """
        try:
            # Calculate bounding box area
            bbox_area = person_bbox.area
            person_height_pixels = person_bbox.height
            
            # Method 1: Area-based estimation
            if self.size_distance_params:
                # Use calibrated parameters
                k = self.size_distance_params['k']
                distance = k / np.sqrt(bbox_area)
            else:
                # Use default parameters
                distance = self.default_size_k / np.sqrt(bbox_area)
            
            # Method 2: Height-based estimation (more accurate)
            # Use pinhole camera model: distance = (real_height * focal_length) / pixel_height
            if person_height_pixels > 0:
                # Use realistic focal length for webcam
                focal_length_pixels = self.realistic_focal_length
                distance_height = (self.reference_height_meters * focal_length_pixels) / person_height_pixels
                
                # Use height-based estimation as primary (more accurate)
                distance = distance_height
                
                # Apply sanity checks for realistic distances
                if distance < 0.2:  # Too close
                    distance = 0.2
                elif distance > 5.0:  # Too far for typical indoor
                    distance = 5.0
            
            # Calculate confidence based on bounding box size
            # Larger bounding boxes (closer persons) have higher confidence
            confidence = min(1.0, person_height_pixels / (frame_height * 0.5))
            
            return DistanceEstimate(
                distance_meters=distance,
                confidence=confidence,
                method='size_based',
                bounding_box_area=bbox_area,
                person_height_pixels=person_height_pixels
            )
            
        except Exception as e:
            logging.error(f"Error in size-based distance estimation: {e}")
            return DistanceEstimate(
                distance_meters=0.0,
                confidence=0.0,
                method='size_based',
                bounding_box_area=0,
                person_height_pixels=0
            )
    
    def estimate_distance_position_based(self, 
                                       person_bbox, 
                                       frame_width: int, 
                                       frame_height: int) -> DistanceEstimate:
        """
        Estimate distance based on bounding box position in frame
        
        Args:
            person_bbox: PersonBoundingBox object
            frame_width: Width of the video frame
            frame_height: Height of the video frame
            
        Returns:
            DistanceEstimate object
        """
        try:
            center_x, center_y = person_bbox.center
            bbox_area = person_bbox.area
            
            # Calculate how far the person is from the center
            frame_center_x = frame_width // 2
            frame_center_y = frame_height // 2
            
            # Distance from center (normalized)
            distance_from_center_x = abs(center_x - frame_center_x) / frame_width
            distance_from_center_y = abs(center_y - frame_center_y) / frame_height
            
            # Combined distance from center
            distance_from_center = np.sqrt(
                distance_from_center_x**2 + distance_from_center_y**2
            )
            
            # Estimate distance based on position
            # Persons at the edges are typically farther away
            # This is a rough estimation - more accurate methods would require
            # depth sensors or stereo vision
            
            # Simple heuristic: persons at edges are 1.5x farther
            position_factor = 1.0 + (distance_from_center * 0.5)
            
            # Base distance from size estimation
            base_distance = self.default_size_k / np.sqrt(bbox_area)
            distance = base_distance * position_factor
            
            # Lower confidence for position-based estimation
            confidence = max(0.3, 1.0 - distance_from_center)
            
            return DistanceEstimate(
                distance_meters=distance,
                confidence=confidence,
                method='position_based',
                bounding_box_area=bbox_area,
                person_height_pixels=person_bbox.height
            )
            
        except Exception as e:
            logging.error(f"Error in position-based distance estimation: {e}")
            return DistanceEstimate(
                distance_meters=0.0,
                confidence=0.0,
                method='position_based',
                bounding_box_area=0,
                person_height_pixels=0
            )
    
    def estimate_distance_combined(self, 
                                 person_bbox, 
                                 frame_width: int, 
                                 frame_height: int) -> DistanceEstimate:
        """
        Combine multiple distance estimation methods for better accuracy
        
        Args:
            person_bbox: PersonBoundingBox object
            frame_width: Width of the video frame
            frame_height: Height of the video frame
            
        Returns:
            DistanceEstimate object with combined estimation
        """
        try:
            # Get estimates from both methods
            size_estimate = self.estimate_distance_size_based(person_bbox, frame_height)
            position_estimate = self.estimate_distance_position_based(
                person_bbox, frame_width, frame_height
            )
            
            # Weight the estimates based on confidence
            if size_estimate.confidence > 0.5:
                # Use size-based as primary if high confidence
                primary_estimate = size_estimate
                secondary_estimate = position_estimate
                primary_weight = 0.7
                secondary_weight = 0.3
            else:
                # Use position-based as primary if size confidence is low
                primary_estimate = position_estimate
                secondary_estimate = size_estimate
                primary_weight = 0.6
                secondary_weight = 0.4
            
            # Combine estimates
            combined_distance = (
                primary_estimate.distance_meters * primary_weight +
                secondary_estimate.distance_meters * secondary_weight
            )
            
            # Calculate combined confidence
            combined_confidence = (
                primary_estimate.confidence * primary_weight +
                secondary_estimate.confidence * secondary_weight
            )
            
            # Apply realistic sanity checks for indoor distances
            if combined_distance < 0.2:  # Minimum realistic distance
                combined_distance = 0.2
                combined_confidence *= 0.8
            elif combined_distance > 4.0:  # Maximum realistic indoor distance
                combined_distance = 4.0
                combined_confidence *= 0.7
            
            return DistanceEstimate(
                distance_meters=combined_distance,
                confidence=combined_confidence,
                method='combined',
                bounding_box_area=person_bbox.area,
                person_height_pixels=person_bbox.height
            )
            
        except Exception as e:
            logging.error(f"Error in combined distance estimation: {e}")
            return DistanceEstimate(
                distance_meters=0.0,
                confidence=0.0,
                method='combined',
                bounding_box_area=0,
                person_height_pixels=0
            )
    
    def add_calibration_point(self, 
                            person_bbox, 
                            actual_distance_meters: float,
                            frame_width: int, 
                            frame_height: int):
        """
        Add a calibration point for distance estimation
        
        Args:
            person_bbox: PersonBoundingBox object
            actual_distance_meters: Known actual distance in meters
            frame_width: Width of the video frame
            frame_height: Height of the video frame
        """
        calibration_point = {
            'bbox_area': person_bbox.area,
            'bbox_height': person_bbox.height,
            'actual_distance': actual_distance_meters,
            'frame_width': frame_width,
            'frame_height': frame_height,
            'center_x': person_bbox.center[0],
            'center_y': person_bbox.center[1]
        }
        
        self.calibration_data.append(calibration_point)
        logging.info(f"Added calibration point: {actual_distance_meters}m distance, "
                    f"{person_bbox.area} bbox area")
    
    def calibrate_from_data(self):
        """
        Calibrate distance estimation parameters from collected data
        """
        if len(self.calibration_data) < 3:
            logging.warning("Need at least 3 calibration points for calibration")
            return
        
        try:
            # Extract data for size-based calibration
            areas = np.array([point['bbox_area'] for point in self.calibration_data])
            distances = np.array([point['actual_distance'] for point in self.calibration_data])
            
            # Fit curve: distance = k / sqrt(area)
            def distance_function(area, k):
                return k / np.sqrt(area)
            
            popt, _ = curve_fit(distance_function, areas, distances, p0=[5000.0])
            self.size_distance_params = {'k': popt[0]}
            
            self.is_calibrated = True
            logging.info(f"Calibration completed. Size-based parameter k = {popt[0]:.2f}")
            
        except Exception as e:
            logging.error(f"Calibration failed: {e}")
    
    def save_calibration(self, filepath: str):
        """
        Save calibration data to file
        
        Args:
            filepath: Path to save calibration file
        """
        calibration_info = {
            'calibration_data': self.calibration_data,
            'size_distance_params': self.size_distance_params,
            'position_distance_params': self.position_distance_params,
            'is_calibrated': self.is_calibrated,
            'camera_fov_horizontal': self.camera_fov_horizontal,
            'camera_fov_vertical': self.camera_fov_vertical,
            'reference_height_meters': self.reference_height_meters
        }
        
        with open(filepath, 'w') as f:
            json.dump(calibration_info, f, indent=2)
        
        logging.info(f"Calibration saved to {filepath}")
    
    def load_calibration(self, filepath: str):
        """
        Load calibration data from file
        
        Args:
            filepath: Path to calibration file
        """
        try:
            with open(filepath, 'r') as f:
                calibration_info = json.load(f)
            
            self.calibration_data = calibration_info.get('calibration_data', [])
            self.size_distance_params = calibration_info.get('size_distance_params')
            self.position_distance_params = calibration_info.get('position_distance_params')
            self.is_calibrated = calibration_info.get('is_calibrated', False)
            
            # Update camera parameters if available
            if 'camera_fov_horizontal' in calibration_info:
                self.camera_fov_horizontal = calibration_info['camera_fov_horizontal']
            if 'camera_fov_vertical' in calibration_info:
                self.camera_fov_vertical = calibration_info['camera_fov_vertical']
            if 'reference_height_meters' in calibration_info:
                self.reference_height_meters = calibration_info['reference_height_meters']
            
            logging.info(f"Calibration loaded from {filepath}")
            
        except Exception as e:
            logging.error(f"Failed to load calibration from {filepath}: {e}")
    
    def get_distance_category(self, distance_meters: float) -> str:
        """
        Categorize distance for movement control
        
        Args:
            distance_meters: Distance in meters
            
        Returns:
            Distance category string
        """
        if distance_meters < 0.5:
            return "too_close"
        elif distance_meters < 1.0:
            return "close"
        elif distance_meters < 2.0:
            return "optimal"
        elif distance_meters < 3.0:
            return "far"
        else:
            return "very_far"
