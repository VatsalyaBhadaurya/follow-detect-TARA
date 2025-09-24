#!/usr/bin/env python3
"""
Tara Voice Integration - Working Voice Commands

This integrates the working voice command system into the main Tara follow system.
"""

import cv2
import numpy as np
import time
import logging
import threading
import queue
from typing import Callable, Optional, List
from enum import Enum
import speech_recognition as sr
import pyaudio
import os
import sys

# Add the tara_follow_system to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tara_follow_system.follow_task import FollowPersonTask, FollowTaskConfig
from tara_follow_system.follow_task import FollowTaskState

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CommandType(Enum):
    """Voice command types"""
    FOLLOW_ME = "follow me"
    STOP = "stop"
    UNKNOWN = "unknown"

class WorkingVoiceHandler:
    """
    Working voice command handler using PocketSphinx
    """
    
    def __init__(self):
        """Initialize with working settings"""
        
        # Working device from troubleshooting
        self.device_id = 1  # Microphone Array
        
        # Optimized settings for PocketSphinx
        self.energy_threshold = 300  # Higher threshold for better detection
        self.timeout = 3
        self.phrase_time_limit = 4
        
        # Command patterns
        self.command_patterns = {
            CommandType.FOLLOW_ME: [
                "follow me", "follow", "come here", "come follow", 
                "follow me please", "start following", "start follow"
            ],
            CommandType.STOP: [
                "stop", "stop following", "halt", "freeze", 
                "don't follow", "stop please", "wait", "stop follow"
            ]
        }
        
        # Callbacks
        self.command_callbacks = {
            CommandType.FOLLOW_ME: [],
            CommandType.STOP: []
        }
        
        # Threading
        self.is_listening = False
        self.listening_thread = None
        self.command_queue = queue.Queue()
        
        # Initialize recognizer
        self.recognizer = sr.Recognizer()
        self.microphone = None
        
        self._initialize_microphone()
    
    def _initialize_microphone(self):
        """Initialize with working microphone"""
        try:
            self.microphone = sr.Microphone(device_index=self.device_id)
            logging.info(f"Using microphone device {self.device_id}")
            
            # Configure recognizer
            self.recognizer.energy_threshold = self.energy_threshold
            self.recognizer.dynamic_energy_threshold = False  # Use fixed threshold
            self.recognizer.pause_threshold = 0.8  # Shorter pause
            
            # Calibrate
            self._calibrate_microphone()
            
        except Exception as e:
            logging.error(f"Microphone initialization failed: {e}")
            self.microphone = None
    
    def _calibrate_microphone(self):
        """Calibrate microphone"""
        if not self.microphone:
            return
        
        try:
            logging.info("Calibrating microphone...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
            logging.info(f"Energy threshold set to {self.recognizer.energy_threshold}")
        except Exception as e:
            logging.error(f"Microphone calibration failed: {e}")
            self.recognizer.energy_threshold = self.energy_threshold
    
    def register_callback(self, command_type: CommandType, callback: Callable):
        """Register command callback"""
        if callback not in self.command_callbacks[command_type]:
            self.command_callbacks[command_type].append(callback)
            logging.info(f"Registered callback for: {command_type.value}")
    
    def _recognize_command(self, audio_data) -> CommandType:
        """Recognize command using PocketSphinx"""
        if not audio_data:
            return CommandType.UNKNOWN
        
        # Use PocketSphinx (offline, more reliable)
        try:
            text = self.recognizer.recognize_sphinx(audio_data)
            text = text.lower().strip()
            logging.info(f"Sphinx recognition: '{text}'")
        except sr.UnknownValueError:
            return CommandType.UNKNOWN
        except Exception as e:
            logging.debug(f"Sphinx recognition failed: {e}")
            return CommandType.UNKNOWN
        
        # Check for commands
        for command_type, patterns in self.command_patterns.items():
            for pattern in patterns:
                if pattern.lower() in text:
                    logging.info(f"Command detected: {command_type.value}")
                    return command_type
        
        return CommandType.UNKNOWN
    
    def _execute_callbacks(self, command_type: CommandType):
        """Execute registered callbacks"""
        if command_type == CommandType.UNKNOWN:
            return
        
        callbacks = self.command_callbacks[command_type]
        for callback in callbacks:
            try:
                callback()
            except Exception as e:
                logging.error(f"Callback error: {e}")
    
    def _listening_loop(self):
        """Main listening loop"""
        logging.info("Voice command listening started")
        
        if not self.microphone:
            logging.error("No microphone available")
            return
        
        while self.is_listening:
            try:
                with self.microphone as source:
                    # Use optimized settings
                    audio = self.recognizer.listen(
                        source,
                        timeout=self.timeout,
                        phrase_time_limit=self.phrase_time_limit
                    )
                
                # Recognize command
                command = self._recognize_command(audio)
                
                if command != CommandType.UNKNOWN:
                    self.command_queue.put(command)
                    self._execute_callbacks(command)
                    
            except sr.WaitTimeoutError:
                continue  # No speech detected, continue listening
            except Exception as e:
                logging.error(f"Listening error: {e}")
                time.sleep(0.5)
    
    def start_listening(self):
        """Start voice command listening"""
        if self.is_listening:
            logging.warning("Already listening")
            return
        
        if not self.microphone:
            logging.error("No microphone available")
            return
        
        self.is_listening = True
        self.listening_thread = threading.Thread(target=self._listening_loop, daemon=True)
        self.listening_thread.start()
        
        logging.info("Voice command listening started")
    
    def stop_listening(self):
        """Stop voice command listening"""
        self.is_listening = False
        if self.listening_thread and self.listening_thread.is_alive():
            self.listening_thread.join(timeout=2.0)
        logging.info("Voice command listening stopped")
    
    def get_latest_command(self, timeout: float = 0.1) -> Optional[CommandType]:
        """Get latest command"""
        try:
            return self.command_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def test_microphone(self) -> bool:
        """Test microphone"""
        if not self.microphone:
            return False
        
        try:
            logging.info("Testing microphone...")
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=2)
                text = self._recognize_command(audio)
                logging.info(f"Microphone test - heard: {text.value if text != CommandType.UNKNOWN else 'unrecognized'}")
                return True
        except Exception as e:
            logging.error(f"Microphone test failed: {e}")
            return False
    
    def cleanup(self):
        """Cleanup resources"""
        self.stop_listening()
        logging.info("WorkingVoiceHandler cleaned up")

class TaraVoiceIntegration:
    """
    Tara system with integrated voice commands
    """
    
    def __init__(self):
        """Initialize Tara with voice commands"""
        
        # Initialize voice handler
        self.voice_handler = WorkingVoiceHandler()
        
        # Initialize Tara follow task
        config = FollowTaskConfig(
            camera_id=0,
            frame_width=640,
            frame_height=480,
            fps=30,
            confidence_threshold=0.3,
            safe_distance=1.0
        )
        
        self.follow_task = FollowPersonTask(config)
        
        # Register voice callbacks
        self.voice_handler.register_callback(CommandType.FOLLOW_ME, self._on_follow_command)
        self.voice_handler.register_callback(CommandType.STOP, self._on_stop_command)
        
        # State
        self.is_running = False
        self.current_state = FollowTaskState.IDLE
        
        logging.info("Tara Voice Integration initialized")
    
    def _on_follow_command(self):
        """Handle follow me command"""
        logging.info("🎯 Voice command: FOLLOW ME")
        if self.follow_task:
            self.follow_task.start_following()
            self.current_state = FollowTaskState.FOLLOWING
    
    def _on_stop_command(self):
        """Handle stop command"""
        logging.info("🛑 Voice command: STOP")
        if self.follow_task:
            self.follow_task.stop_following()
            self.current_state = FollowTaskState.IDLE
    
    def run(self):
        """Run Tara with voice commands"""
        print("🤖 Tara Person Following with Voice Commands")
        print("=" * 50)
        
        # Test voice system
        if not self.voice_handler.test_microphone():
            print("❌ Voice system test failed!")
            print("Using keyboard fallback: F (follow), S (stop), Q (quit)")
            use_voice = False
        else:
            print("✅ Voice system test passed!")
            print("Voice commands: 'follow me', 'stop'")
            print("Keyboard fallback: F (follow), S (stop), Q (quit)")
            use_voice = True
        
        # Start voice listening
        if use_voice:
            self.voice_handler.start_listening()
        
        # Start Tara follow task in a separate thread
        self.follow_task_thread = threading.Thread(target=self.follow_task.run, daemon=True)
        self.follow_task_thread.start()
        self.is_running = True
        
        print("\n🎮 Controls:")
        if use_voice:
            print("  Voice: 'follow me', 'stop'")
        print("  Keyboard: F (follow), S (stop), Q (quit)")
        print("\nStarting in 3 seconds...")
        time.sleep(3)
        
        try:
            # Main loop
            while self.is_running:
                # Check for keyboard input
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q') or key == 27:  # Q or ESC
                    print("🛑 Quit command received")
                    break
                elif key == ord('f') or key == ord('F'):
                    self._on_follow_command()
                elif key == ord('s') or key == ord('S'):
                    self._on_stop_command()
                
                # Check for voice commands
                if use_voice:
                    voice_command = self.voice_handler.get_latest_command(timeout=0.01)
                    if voice_command:
                        print(f"🎤 Voice command received: {voice_command.value}")
                
                # Update state display
                self._update_state_display()
                
                time.sleep(0.01)
        
        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
        
        finally:
            self.cleanup()
    
    def _update_state_display(self):
        """Update state display"""
        current_state = self.follow_task.get_current_state()
        if current_state != self.current_state:
            self.current_state = current_state
            state_messages = {
                FollowTaskState.IDLE: "🟡 IDLE - Waiting for command",
                FollowTaskState.FOLLOWING: "🟢 FOLLOWING - Tracking person",
                FollowTaskState.SEARCHING: "🔍 SEARCHING - Looking for person",
                FollowTaskState.LOST: "🔴 LOST - Person not found"
            }
            print(f"State: {state_messages.get(current_state, 'Unknown')}")
    
    def cleanup(self):
        """Cleanup resources"""
        self.is_running = False
        
        if self.follow_task:
            self.follow_task.stop_following()
            self.follow_task.cleanup()
        
        if self.voice_handler:
            self.voice_handler.cleanup()
        
        cv2.destroyAllWindows()
        logging.info("Tara Voice Integration cleanup completed")

def main():
    """Main function"""
    try:
        tara = TaraVoiceIntegration()
        tara.run()
    except Exception as e:
        logging.error(f"Tara Voice Integration error: {e}")
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
