#!/usr/bin/env python3
"""
Microphone Test Script for Tara Voice Commands

This script helps you test and find the working microphone for voice commands.
"""

import speech_recognition as sr
import time

def test_microphone(mic_index, mic_name):
    """Test a specific microphone"""
    print(f"\nTesting microphone {mic_index}: {mic_name}")
    
    try:
        recognizer = sr.Recognizer()
        microphone = sr.Microphone(device_index=mic_index)
        
        # Adjust for ambient noise
        print("Adjusting for ambient noise...")
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
        
        print(f"Energy threshold: {recognizer.energy_threshold}")
        print("Listening for 3 seconds... Say something!")
        
        with microphone as source:
            audio = recognizer.listen(source, timeout=3, phrase_time_limit=3)
        
        print("Processing audio...")
        try:
            text = recognizer.recognize_google(audio)
            print(f"✅ SUCCESS! Heard: '{text}'")
            return True
        except sr.UnknownValueError:
            print("❌ Could not understand audio")
            return False
        except sr.RequestError as e:
            print(f"❌ Speech recognition service error: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error with microphone {mic_index}: {e}")
        return False

def main():
    """Main function to test all microphones"""
    print("🎤 Tara Voice Command - Microphone Test")
    print("=" * 50)
    
    # Get list of microphones
    mic_list = sr.Microphone.list_microphone_names()
    
    print(f"Found {len(mic_list)} audio devices:")
    for i, mic in enumerate(mic_list):
        print(f"  {i}: {mic}")
    
    # Test microphones that look like input devices
    input_mics = []
    for i, mic in enumerate(mic_list):
        mic_lower = mic.lower()
        if any(keyword in mic_lower for keyword in ['microphone', 'mic', 'input', 'capture']):
            input_mics.append((i, mic))
    
    print(f"\n🎯 Testing {len(input_mics)} potential input microphones:")
    
    working_mics = []
    for mic_index, mic_name in input_mics:
        if test_microphone(mic_index, mic_name):
            working_mics.append((mic_index, mic_name))
    
    print(f"\n📊 Results:")
    print(f"Total microphones found: {len(mic_list)}")
    print(f"Input microphones tested: {len(input_mics)}")
    print(f"Working microphones: {len(working_mics)}")
    
    if working_mics:
        print(f"\n✅ Working microphones:")
        for mic_index, mic_name in working_mics:
            print(f"  {mic_index}: {mic_name}")
        
        print(f"\n💡 To use a specific microphone, modify the voice_handler.py:")
        print(f"   self.microphone = sr.Microphone(device_index={working_mics[0][0]})")
    else:
        print(f"\n❌ No working microphones found!")
        print(f"   Check your microphone permissions and connections.")
        print(f"   Try running as administrator if needed.")

if __name__ == "__main__":
    main()
