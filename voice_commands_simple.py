#!/usr/bin/env python3
"""
Simple Voice Commands for Tara

This version uses keyboard input as a voice command alternative for testing.
"""

import cv2
import numpy as np
import time
import logging
import threading
from typing import Callable, Optional
from enum import Enum
import queue

class CommandType(Enum):
    """Enumeration of recognized voice commands"""
    FOLLOW_ME = "follow me"
    STOP = "stop"
    UNKNOWN = "unknown"

class SimpleVoiceCommandHandler:
    """
    Simple voice command handler that can use keyboard input as fallback
    """
    
    def __init__(self, use_keyboard_fallback: bool = True):
        """
        Initialize simple voice command handler
        
        Args:
            use_keyboard_fallback: If True, use keyboard input when voice fails
        """
        self.use_keyboard_fallback = use_keyboard_fallback
        
        # Command patterns
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
        
        # Callback functions
        self.command_callbacks = {
            CommandType.FOLLOW_ME: [],
            CommandType.STOP: []
        }
        
        # Threading and control
        self.is_listening = False
        self.listening_thread = None
        self.command_queue = queue.Queue()
        
        logging.info("SimpleVoiceCommandHandler initialized")
    
    def register_callback(self, command_type: CommandType, callback: Callable):
        """Register a callback function for a specific command"""
        if callback not in self.command_callbacks[command_type]:
            self.command_callbacks[command_type].append(callback)
            logging.info(f"Registered callback for command: {command_type.value}")
    
    def _keyboard_listening_loop(self):
        """Keyboard listening loop for fallback"""
        logging.info("Keyboard command listening started")
        print("🎤 Voice commands not available. Using keyboard input:")
        print("   Press 'F' for 'follow me'")
        print("   Press 'S' for 'stop'")
        print("   Press 'Q' to quit")
        
        while self.is_listening:
            try:
                # Check for keyboard input (non-blocking)
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('f') or key == ord('F'):
                    command = CommandType.FOLLOW_ME
                    self.command_queue.put(command)
                    self._execute_command_callbacks(command)
                    print("🎯 FOLLOW ME command received!")
                
                elif key == ord('s') or key == ord('S'):
                    command = CommandType.STOP
                    self.command_queue.put(command)
                    self._execute_command_callbacks(command)
                    print("🛑 STOP command received!")
                
                elif key == ord('q') or key == ord('Q') or key == 27:  # ESC
                    break
                
                time.sleep(0.1)
                
            except Exception as e:
                logging.error(f"Error in keyboard listening: {e}")
                time.sleep(0.1)
    
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
    
    def start_listening(self):
        """Start command listening"""
        if self.is_listening:
            logging.warning("Command listening is already active")
            return
        
        self.is_listening = True
        
        if self.use_keyboard_fallback:
            self.listening_thread = threading.Thread(target=self._keyboard_listening_loop, daemon=True)
            self.listening_thread.start()
            logging.info("Keyboard command listening started")
        else:
            logging.info("Voice command listening would start here")
    
    def stop_listening(self):
        """Stop command listening"""
        if not self.is_listening:
            logging.warning("Command listening is not active")
            return
        
        self.is_listening = False
        
        if self.listening_thread and self.listening_thread.is_alive():
            self.listening_thread.join(timeout=2.0)
        
        logging.info("Command listening stopped")
    
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
        """Test if command system is working"""
        return True  # Keyboard fallback always works
    
    def cleanup(self):
        """Clean up resources"""
        self.stop_listening()
        logging.info("SimpleVoiceCommandHandler cleaned up")

def test_simple_voice_commands():
    """Test the simple voice command system"""
    print("🎤 Testing Simple Voice Commands (Keyboard Fallback)")
    print("=" * 50)
    
    def on_follow():
        print("✅ Follow command callback executed!")
    
    def on_stop():
        print("✅ Stop command callback executed!")
    
    # Initialize handler
    handler = SimpleVoiceCommandHandler(use_keyboard_fallback=True)
    
    # Register callbacks
    handler.register_callback(CommandType.FOLLOW_ME, on_follow)
    handler.register_callback(CommandType.STOP, on_stop)
    
    # Start listening
    handler.start_listening()
    
    print("\n🎮 Commands:")
    print("F - Follow me")
    print("S - Stop")
    print("Q - Quit")
    
    try:
        # Run for 20 seconds
        start_time = time.time()
        while time.time() - start_time < 20:
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\nStopping...")
    
    finally:
        handler.cleanup()
        print("✅ Test completed!")

if __name__ == "__main__":
    test_simple_voice_commands()
