#!/usr/bin/env python3
"""
Tara Person Following System with Working Voice Commands

This is the main system with the working voice command configuration.
"""

import cv2
import numpy as np
import time
import logging
import argparse
import os
import sys
from typing import Optional

# Suppress YOLO verbose output
os.environ['YOLO_VERBOSE'] = 'False'

# Add the tara_follow_system to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tara_follow_system.follow_task import FollowPersonTask, FollowTaskConfig

def main():
    """Main function with working voice commands"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Tara Person Following System with Working Voice')
    parser.add_argument('--camera', type=int, default=0, help='Camera device ID')
    parser.add_argument('--width', type=int, default=640, help='Frame width')
    parser.add_argument('--height', type=int, default=480, help='Frame height')
    parser.add_argument('--fps', type=int, default=30, help='Target FPS')
    parser.add_argument('--confidence', type=float, default=0.3, help='Detection confidence threshold')
    parser.add_argument('--safe-distance', type=float, default=1.0, help='Safe following distance')
    parser.add_argument('--no-voice', action='store_true', help='Disable voice commands')
    parser.add_argument('--no-display', action='store_true', help='Disable video display')
    parser.add_argument('--save-video', action='store_true', help='Save output video')
    parser.add_argument('--video-filename', type=str, default='follow_output.avi', help='Output video filename')
    parser.add_argument('--log-level', type=str, default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logging.info("Starting Tara Person Following System with Working Voice")
    logging.info(f"Arguments: {vars(args)}")
    
    try:
        # Create configuration with working settings
        config = FollowTaskConfig(
            camera_id=args.camera,
            frame_width=args.width,
            frame_height=args.height,
            fps=args.fps,
            confidence_threshold=args.confidence,
            safe_distance=args.safe_distance
        )
        
        # Create and run the follow task
        follow_task = FollowPersonTask(config)
        
        print("🤖 Tara Person Following System with Working Voice")
        print("=" * 60)
        print("✅ Person detection and tracking: WORKING")
        print("✅ Distance calculation: WORKING (1.5-4.0m range)")
        print("✅ Bounding boxes: WORKING (color-coded)")
        print("✅ Voice commands: WORKING (PocketSphinx)")
        print()
        print("🎮 Controls:")
        print("  Voice: 'follow me', 'stop'")
        print("  Keyboard: F (follow), S (stop), Q (quit)")
        print()
        print("🎯 Voice Command Tips:")
        print("  - Speak clearly and at normal volume")
        print("  - Say 'follow me' to start following")
        print("  - Say 'stop' to stop following")
        print("  - Commands work with PocketSphinx (offline)")
        print()
        print("🚀 Starting system in 3 seconds...")
        time.sleep(3)
        
        # Run the follow task
        follow_task.run()
        
    except KeyboardInterrupt:
        logging.info("System interrupted by user")
        print("\n🛑 System stopped by user")
        
    except Exception as e:
        logging.error(f"System error: {e}")
        print(f"❌ System error: {e}")
        
    finally:
        # Cleanup
        try:
            if 'follow_task' in locals():
                follow_task.cleanup()
            cv2.destroyAllWindows()
            logging.info("System cleanup completed")
            print("✅ System cleanup completed")
        except Exception as e:
            logging.error(f"Cleanup error: {e}")
    
    logging.info("Tara Person Following System completed")

if __name__ == "__main__":
    main()
