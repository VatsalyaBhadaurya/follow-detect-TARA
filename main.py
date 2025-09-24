#!/usr/bin/env python3
"""
Main script for Tara Person Following System

This script demonstrates how to use the complete person following system.
It initializes the task with default configuration and runs the main loop.
"""

import sys
import logging
import argparse
from tara_follow_system.follow_task import FollowPersonTask, FollowTaskConfig

def setup_logging(log_level: str = "INFO"):
    """
    Setup logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('tara_follow.log')
        ]
    )

def main():
    """Main function to run the Tara follow person task"""
    parser = argparse.ArgumentParser(description='Tara Person Following System')
    parser.add_argument('--camera', type=int, default=0, help='Camera ID (default: 0)')
    parser.add_argument('--width', type=int, default=640, help='Frame width (default: 640)')
    parser.add_argument('--height', type=int, default=480, help='Frame height (default: 480)')
    parser.add_argument('--fps', type=int, default=30, help='Target FPS (default: 30)')
    parser.add_argument('--confidence', type=float, default=0.5, help='Detection confidence threshold (default: 0.5)')
    parser.add_argument('--safe-distance', type=float, default=1.0, help='Safe following distance in meters (default: 1.0)')
    parser.add_argument('--no-voice', action='store_true', help='Disable voice commands')
    parser.add_argument('--no-display', action='store_true', help='Disable video display')
    parser.add_argument('--save-video', action='store_true', help='Save output video')
    parser.add_argument('--video-filename', type=str, default='follow_output.avi', help='Output video filename')
    parser.add_argument('--log-level', type=str, default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='Logging level')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    logging.info("Starting Tara Person Following System")
    logging.info(f"Arguments: {vars(args)}")
    
    try:
        # Create configuration
        config = FollowTaskConfig(
            camera_id=args.camera,
            frame_width=args.width,
            frame_height=args.height,
            fps=args.fps,
            confidence_threshold=args.confidence,
            safe_distance=args.safe_distance,
            voice_enabled=not args.no_voice,
            show_display=not args.no_display,
            save_video=args.save_video,
            video_filename=args.video_filename
        )
        
        # Create and run follow task
        follow_task = FollowPersonTask(config)
        follow_task.run()
        
    except KeyboardInterrupt:
        logging.info("Task interrupted by user")
    except Exception as e:
        logging.error(f"Task failed with error: {e}")
        sys.exit(1)
    
    logging.info("Tara Person Following System completed")

if __name__ == "__main__":
    main()
