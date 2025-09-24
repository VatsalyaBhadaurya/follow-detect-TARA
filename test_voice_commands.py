#!/usr/bin/env python3
"""
Test Voice Commands for Tara

Simple test to verify voice commands are working with the fixed handler.
"""

import logging
import time
from tara_follow_system.voice_handler import VoiceCommandHandler, CommandType

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def on_follow_command():
    print("🎯 FOLLOW COMMAND RECEIVED!")

def on_stop_command():
    print("🛑 STOP COMMAND RECEIVED!")

def main():
    print("🎤 Testing Tara Voice Commands")
    print("=" * 40)
    
    # Initialize voice handler
    voice_handler = VoiceCommandHandler()
    
    # Register callbacks
    voice_handler.register_callback(CommandType.FOLLOW_ME, on_follow_command)
    voice_handler.register_callback(CommandType.STOP, on_stop_command)
    
    # Test microphone
    print("Testing microphone...")
    if voice_handler.test_microphone():
        print("✅ Microphone test passed!")
    else:
        print("❌ Microphone test failed!")
        return
    
    # Start listening
    print("\n🎤 Voice command listening started!")
    print("Say 'follow me' or 'stop' to test commands.")
    print("Press Ctrl+C to stop.")
    
    voice_handler.start_listening()
    
    try:
        # Run for 30 seconds
        start_time = time.time()
        while time.time() - start_time < 30:
            # Check for commands
            command = voice_handler.get_latest_command(timeout=0.1)
            if command:
                print(f"Command received: {command.value}")
            
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\nStopping...")
    
    finally:
        voice_handler.cleanup()
        print("✅ Test completed!")

if __name__ == "__main__":
    main()
