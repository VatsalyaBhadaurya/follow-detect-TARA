#!/usr/bin/env python3
"""
Alternative Voice Command Solutions for Tara

This script provides multiple approaches to get voice commands working:
1. Using sounddevice library
2. Using PyAudio directly
3. Using different speech recognition engines
4. Using keyboard input as fallback
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
import wave

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CommandType(Enum):
    """Voice command types"""
    FOLLOW_ME = "follow me"
    STOP = "stop"
    UNKNOWN = "unknown"

class AlternativeVoiceHandler:
    """
    Alternative voice command handler using multiple approaches
    """
    
    def __init__(self):
        """Initialize with multiple voice input methods"""
        
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
        
        # Voice input methods
        self.voice_methods = {
            'speechrecognition': self._init_speechrecognition,
            'sounddevice': self._init_sounddevice,
            'pyaudio_direct': self._init_pyaudio_direct,
            'keyboard_fallback': self._init_keyboard_fallback
        }
        
        self.current_method = None
        self.recognizer = None
        self.microphone = None
        
        # Initialize best available method
        self._initialize_best_method()
    
    def _init_speechrecognition(self) -> bool:
        """Initialize SpeechRecognition method"""
        try:
            self.recognizer = sr.Recognizer()
            
            # Try different microphone devices
            working_devices = [1, 5, 6]  # From troubleshooting
            for device_id in working_devices:
                try:
                    self.microphone = sr.Microphone(device_index=device_id)
                    logging.info(f"SpeechRecognition using device {device_id}")
                    
                    # Test access
                    with self.microphone as source:
                        self.recognizer.adjust_for_ambient_noise(source, duration=1)
                    
                    return True
                except Exception as e:
                    logging.debug(f"Device {device_id} failed: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logging.error(f"SpeechRecognition init failed: {e}")
            return False
    
    def _init_sounddevice(self) -> bool:
        """Initialize sounddevice method"""
        try:
            import sounddevice as sd
            
            # Get input devices
            devices = sd.query_devices()
            input_devices = []
            
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    input_devices.append(i)
            
            if input_devices:
                logging.info(f"sounddevice found {len(input_devices)} input devices")
                return True
            else:
                return False
                
        except ImportError:
            logging.warning("sounddevice not available")
            return False
        except Exception as e:
            logging.error(f"sounddevice init failed: {e}")
            return False
    
    def _init_pyaudio_direct(self) -> bool:
        """Initialize PyAudio direct method"""
        try:
            p = pyaudio.PyAudio()
            
            # Find input device
            input_device = None
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    input_device = i
                    break
            
            if input_device is not None:
                logging.info(f"PyAudio direct using device {input_device}")
                p.terminate()
                return True
            else:
                p.terminate()
                return False
                
        except Exception as e:
            logging.error(f"PyAudio direct init failed: {e}")
            return False
    
    def _init_keyboard_fallback(self) -> bool:
        """Initialize keyboard fallback method"""
        logging.info("Using keyboard fallback for voice commands")
        return True
    
    def _initialize_best_method(self):
        """Initialize the best available voice input method"""
        for method_name, init_func in self.voice_methods.items():
            try:
                if init_func():
                    self.current_method = method_name
                    logging.info(f"Initialized voice method: {method_name}")
                    break
            except Exception as e:
                logging.debug(f"Method {method_name} failed: {e}")
                continue
        
        if not self.current_method:
            logging.error("No voice input method available!")
    
    def register_callback(self, command_type: CommandType, callback: Callable):
        """Register command callback"""
        if callback not in self.command_callbacks[command_type]:
            self.command_callbacks[command_type].append(callback)
            logging.info(f"Registered callback for: {command_type.value}")
    
    def _recognize_command_speechrecognition(self, audio_data) -> CommandType:
        """Recognize command using SpeechRecognition"""
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
    
    def _recognize_command_sounddevice(self) -> CommandType:
        """Recognize command using sounddevice"""
        try:
            import sounddevice as sd
            import numpy as np
            
            # Record audio
            sample_rate = 44100
            duration = 3
            
            logging.info("Recording audio with sounddevice...")
            audio_data = sd.rec(int(duration * sample_rate), 
                              samplerate=sample_rate, 
                              channels=1, 
                              dtype=np.float32)
            sd.wait()
            
            # Convert to speech_recognition format
            audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
            audio = sr.AudioData(audio_bytes, sample_rate, 2)
            
            # Use speech recognition
            return self._recognize_command_speechrecognition(audio)
            
        except Exception as e:
            logging.error(f"sounddevice recognition failed: {e}")
            return CommandType.UNKNOWN
    
    def _recognize_command_pyaudio_direct(self) -> CommandType:
        """Recognize command using PyAudio direct"""
        try:
            p = pyaudio.PyAudio()
            
            # Find input device
            input_device = None
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    input_device = i
                    break
            
            if input_device is None:
                return CommandType.UNKNOWN
            
            # Record audio
            stream = p.open(format=pyaudio.paInt16,
                           channels=1,
                           rate=44100,
                           input=True,
                           input_device_index=input_device,
                           frames_per_buffer=1024)
            
            logging.info("Recording audio with PyAudio...")
            frames = []
            for _ in range(132):  # 3 seconds at 44100 Hz
                data = stream.read(1024)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            # Convert to speech_recognition format
            audio_bytes = b''.join(frames)
            audio = sr.AudioData(audio_bytes, 44100, 2)
            
            # Use speech recognition
            return self._recognize_command_speechrecognition(audio)
            
        except Exception as e:
            logging.error(f"PyAudio direct recognition failed: {e}")
            return CommandType.UNKNOWN
    
    def _keyboard_fallback_loop(self):
        """Keyboard fallback loop"""
        logging.info("Keyboard fallback active. Press 'F' for follow, 'S' for stop")
        
        while self.is_listening:
            try:
                # Check for keyboard input
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('f') or key == ord('F'):
                    logging.info("Keyboard: FOLLOW ME command")
                    self.command_queue.put(CommandType.FOLLOW_ME)
                    self._execute_callbacks(CommandType.FOLLOW_ME)
                elif key == ord('s') or key == ord('S'):
                    logging.info("Keyboard: STOP command")
                    self.command_queue.put(CommandType.STOP)
                    self._execute_callbacks(CommandType.STOP)
                
                time.sleep(0.1)
                
            except Exception as e:
                logging.error(f"Keyboard fallback error: {e}")
                break
    
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
        """Main listening loop using current method"""
        logging.info(f"Voice command listening started using: {self.current_method}")
        
        while self.is_listening:
            try:
                if self.current_method == 'speechrecognition':
                    # Use SpeechRecognition
                    if self.microphone and self.recognizer:
                        with self.microphone as source:
                            audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=3)
                        command = self._recognize_command_speechrecognition(audio)
                        if command != CommandType.UNKNOWN:
                            self.command_queue.put(command)
                            self._execute_callbacks(command)
                
                elif self.current_method == 'sounddevice':
                    # Use sounddevice
                    command = self._recognize_command_sounddevice()
                    if command != CommandType.UNKNOWN:
                        self.command_queue.put(command)
                        self._execute_callbacks(command)
                
                elif self.current_method == 'pyaudio_direct':
                    # Use PyAudio direct
                    command = self._recognize_command_pyaudio_direct()
                    if command != CommandType.UNKNOWN:
                        self.command_queue.put(command)
                        self._execute_callbacks(command)
                
                elif self.current_method == 'keyboard_fallback':
                    # Use keyboard fallback
                    self._keyboard_fallback_loop()
                    break  # Exit loop as keyboard_fallback_loop handles the loop
                
                time.sleep(0.5)  # Small delay between attempts
                
            except Exception as e:
                logging.error(f"Listening error: {e}")
                time.sleep(1.0)
    
    def start_listening(self):
        """Start voice command listening"""
        if self.is_listening:
            logging.warning("Already listening")
            return
        
        if not self.current_method:
            logging.error("No voice input method available")
            return
        
        self.is_listening = True
        self.listening_thread = threading.Thread(target=self._listening_loop, daemon=True)
        self.listening_thread.start()
        
        logging.info(f"Voice command listening started using: {self.current_method}")
    
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
    
    def test_method(self) -> bool:
        """Test current voice method"""
        if not self.current_method:
            return False
        
        logging.info(f"Testing voice method: {self.current_method}")
        
        if self.current_method == 'keyboard_fallback':
            logging.info("Keyboard fallback test: Press 'F' or 'S' keys")
            return True
        
        # For other methods, try a quick test
        try:
            if self.current_method == 'speechrecognition' and self.microphone:
                with self.microphone as source:
                    self.recognizer.energy_threshold = 50
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=2)
                    return True
            elif self.current_method == 'sounddevice':
                import sounddevice as sd
                # Quick recording test
                sd.rec(1024, samplerate=44100, channels=1, dtype=np.float32)
                sd.wait()
                return True
            elif self.current_method == 'pyaudio_direct':
                p = pyaudio.PyAudio()
                p.terminate()
                return True
        except Exception as e:
            logging.error(f"Method test failed: {e}")
            return False
    
    def cleanup(self):
        """Cleanup resources"""
        self.stop_listening()
        logging.info("AlternativeVoiceHandler cleaned up")

def test_alternative_voice_commands():
    """Test the alternative voice command system"""
    print("🎤 Testing Alternative Voice Commands")
    print("=" * 50)
    
    def on_follow():
        print("🎯 FOLLOW ME command received!")
    
    def on_stop():
        print("🛑 STOP command received!")
    
    # Initialize handler
    handler = AlternativeVoiceHandler()
    
    if not handler.current_method:
        print("❌ No voice input method available!")
        return
    
    # Register callbacks
    handler.register_callback(CommandType.FOLLOW_ME, on_follow)
    handler.register_callback(CommandType.STOP, on_stop)
    
    # Test method
    if handler.test_method():
        print(f"✅ Voice method test passed: {handler.current_method}")
    else:
        print(f"❌ Voice method test failed: {handler.current_method}")
        return
    
    # Start listening
    print(f"\n🎤 Voice command listening started using: {handler.current_method}")
    if handler.current_method == 'keyboard_fallback':
        print("Use keyboard: Press 'F' for follow, 'S' for stop")
    else:
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
    test_alternative_voice_commands()
