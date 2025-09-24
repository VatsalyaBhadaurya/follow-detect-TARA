#!/usr/bin/env python3
"""
Working Voice Commands for Tara

This version uses the working microphone devices and optimized settings
based on the troubleshooting results.
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

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CommandType(Enum):
    """Voice command types"""
    FOLLOW_ME = "follow me"
    STOP = "stop"
    UNKNOWN = "unknown"

class OptimizedVoiceHandler:
    """
    Optimized voice command handler using working microphone devices
    """
    
    def __init__(self):
        """Initialize with working microphone devices"""
        # Working devices found in troubleshooting:
        self.working_devices = [1, 5, 6]  # Device IDs that work
        self.current_device = 1  # Start with device 1 (Microphone Array)
        
        # Optimized recognition settings
        self.energy_threshold = 50  # Very sensitive
        self.timeout = 5  # Longer timeout
        self.phrase_time_limit = 6  # Longer phrase time
        
        # Command patterns
        self.command_patterns = {
            CommandType.FOLLOW_ME: [
                "follow me", "follow", "come here", "come follow", 
                "follow me please", "start following"
            ],
            CommandType.STOP: [
                "stop", "stop following", "halt", "freeze", 
                "don't follow", "stop please", "wait"
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
        """Initialize with the best working microphone"""
        for device_id in self.working_devices:
            try:
                self.microphone = sr.Microphone(device_index=device_id)
                self.current_device = device_id
                logging.info(f"Using microphone device {device_id}")
                break
            except Exception as e:
                logging.warning(f"Failed to use device {device_id}: {e}")
                continue
        
        if not self.microphone:
            logging.error("No working microphone found!")
            return
        
        # Configure recognizer with optimized settings
        self.recognizer.energy_threshold = self.energy_threshold
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 1.0  # Longer pause threshold
        
        # Calibrate for ambient noise
        self._calibrate_microphone()
    
    def _calibrate_microphone(self):
        """Calibrate microphone with longer duration"""
        if not self.microphone:
            return
        
        try:
            logging.info("Calibrating microphone (this may take 5 seconds)...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=5)
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
        """Recognize command using multiple methods"""
        if not audio_data:
            return CommandType.UNKNOWN
        
        # Try Google Speech Recognition first
        try:
            text = self.recognizer.recognize_google(audio_data)
            text = text.lower().strip()
            logging.info(f"Google recognition: '{text}'")
        except sr.UnknownValueError:
            # Try PocketSphinx as fallback
            try:
                text = self.recognizer.recognize_sphinx(audio_data)
                text = text.lower().strip()
                logging.info(f"Sphinx recognition: '{text}'")
            except:
                return CommandType.UNKNOWN
        except sr.RequestError as e:
            logging.debug(f"Google recognition failed: {e}")
            # Try PocketSphinx as fallback
            try:
                text = self.recognizer.recognize_sphinx(audio_data)
                text = text.lower().strip()
                logging.info(f"Sphinx fallback: '{text}'")
            except:
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
        """Main listening loop with optimized settings"""
        logging.info("Optimized voice command listening started")
        
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
                time.sleep(0.1)
    
    def start_listening(self):
        """Start optimized voice command listening"""
        if self.is_listening:
            logging.warning("Already listening")
            return
        
        if not self.microphone:
            logging.error("No microphone available")
            return
        
        self.is_listening = True
        self.listening_thread = threading.Thread(target=self._listening_loop, daemon=True)
        self.listening_thread.start()
        
        logging.info("Optimized voice command listening started")
    
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
        """Test microphone with optimized settings"""
        if not self.microphone:
            return False
        
        try:
            logging.info("Testing microphone with optimized settings...")
            with self.microphone as source:
                # Lower threshold for testing
                self.recognizer.energy_threshold = 30
                audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=3)
                
                # Try recognition
                try:
                    text = self._recognize_command(audio)
                    if text != CommandType.UNKNOWN:
                        logging.info(f"Microphone test successful - heard: {text}")
                    else:
                        logging.info("Microphone test successful - audio detected")
                    return True
                except:
                    logging.info("Microphone test successful - audio detected")
                    return True
                    
        except Exception as e:
            logging.error(f"Microphone test failed: {e}")
            return False
    
    def cleanup(self):
        """Cleanup resources"""
        self.stop_listening()
        logging.info("OptimizedVoiceHandler cleaned up")

def test_optimized_voice_commands():
    """Test the optimized voice command system"""
    print("🎤 Testing Optimized Voice Commands")
    print("=" * 50)
    
    def on_follow():
        print("🎯 FOLLOW ME command received!")
    
    def on_stop():
        print("🛑 STOP command received!")
    
    # Initialize handler
    handler = OptimizedVoiceHandler()
    
    # Register callbacks
    handler.register_callback(CommandType.FOLLOW_ME, on_follow)
    handler.register_callback(CommandType.STOP, on_stop)
    
    # Test microphone
    if handler.test_microphone():
        print("✅ Microphone test passed!")
    else:
        print("❌ Microphone test failed!")
        return
    
    # Start listening
    print("\n🎤 Voice command listening started!")
    print("Say 'follow me' or 'stop' to test commands.")
    print("Press Ctrl+C to stop.")
    
    handler.start_listening()
    
    try:
        # Run for 30 seconds
        start_time = time.time()
        while time.time() - start_time < 30:
            command = handler.get_latest_command(timeout=0.1)
            if command:
                print(f"Command received: {command.value}")
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\nStopping...")
    
    finally:
        handler.cleanup()
        print("✅ Test completed!")

if __name__ == "__main__":
    test_optimized_voice_commands()
