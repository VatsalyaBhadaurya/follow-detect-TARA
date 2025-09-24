#!/usr/bin/env python3
"""
Offline Voice Command Test for Tara

This script tests voice commands without requiring internet connectivity.
"""

import speech_recognition as sr
import time
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_offline_voice_commands():
    """Test voice commands using offline recognition"""
    print("🎤 Testing Offline Voice Commands")
    print("=" * 40)
    
    # Initialize recognizer
    recognizer = sr.Recognizer()
    
    # Try to find a working microphone
    mic_list = sr.Microphone.list_microphone_names()
    microphone = None
    
    # Look for microphone devices
    for i, mic_name in enumerate(mic_list):
        mic_lower = mic_name.lower()
        if any(keyword in mic_lower for keyword in ['microphone', 'mic', 'input', 'capture']):
            try:
                microphone = sr.Microphone(device_index=i)
                print(f"Using microphone: {i} - {mic_name}")
                break
            except Exception as e:
                print(f"Failed to use microphone {i}: {e}")
                continue
    
    if not microphone:
        print("❌ No working microphone found!")
        return False
    
    # Adjust for ambient noise
    print("Adjusting for ambient noise...")
    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=2)
        print(f"Energy threshold set to: {recognizer.energy_threshold}")
    except Exception as e:
        print(f"❌ Calibration failed: {e}")
        return False
    
    # Test offline recognition
    print("\n🔊 Say 'follow me' or 'stop' (3 attempts):")
    
    for attempt in range(3):
        print(f"\nAttempt {attempt + 1}/3:")
        print("Listening... (say 'follow me' or 'stop')")
        
        try:
            with microphone as source:
                # Listen for audio
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=3)
            
            print("Processing audio...")
            
            # Try offline recognition with PocketSphinx
            try:
                text = recognizer.recognize_sphinx(audio)
                text = text.lower().strip()
                print(f"✅ Heard: '{text}'")
                
                # Check for commands
                if 'follow' in text and 'me' in text:
                    print("🎯 COMMAND DETECTED: Follow Me!")
                    return True
                elif 'stop' in text:
                    print("🎯 COMMAND DETECTED: Stop!")
                    return True
                else:
                    print("❓ Command not recognized")
                    
            except sr.UnknownValueError:
                print("❌ Could not understand audio")
            except Exception as e:
                print(f"❌ Recognition error: {e}")
                
        except sr.WaitTimeoutError:
            print("⏰ No audio detected")
        except Exception as e:
            print(f"❌ Listening error: {e}")
    
    print("\n❌ Voice command test failed")
    return False

def test_simple_audio_detection():
    """Simple test to see if microphone can detect any audio"""
    print("\n🔊 Simple Audio Detection Test")
    print("=" * 40)
    
    recognizer = sr.Recognizer()
    
    # Try different microphones
    mic_list = sr.Microphone.list_microphone_names()
    
    for i, mic_name in enumerate(mic_list):
        mic_lower = mic_name.lower()
        if any(keyword in mic_lower for keyword in ['microphone', 'mic', 'input', 'capture']):
            try:
                microphone = sr.Microphone(device_index=i)
                print(f"\nTesting microphone {i}: {mic_name}")
                
                # Lower the energy threshold for easier detection
                recognizer.energy_threshold = 50
                
                print("Make some noise (clap, speak, etc.)...")
                
                with microphone as source:
                    audio = recognizer.listen(source, timeout=3, phrase_time_limit=2)
                
                print("✅ Audio detected! Microphone is working.")
                
                # Try to get some basic audio info
                try:
                    # This will fail but shows we got audio
                    recognizer.recognize_sphinx(audio)
                except:
                    pass
                
                print(f"✅ Microphone {i} is working correctly!")
                return True
                
            except sr.WaitTimeoutError:
                print("❌ No audio detected")
            except Exception as e:
                print(f"❌ Error: {e}")
    
    print("\n❌ No working microphone found")
    return False

def main():
    """Main test function"""
    print("🎤 Tara Voice Command - Offline Test")
    print("=" * 50)
    
    # First test simple audio detection
    if test_simple_audio_detection():
        print("\n" + "="*50)
        # If audio detection works, test voice commands
        test_offline_voice_commands()
    else:
        print("\n💡 Troubleshooting Tips:")
        print("1. Check microphone permissions in Windows")
        print("2. Make sure microphone is not muted")
        print("3. Try running as administrator")
        print("4. Check if microphone is being used by another application")
        print("5. Try a different microphone if available")

if __name__ == "__main__":
    main()
