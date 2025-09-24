# Tara Person Following System

A comprehensive person following system for the Tara robot that combines computer vision, voice recognition, and intelligent movement control.

## Features

### 🎯 Person Detection & Tracking
- **YOLO-based Detection**: Uses YOLOv8 for accurate person detection
- **Multi-person Tracking**: Tracks multiple persons with unique IDs
- **Bounding Box Analysis**: Provides detailed bounding box information for distance estimation

### 📏 Distance Estimation
- **Size-based Estimation**: Estimates distance using bounding box size and known human height
- **Position-based Estimation**: Uses bounding box position for additional distance cues
- **Combined Approach**: Merges multiple estimation methods for improved accuracy
- **Calibration Support**: Supports calibration for different camera setups

### 🎤 Voice Commands
- **"Follow Me"**: Activates person following mode
- **"Stop"**: Deactivates following mode and halts robot movement
- **Real-time Recognition**: Continuous voice command listening
- **Multi-language Support**: Configurable language settings

### 🤖 Movement Control
- **PID Control**: Smooth following with proportional-integral-derivative control
- **Safe Distance Maintenance**: Maintains optimal following distance (~1 meter)
- **Search Behavior**: Automatically searches when person is lost
- **Emergency Stop**: Immediate stop when person gets too close
- **Smooth Acceleration**: Prevents sudden movements

## Installation

### Prerequisites
- Python 3.8 or higher
- OpenCV
- Camera/webcam
- Microphone (for voice commands)

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd follow-TARA
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Download YOLO model** (optional, will download automatically):
   ```bash
   # The system will automatically download yolov8n.pt on first run
   ```

## Usage

### Basic Usage

Run the system with default settings:
```bash
python main.py
```

### Advanced Usage

```bash
python main.py --camera 0 --width 640 --height 480 --fps 30 \
               --confidence 0.5 --safe-distance 1.0 \
               --save-video --video-filename output.avi
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--camera` | Camera ID | 0 |
| `--width` | Frame width | 640 |
| `--height` | Frame height | 480 |
| `--fps` | Target FPS | 30 |
| `--confidence` | Detection confidence threshold | 0.5 |
| `--safe-distance` | Safe following distance (meters) | 1.0 |
| `--no-voice` | Disable voice commands | False |
| `--no-display` | Disable video display | False |
| `--save-video` | Save output video | False |
| `--video-filename` | Output video filename | follow_output.avi |
| `--log-level` | Logging level (DEBUG/INFO/WARNING/ERROR) | INFO |

### Controls

#### Voice Commands
- **"Follow me"** - Start following the detected person
- **"Stop"** - Stop following and halt movement

#### Keyboard Controls
- **F** - Start following mode
- **S** - Stop following mode
- **Q** or **ESC** - Quit the application

## System Architecture

### Core Modules

1. **PersonDetector** (`person_detector.py`)
   - YOLO-based person detection
   - Multi-person tracking
   - Bounding box management

2. **DistanceEstimator** (`distance_estimator.py`)
   - Size-based distance estimation
   - Position-based distance estimation
   - Calibration support

3. **VoiceCommandHandler** (`voice_handler.py`)
   - Speech-to-text recognition
   - Command pattern matching
   - Callback management

4. **MovementController** (`movement_controller.py`)
   - PID-based movement control
   - Safe distance maintenance
   - Search behavior

5. **FollowPersonTask** (`follow_task.py`)
   - Main task coordination
   - State management
   - Video processing loop

### Data Flow

```
Camera → PersonDetector → DistanceEstimator → MovementController → Robot
   ↑                                                                    ↓
VoiceHandler ←→ FollowPersonTask ←→ Display/Video ←←←←←←←←←←←←←←←←←←←←←←←
```

## Configuration

### Camera Settings
```python
config = FollowTaskConfig(
    camera_id=0,           # Camera device ID
    frame_width=640,       # Video frame width
    frame_height=480,      # Video frame height
    fps=30                # Target frames per second
)
```

### Detection Settings
```python
config = FollowTaskConfig(
    confidence_threshold=0.5,  # Minimum detection confidence
    tracking_enabled=True      # Enable person tracking
)
```

### Distance Settings
```python
config = FollowTaskConfig(
    safe_distance=1.0,     # Optimal following distance (meters)
    min_distance=0.5,      # Minimum safe distance (meters)
    max_distance=3.0       # Maximum following distance (meters)
)
```

### Movement Settings
```python
config = FollowTaskConfig(
    max_linear_velocity=0.5,   # Maximum forward/backward speed (m/s)
    max_angular_velocity=1.0,  # Maximum turning speed (rad/s)
)
```

## Calibration

### Distance Calibration

For accurate distance estimation, calibrate the system with known distances:

```python
from tara_follow_system.distance_estimator import DistanceEstimator

# Create estimator
estimator = DistanceEstimator()

# Add calibration points (distance in meters)
# Place a person at known distances and add calibration points
estimator.add_calibration_point(person_bbox, 1.0, frame_width, frame_height)  # 1 meter
estimator.add_calibration_point(person_bbox, 2.0, frame_width, frame_height)  # 2 meters
estimator.add_calibration_point(person_bbox, 3.0, frame_width, frame_height)  # 3 meters

# Calibrate from collected data
estimator.calibrate_from_data()

# Save calibration
estimator.save_calibration("calibration.json")
```

## Customization

### Adding New Voice Commands

```python
from tara_follow_system.voice_handler import VoiceCommandHandler, CommandType

# Create custom command
class CustomCommand(Enum):
    WAIT = "wait"

# Add to command patterns
voice_handler.command_patterns[CustomCommand.WAIT] = ["wait", "pause", "hold"]

# Register callback
def on_wait_command():
    print("Wait command received")
    # Add your custom logic here

voice_handler.register_callback(CustomCommand.WAIT, on_wait_command)
```

### Adjusting PID Parameters

```python
# Fine-tune movement control
movement_controller.adjust_pid_parameters(
    distance_kp=1.0,    # Distance proportional gain
    distance_ki=0.1,    # Distance integral gain
    distance_kd=0.2,    # Distance derivative gain
    angle_kp=1.5,       # Angle proportional gain
    angle_ki=0.0,       # Angle integral gain
    angle_kd=0.3        # Angle derivative gain
)
```

## Troubleshooting

### Common Issues

1. **Camera not detected**
   - Check camera permissions
   - Verify camera ID with `ls /dev/video*`
   - Try different camera IDs (0, 1, 2, etc.)

2. **Poor person detection**
   - Adjust confidence threshold: `--confidence 0.3`
   - Ensure good lighting conditions
   - Check camera focus and positioning

3. **Voice commands not working**
   - Test microphone: `python -c "import speech_recognition as sr; print('Mic test passed')"`
   - Check microphone permissions
   - Adjust energy threshold in voice handler

4. **Inaccurate distance estimation**
   - Calibrate the system with known distances
   - Adjust camera FOV parameters
   - Check person height assumptions

### Performance Optimization

1. **Reduce FPS for better accuracy**:
   ```bash
   python main.py --fps 15
   ```

2. **Lower resolution for faster processing**:
   ```bash
   python main.py --width 320 --height 240
   ```

3. **Disable display for headless operation**:
   ```bash
   python main.py --no-display
   ```

## API Reference

### PersonDetector
- `detect_persons(frame)` - Detect persons in video frame
- `track_persons(frame, persons)` - Track detected persons
- `get_largest_person(persons)` - Get closest person
- `draw_detections(frame, persons)` - Draw bounding boxes

### DistanceEstimator
- `estimate_distance_size_based(person_bbox, frame_height)` - Size-based estimation
- `estimate_distance_position_based(person_bbox, frame_width, frame_height)` - Position-based estimation
- `estimate_distance_combined(person_bbox, frame_width, frame_height)` - Combined estimation
- `add_calibration_point(person_bbox, distance, frame_width, frame_height)` - Add calibration point

### VoiceCommandHandler
- `start_listening()` - Start voice command recognition
- `stop_listening()` - Stop voice command recognition
- `register_callback(command_type, callback)` - Register command callback
- `get_latest_command(timeout)` - Get latest recognized command

### MovementController
- `start_following(person_id)` - Start following mode
- `stop_following()` - Stop following mode
- `update_target(person_bbox, distance_estimate, frame_width, frame_height)` - Update movement
- `get_current_state()` - Get current movement state

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Commit your changes: `git commit -am 'Add feature'`
5. Push to the branch: `git push origin feature-name`
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- YOLO team for the excellent object detection framework
- OpenCV community for computer vision tools
- SpeechRecognition library for voice processing
- Tara robot development team for the platform

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review existing GitHub issues
3. Create a new issue with detailed information
4. Contact the development team

---

**Note**: This system is designed for educational and research purposes. Always ensure safety when operating robots, especially around people and obstacles.
#   f o l l o w - d e t e c t - T A R A  
 