"""
Tara Person Following System

A comprehensive system for enabling the Tara robot to follow a person
using voice commands, computer vision, and intelligent movement control.
"""

__version__ = "1.0.0"
__author__ = "Tara Development Team"

from .person_detector import PersonDetector
from .distance_estimator import DistanceEstimator
from .voice_handler import VoiceCommandHandler
from .movement_controller import MovementController
from .follow_task import FollowPersonTask

__all__ = [
    'PersonDetector',
    'DistanceEstimator', 
    'VoiceCommandHandler',
    'MovementController',
    'FollowPersonTask'
]
