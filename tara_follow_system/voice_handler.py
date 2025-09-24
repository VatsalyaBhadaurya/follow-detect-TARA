"""
Voice Command Handler for Tara Robot

This module handles voice command recognition for the person following system.
It processes "follow me" and "stop" commands using speech recognition.
"""

import speech_recognition as sr
import threading
import time
import logging
from typing import Callable, Optional, Dict, List
from enum import Enum
import queue

class CommandType(Enum):
    """Enumeration of recognized voice commands"""
    FOLLOW_ME = "follow me"
    STOP = "stop"
    UNKNOWN = "unknown"

class VoiceCommandHandler:
    """
    Voice command recognition and processing system
    
    This class provides methods to:
    1. Listen for voice commands continuously
    2. Recognize "follow me" and "stop" commands
    3. Handle command callbacks
    4. Manage microphone and speech recognition
    """
    
    def __init__(self, 
                 language: str = "en-US",
                 energy_threshold: int = 300,
                 timeout: float = 1.0,
                 phrase_timeout: float = 0.3):
        """
        Initialize voice command handler
        
        Args:
            language: Language for speech recognition
            energy_threshold: Energy threshold for microphone activation
            timeout: Timeout for speech recognition
            phrase_timeout: Timeout between phrases
        """
        self.language = language
        self.energy_threshold = energy_threshold
        self.timeout = timeout
        self.phrase_timeout = phrase_timeout
        
        # Initialize speech recognizer
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
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
        
        # Calibrate microphone for ambient noise
        self._calibrate_microphone()
        
        logging.info("VoiceCommandHandler initialized successfully")
    
    def _calibrate_microphone(self):
        """Calibrate microphone for ambient noise"""
        try:
            logging.info("Calibrating microphone for ambient noise...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
            logging.info(f"Energy threshold set to {self.recognizer.energy_threshold}")
        except Exception as e:
            logging.error(f"Microphone calibration failed: {e}")
            # Use default threshold if calibration fails
            self.recognizer.energy_threshold = self.energy_threshold
    
    def register_callback(self, command_type: CommandType, callback: Callable):
        """
        Register a callback function for a specific command
        
        Args:
            command_type: Type of command to register callback for
            callback: Function to call when command is detected
        """
        if callback not in self.command_callbacks[command_type]:
            self.command_callbacks[command_type].append(callback)
            logging.info(f"Registered callback for command: {command_type.value}")
    
    def unregister_callback(self, command_type: CommandType, callback: Callable):
        """
        Unregister a callback function for a specific command
        
        Args:
            command_type: Type of command to unregister callback for
            callback: Function to unregister
        """
        if callback in self.command_callbacks[command_type]:
            self.command_callbacks[command_type].remove(callback)
            logging.info(f"Unregistered callback for command: {command_type.value}")
    
    def _recognize_command(self, audio_data) -> CommandType:
        """
        Recognize command from audio data
        
        Args:
            audio_data: Audio data from microphone
            
        Returns:
            Recognized command type
        """
        try:
            # Convert audio to text
            text = self.recognizer.recognize_google(audio_data, language=self.language)
            text = text.lower().strip()
            
            logging.info(f"Recognized speech: '{text}'")
            
            # Check against command patterns
            for command_type, patterns in self.command_patterns.items():
                for pattern in patterns:
                    if pattern.lower() in text:
                        logging.info(f"Command detected: {command_type.value}")
                        return command_type
            
            return CommandType.UNKNOWN
            
        except sr.UnknownValueError:
            # Speech was unintelligible
            return CommandType.UNKNOWN
        except sr.RequestError as e:
            logging.error(f"Speech recognition service error: {e}")
            return CommandType.UNKNOWN
        except Exception as e:
            logging.error(f"Error in speech recognition: {e}")
            return CommandType.UNKNOWN
    
    def _execute_command_callbacks(self, command_type: CommandType):
        """
        Execute all registered callbacks for a command
        
        Args:
            command_type: Type of command that was detected
        """
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
        """
        Get the latest recognized command from the queue
        
        Args:
            timeout: Timeout for getting command from queue
            
        Returns:
            Latest command type or None if no command available
        """
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
        """
        Test if microphone is working properly
        
        Returns:
            True if microphone test passes, False otherwise
        """
        try:
            logging.info("Testing microphone...")
            with self.microphone as source:
                # Test if we can get audio data
                audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=1)
                
                # Try to recognize (even if it fails, we know mic is working)
                try:
                    self.recognizer.recognize_google(audio)
                except:
                    pass  # We don't care about recognition, just that we got audio
                
            logging.info("Microphone test passed")
            return True
            
        except Exception as e:
            logging.error(f"Microphone test failed: {e}")
            return False
    
    def set_energy_threshold(self, threshold: int):
        """
        Set microphone energy threshold
        
        Args:
            threshold: New energy threshold value
        """
        self.recognizer.energy_threshold = threshold
        logging.info(f"Energy threshold set to {threshold}")
    
    def get_energy_threshold(self) -> int:
        """
        Get current microphone energy threshold
        
        Returns:
            Current energy threshold value
        """
        return self.recognizer.energy_threshold
    
    def cleanup(self):
        """Clean up resources"""
        self.stop_listening()
        logging.info("VoiceCommandHandler cleaned up")
