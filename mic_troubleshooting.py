#!/usr/bin/env python3
"""
Comprehensive Microphone Troubleshooting for Tara Voice Commands

This script tests all possible ways to get the microphone working.
"""

import speech_recognition as sr
import pyaudio
import time
import logging
import sys
import os
from typing import List, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_pyaudio_devices():
    """Test PyAudio device enumeration"""
    print("🎤 Testing PyAudio Devices")
    print("=" * 40)
    
    try:
        p = pyaudio.PyAudio()
        
        print(f"PyAudio version: {pyaudio.__version__}")
        print(f"Total devices: {p.get_device_count()}")
        
        input_devices = []
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                input_devices.append((i, info))
                print(f"  {i}: {info['name']} - {info['maxInputChannels']} channels")
        
        p.terminate()
        return input_devices
        
    except Exception as e:
        print(f"❌ PyAudio error: {e}")
        return []

def test_speech_recognition_devices():
    """Test SpeechRecognition microphone enumeration"""
    print("\n🎤 Testing SpeechRecognition Devices")
    print("=" * 40)
    
    try:
        mic_list = sr.Microphone.list_microphone_names()
        print(f"Total microphones: {len(mic_list)}")
        
        for i, name in enumerate(mic_list):
            print(f"  {i}: {name}")
            
        return mic_list
        
    except Exception as e:
        print(f"❌ SpeechRecognition error: {e}")
        return []

def test_microphone_access(device_index: int, device_name: str) -> bool:
    """Test if a specific microphone device is accessible"""
    print(f"\n🔍 Testing microphone {device_index}: {device_name}")
    
    try:
        # Test with SpeechRecognition
        recognizer = sr.Recognizer()
        microphone = sr.Microphone(device_index=device_index)
        
        # Test basic access
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
        
        print(f"✅ Device {device_index} accessible")
        return True
        
    except Exception as e:
        print(f"❌ Device {device_index} failed: {e}")
        return False

def test_audio_recording(device_index: int, device_name: str) -> bool:
    """Test if we can record audio from a specific device"""
    print(f"\n🔊 Testing audio recording from {device_index}: {device_name}")
    
    try:
        recognizer = sr.Recognizer()
        microphone = sr.Microphone(device_index=device_index)
        
        print("Listening for 2 seconds... (make some noise)")
        
        with microphone as source:
            # Lower energy threshold for easier detection
            recognizer.energy_threshold = 100
            
            audio = recognizer.listen(source, timeout=2, phrase_time_limit=2)
            
            print("✅ Audio recorded successfully")
            return True
            
    except sr.WaitTimeoutError:
        print("⏰ No audio detected (timeout)")
        return False
    except Exception as e:
        print(f"❌ Recording failed: {e}")
        return False

def test_speech_recognition_engines():
    """Test different speech recognition engines"""
    print("\n🗣️ Testing Speech Recognition Engines")
    print("=" * 40)
    
    # Test audio data
    test_audio = None
    
    # First, try to get some audio
    try:
        recognizer = sr.Recognizer()
        microphone = sr.Microphone(device_index=0)
        
        print("Recording test audio...")
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            recognizer.energy_threshold = 100
            test_audio = recognizer.listen(source, timeout=2, phrase_time_limit=2)
        
        print("✅ Test audio recorded")
        
    except Exception as e:
        print(f"❌ Could not record test audio: {e}")
        return
    
    # Test different engines
    engines = [
        ("Google Speech Recognition", lambda audio: recognizer.recognize_google(audio)),
        ("Google Speech Recognition (with key)", lambda audio: recognizer.recognize_google(audio, key=None)),
        ("PocketSphinx (Offline)", lambda audio: recognizer.recognize_sphinx(audio)),
        ("Bing Speech Recognition", lambda audio: recognizer.recognize_bing(audio, key=None)),
        ("Azure Speech Recognition", lambda audio: recognizer.recognize_azure(audio, key=None)),
        ("Houndify", lambda audio: recognizer.recognize_houndify(audio, client_id=None, client_key=None)),
        ("IBM Speech to Text", lambda audio: recognizer.recognize_ibm(audio, username=None, password=None)),
    ]
    
    for engine_name, engine_func in engines:
        try:
            print(f"Testing {engine_name}...")
            text = engine_func(test_audio)
            print(f"✅ {engine_name}: '{text}'")
        except sr.UnknownValueError:
            print(f"⚠️ {engine_name}: Could not understand audio")
        except sr.RequestError as e:
            print(f"❌ {engine_name}: {e}")
        except Exception as e:
            print(f"❌ {engine_name}: {e}")

def test_windows_audio_permissions():
    """Test Windows audio permissions"""
    print("\n🪟 Testing Windows Audio Permissions")
    print("=" * 40)
    
    try:
        # Check if we're running as administrator
        import ctypes
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        print(f"Running as administrator: {is_admin}")
        
        if not is_admin:
            print("💡 Try running as administrator for better microphone access")
        
        # Check microphone privacy settings
        print("\n🔧 Windows Microphone Privacy Settings:")
        print("1. Go to Settings > Privacy & Security > Microphone")
        print("2. Ensure 'Allow apps to access your microphone' is ON")
        print("3. Ensure 'Allow desktop apps to access your microphone' is ON")
        print("4. Check that Python/VS Code has microphone permission")
        
    except Exception as e:
        print(f"❌ Could not check Windows permissions: {e}")

def test_alternative_libraries():
    """Test alternative audio libraries"""
    print("\n📚 Testing Alternative Audio Libraries")
    print("=" * 40)
    
    # Test sounddevice
    try:
        import sounddevice as sd
        print("✅ sounddevice available")
        
        devices = sd.query_devices()
        print(f"sounddevice found {len(devices)} devices")
        
        # Find input devices
        input_devices = []
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                input_devices.append((i, device['name']))
                print(f"  Input {i}: {device['name']}")
        
        if input_devices:
            # Test recording with sounddevice
            print("\nTesting sounddevice recording...")
            sample_rate = 44100
            duration = 2
            
            print("Recording for 2 seconds...")
            audio_data = sd.rec(int(duration * sample_rate), 
                              samplerate=sample_rate, 
                              channels=1, 
                              device=input_devices[0][0])
            sd.wait()
            
            print(f"✅ sounddevice recording successful: {len(audio_data)} samples")
        
    except ImportError:
        print("❌ sounddevice not installed")
        print("   Install with: pip install sounddevice")
    except Exception as e:
        print(f"❌ sounddevice error: {e}")
    
    # Test pyaudio directly
    try:
        print("\nTesting PyAudio direct recording...")
        p = pyaudio.PyAudio()
        
        # Find input device
        input_device = None
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                input_device = i
                break
        
        if input_device is not None:
            stream = p.open(format=pyaudio.paInt16,
                           channels=1,
                           rate=44100,
                           input=True,
                           input_device_index=input_device,
                           frames_per_buffer=1024)
            
            print("Recording for 1 second...")
            frames = []
            for _ in range(44):  # 1 second at 44100 Hz
                data = stream.read(1024)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            print(f"✅ PyAudio direct recording successful: {len(frames)} frames")
        else:
            print("❌ No input device found for PyAudio")
            p.terminate()
            
    except Exception as e:
        print(f"❌ PyAudio direct recording error: {e}")

def test_voice_commands_with_different_settings():
    """Test voice commands with different recognition settings"""
    print("\n🎯 Testing Voice Commands with Different Settings")
    print("=" * 40)
    
    settings = [
        {"energy_threshold": 50, "timeout": 2, "phrase_time_limit": 3, "name": "Sensitive"},
        {"energy_threshold": 100, "timeout": 3, "phrase_time_limit": 4, "name": "Normal"},
        {"energy_threshold": 200, "timeout": 4, "phrase_time_limit": 5, "name": "Less Sensitive"},
        {"energy_threshold": 300, "timeout": 5, "phrase_time_limit": 6, "name": "Low Sensitivity"},
    ]
    
    for setting in settings:
        print(f"\nTesting {setting['name']} settings:")
        print(f"  Energy threshold: {setting['energy_threshold']}")
        print(f"  Timeout: {setting['timeout']}s")
        print(f"  Phrase time limit: {setting['phrase_time_limit']}s")
        
        try:
            recognizer = sr.Recognizer()
            microphone = sr.Microphone(device_index=0)
            
            recognizer.energy_threshold = setting['energy_threshold']
            
            print("Say 'follow me' or 'stop'...")
            
            with microphone as source:
                recognizer.adjust_for_ambient_noise(source, duration=1)
                
                audio = recognizer.listen(
                    source, 
                    timeout=setting['timeout'], 
                    phrase_time_limit=setting['phrase_time_limit']
                )
            
            # Try recognition
            try:
                text = recognizer.recognize_google(audio)
                print(f"✅ Heard: '{text}'")
                
                # Check for commands
                if 'follow' in text.lower() and 'me' in text.lower():
                    print("🎯 FOLLOW ME command detected!")
                elif 'stop' in text.lower():
                    print("🛑 STOP command detected!")
                else:
                    print("❓ Command not recognized")
                    
            except sr.UnknownValueError:
                print("❌ Could not understand audio")
            except sr.RequestError as e:
                print(f"❌ Recognition service error: {e}")
                
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    """Main troubleshooting function"""
    print("🎤 Comprehensive Microphone Troubleshooting")
    print("=" * 50)
    
    # Test 1: Device enumeration
    pyaudio_devices = test_pyaudio_devices()
    sr_devices = test_speech_recognition_devices()
    
    # Test 2: Device access
    print("\n🔍 Testing Device Access")
    print("=" * 40)
    
    working_devices = []
    for i, device_name in enumerate(sr_devices):
        if test_microphone_access(i, device_name):
            if test_audio_recording(i, device_name):
                working_devices.append((i, device_name))
    
    print(f"\n📊 Results: {len(working_devices)} working devices found")
    for device_index, device_name in working_devices:
        print(f"  ✅ {device_index}: {device_name}")
    
    # Test 3: Speech recognition engines
    if working_devices:
        test_speech_recognition_engines()
    
    # Test 4: Windows permissions
    test_windows_audio_permissions()
    
    # Test 5: Alternative libraries
    test_alternative_libraries()
    
    # Test 6: Different voice command settings
    if working_devices:
        test_voice_commands_with_different_settings()
    
    # Summary and recommendations
    print("\n📋 Summary and Recommendations")
    print("=" * 50)
    
    if working_devices:
        print("✅ Working microphones found!")
        print("\n🔧 To fix voice commands in Tara:")
        print("1. Use a working microphone device:")
        for device_index, device_name in working_devices:
            print(f"   - Device {device_index}: {device_name}")
        
        print("\n2. Try different recognition settings:")
        print("   - Lower energy threshold (50-100)")
        print("   - Increase timeout (3-5 seconds)")
        print("   - Increase phrase time limit (4-6 seconds)")
        
        print("\n3. Test with PocketSphinx (offline):")
        print("   pip install PocketSphinx")
        
        print("\n4. Check Windows microphone permissions:")
        print("   - Settings > Privacy > Microphone")
        print("   - Allow desktop apps access")
        
    else:
        print("❌ No working microphones found!")
        print("\n🔧 Troubleshooting steps:")
        print("1. Check microphone hardware connection")
        print("2. Test microphone in Windows Sound settings")
        print("3. Run as administrator")
        print("4. Check Windows microphone permissions")
        print("5. Try a different microphone")
        print("6. Restart the application")

if __name__ == "__main__":
    main()
