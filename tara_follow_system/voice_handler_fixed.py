"""
Fixed Voice Command Handler for Tara Robot

This version includes multiple speech recognition backends and better microphone handling.
"""

import speech_recognition as sr
import threading
import time
import logging
from typing import Callable, Optional, Dict, List
from enum import Enum
import queue
import os

class CommandType(Enum):
    """Enumeration of recognized voice commands"""
    FOLLOW_ME = "follow me"
    STOP = "stop"
    UNKNOWN = "unknown"

class VoiceCommandHandler:
    """
    Enhanced voice command recognition with multiple backends and better error handling
    """
    
    def __init__(self, 
                 language: str = "en-US",
                 energy_threshold: int = 300,
                 timeout: float = 1.0,
                 phrase_timeout: float = 0.3,
                 mic_device_index: Optional[int] = None):
        """
        Initialize voice command handler with multiple speech recognition backends
        """
        self.language = language
        self.energy_threshold = energy_threshold
        self.timeout = timeout
        self.phrase_timeout = phrase_timeout
        self.mic_device_index = mic_device_index
        
        # Initialize speech recognizer
        self.recognizer = sr.Recognizer()
        
        # Try to initialize microphone
        self.microphone = self._initialize_microphone()
        
        # Configure recognizer
        self.recognizer.energy_threshold = energy_threshold
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        
        # Command patterns for recognition
        self.command_patterns = {
            CommandType.FOLLOW_ME: [
                "follow me", "follow", "come here", "come follow", 
                "follow me please", "start following", "follow"
            ],
            CommandType.STOP: [
                "stop", "stop following", "halt", "freeze", 
                "don't follow", "stop please", "wait"
            ]
        }
        
        # Callback functions for commands
        self.command_callbacks: Dict[CommandType, List[Callable]] = {
            CommandType.FOLLOW_ME: [],
            CommandType.STOP: []
        }
        
        # Threading and control
        self.is_listening = False
        self.listening_thread: Optional[threading.Thread] = None
        self.command_queue = queue.Queue()
        
        # Speech recognition backends (in order of preference)
        self.recognition_backends = [
            self._recognize_with_google,
            self._recognize_with_sphinx,
            self._recognize_with_whisper_local
        ]
        
        # Calibrate microphone for ambient noise
        self._calibrate_microphone()
        
        logging.info("VoiceCommandHandler initialized successfully")
    
    def _initialize_microphone(self):
        """Initialize microphone with fallback options"""
        try:
            if self.mic_device_index is not None:
                # Try specified microphone
                mic = sr.Microphone(device_index=self.mic_device_index)
                logging.info(f"Using microphone device {self.mic_device_index}")
                return mic
            else:
                # Try default microphone
                mic = sr.Microphone()
                logging.info("Using default microphone")
                return mic
        except Exception as e:
            logging.error(f"Failed to initialize microphone: {e}")
            # Try to find any working microphone
            return self._find_working_microphone()
    
    def _find_working_microphone(self):
        """Find a working microphone from available devices"""
        mic_list = sr.Microphone.list_microphone_names()
        
        # Try microphones that look like input devices
        for i, mic_name in enumerate(mic_list):
            mic_lower = mic_name.lower()
            if any(keyword in mic_lower for keyword in ['microphone', 'mic', 'input', 'capture']):
                try:
                    mic = sr.Microphone(device_index=i)
                    logging.info(f"Found working microphone: {i} - {mic_name}")
                    return mic
                except Exception as e:
                    logging.debug(f"Microphone {i} failed: {e}")
                    continue
        
        # If no specific microphone found, try default
        try:
            return sr.Microphone()
        except Exception as e:
            logging.error(f"Failed to find any working microphone: {e}")
            return None
    
    def _calibrate_microphone(self):
        """Calibrate microphone for ambient noise"""
        if not self.microphone:
            logging.error("No microphone available for calibration")
            return
            
        try:
            logging.info("Calibrating microphone for ambient noise...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
            logging.info(f"Energy threshold set to {self.recognizer.energy_threshold}")
        except Exception as e:
            logging.error(f"Microphone calibration failed: {e}")
            # Use default threshold if calibration fails
            self.recognizer.energy_threshold = self.energy_threshold
    
    def _recognize_with_google(self, audio_data):
        """Try Google Speech Recognition"""
        try:
            text = self.recognizer.recognize_google(audio_data, language=self.language)
            logging.debug(f"Google recognition: '{text}'")
            return text
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            logging.debug(f"Google recognition failed: {e}")
            return None
    
    def _recognize_with_sphinx(self, audio_data):
        """Try PocketSphinx offline recognition"""
        try:
            text = self.recognizer.recognize_sphinx(audio_data)
            logging.debug(f"Sphinx recognition: '{text}'")
            return text
        except sr.UnknownValueError:
            return None
        except Exception as e:
            logging.debug(f"Sphinx recognition failed: {e}")
            return None
    
    def _recognize_with_whisper_local(self, audio_data):
        """Try local Whisper recognition (if available)"""
        try:
            # This would require additional setup with whisper
            # For now, we'll skip this backend
            return None
        except Exception as e:
            logging.debug(f"Whisper recognition failed: {e}")
            return None
    
    def register_callback(self, command_type: CommandType, callback: Callable):
        """Register a callback function for a specific command"""
        if callback not in self.command_callbacks[command_type]:
            self.command_callbacks[command_type].append(callback)
            logging.info(f"Registered callback for command: {command_type.value}")
    
    def unregister_callback(self, command_type: CommandType, callback: Callable):
        """Unregister a callback function for a specific command"""
        if callback in self.command_callbacks[command_type]:
            self.command_callbacks[command_type].remove(callback)
            logging.info(f"Unregistered callback for command: {command_type.value}")
    
    def _recognize_command(self, audio_data) -> CommandType:
        """Recognize command from audio data using multiple backends"""
        if not audio_data:
            return CommandType.UNKNOWN
        
        # Try each recognition backend
        for backend in self.recognition_backends:
            try:
                text = backend(audio_data)
                if text:
                    text = text.lower().strip()
                    logging.info(f"Recognized speech: '{text}'")
                    
                    # Check against command patterns
                    for command_type, patterns in self.command_patterns.items():
                        for pattern in patterns:
                            if pattern.lower() in text:
                                logging.info(f"Command detected: {command_type.value}")
                                return command_type
                    
                    return CommandType.UNKNOWN
            except Exception as e:
                logging.debug(f"Recognition backend failed: {e}")
                continue
        
        return CommandType.UNKNOWN
    
    def _execute_command_callbacks(self, command_type: CommandType):
        """Execute all registered callbacks for a command"""
        if command_type == CommandType.UNKNOWN:
            return
        
        callbacks = self.command_callbacks[command_type]
        for callback in callbacks:
            try:
                callback()
            except Exception as e:
                logging.error(f"Error executing callback for {command_type.value}: {e}")
    
    def _listening_loop(self):
        """Main listening loop running in separate thread"""
        logging.info("Voice command listening started")
        
        while self.is_listening:
            try:
                if not self.microphone:
                    logging.error("No microphone available")
                    time.sleep(1)
                    continue
                
                with self.microphone as source:
                    # Listen for audio with timeout
                    audio = self.recognizer.listen(
                        source, 
                        timeout=self.timeout, 
                        phrase_time_limit=self.phrase_timeout
                    )
                
                # Recognize command
                command = self._recognize_command(audio)
                
                if command != CommandType.UNKNOWN:
                    # Put command in queue for processing
                    self.command_queue.put(command)
                    
                    # Execute callbacks
                    self._execute_command_callbacks(command)
                    
            except sr.WaitTimeoutError:
                # No speech detected within timeout, continue listening
                continue
            except Exception as e:
                logging.error(f"Error in listening loop: {e}")
                time.sleep(0.1)  # Brief pause before retrying
    
    def start_listening(self):
        """Start continuous voice command listening"""
        if self.is_listening:
            logging.warning("Voice command listening is already active")
            return
        
        if not self.microphone:
            logging.error("Cannot start listening: no microphone available")
            return
        
        self.is_listening = True
        self.listening_thread = threading.Thread(target=self._listening_loop, daemon=True)
        self.listening_thread.start()
        
        logging.info("Voice command listening started")
    
    def stop_listening(self):
        """Stop voice command listening"""
        if not self.is_listening:
            logging.warning("Voice command listening is not active")
            return
        
        self.is_listening = False
        
        if self.listening_thread and self.listening_thread.is_alive():
            self.listening_thread.join(timeout=2.0)
        
        logging.info("Voice command listening stopped")
    
    def get_latest_command(self, timeout: float = 0.1) -> Optional[CommandType]:
        """Get the latest recognized command from the queue"""
        try:
            return self.command_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def clear_command_queue(self):
        """Clear all pending commands from the queue"""
        while not self.command_queue.empty():
            try:
                self.command_queue.get_nowait()
            except queue.Empty:
                break
    
    def test_microphone(self) -> bool:
        """Test if microphone is working properly"""
        if not self.microphone:
            logging.error("No microphone available for testing")
            return False
            
        try:
            logging.info("Testing microphone...")
            with self.microphone as source:
                # Test if we can get audio data
                audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=1)
                
                # Try to recognize (even if it fails, we know mic is working)
                try:
                    text = self._recognize_command(audio)
                    if text != CommandType.UNKNOWN:
                        logging.info(f"Microphone test passed - heard: {text}")
                    else:
                        logging.info("Microphone test passed - audio detected but no command recognized")
                    return True
                except:
                    logging.info("Microphone test passed - audio detected")
                    return True
                
        except Exception as e:
            logging.error(f"Microphone test failed: {e}")
            return False
    
    def set_energy_threshold(self, threshold: int):
        """Set microphone energy threshold"""
        self.recognizer.energy_threshold = threshold
        logging.info(f"Energy threshold set to {threshold}")
    
    def get_energy_threshold(self) -> int:
        """Get current microphone energy threshold"""
        return int(self.recognizer.energy_threshold)
    
    def cleanup(self):
        """Clean up resources"""
        self.stop_listening()
        logging.info("VoiceCommandHandler cleaned up")
