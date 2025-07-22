# Cat Detection System - Design Document

## Overview

The Cat Detection System is a lightweight, real-time cat detection application designed for Raspberry Pi Zero 2 W with Camera Module v2. It provides a web-based interface for monitoring and detecting cats in a live video stream.

## Architecture

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Camera Module │    │   Web Interface │    │  Detection      │
│   (Hardware)    │    │   (Flask App)   │    │  (OpenCV)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Camera.py     │    │   App.py        │    │  Detector.py    │
│   (Capture)     │    │   (Web Server)  │    │  (AI Detection) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────┐
                    │   Config.py     │
                    │   (Settings)    │
                    └─────────────────┘
```

## Core Components

### 1. Camera Module (`camera.py`)
**Purpose:** Manages video capture from Raspberry Pi Camera Module using libcamera-still

**Key Features:**
- Threaded video capture for non-blocking operation
- Uses libcamera-still subprocess for frame capture
- Configurable resolution, framerate, and rotation
- Frame buffering with thread-safe access
- Automatic camera initialization and cleanup

**Design Decisions:**
- Uses libcamera-still for robust Raspberry Pi camera support
- OpenCV is only used for JPEG decoding/encoding and detection
- Threaded capture loop prevents blocking the main application
- Thread-safe frame access with locks
- Configurable parameters via config.py

### 2. Detection Engine (`tflite_detector.py`)
**Purpose:** Performs cat detection using an INT8 SSDLite MobileNet V2 TFLite model

**Key Features:**
- Runs TensorFlow Lite model via tflite-runtime
- Quantization-aware preprocessing & output handling
- Configurable score threshold
- Detection interval limiting via motion checks
- Real-time annotation of detected cats

**Design Decisions:**
- TFLite chosen for efficient inference on Pi Zero 2 W
- Pre-quantized INT8 model minimizes CPU usage
- Motion gating avoids unnecessary inference
- Visual annotation for user feedback


### 3. Web Application (`app.py`)
**Purpose:** Provides web interface and coordinates system components

**Key Features:**
- Flask-based web server
- MJPEG video streaming
- Real-time status updates via AJAX
- Threaded frame processing

**Design Decisions:**
- Flask chosen for simplicity and lightweight footprint
- MJPEG streaming for real-time video display
- Separate processing thread to prevent web server blocking
- RESTful status endpoint for dynamic updates

### 4. Configuration (`config.py`)
**Purpose:** Centralized configuration management

**Key Features:**
- Camera settings (resolution, framerate, rotation)
- Detection parameters (confidence, interval)
- Web server settings (host, port, debug mode)
- File paths and system constants

## Data Flow

### 1. Video Capture Flow
```
Camera Module → camera.py → Frame Buffer → Processing Thread
```

### 2. Detection Flow
```
Frame Buffer → detector.py → Detection Results → Annotated Frame
```

### 3. Web Interface Flow
```
Annotated Frame → app.py → MJPEG Stream → Browser Display
```

### 4. Status Updates Flow
```
System Metrics → app.py → JSON API → JavaScript → UI Updates
```

## Threading Model

### Main Thread
- Flask web server
- HTTP request handling
- Status API responses

### Camera Thread
- Continuous video capture
- Frame buffering
- Camera resource management

### Processing Thread
- Frame analysis
- Detection processing
- Global state updates

## Configuration Management

### Camera Settings
- **Resolution:** 1280x720 (configurable, optimized for Camera Module v2)
- **Framerate:** 15 FPS (configurable, optimized for Camera Module v2)
- **Rotation:** 0° (configurable)

### Detection Settings
- **Confidence Threshold:** 0.4 (configurable, optimized for Camera Module v2)
- **Detection Interval:** 0.05 seconds (configurable, optimized for Camera Module v2)
- **Cascade Path:** Auto-detected with fallbacks

### Web Server Settings
- **Host:** 0.0.0.0 (all interfaces)
- **Port:** 5000 (configurable)
- **Debug Mode:** False (production)

## Error Handling

### Camera Errors
- Automatic retry on initialization failure
- Graceful degradation if camera unavailable
- Logging of camera-specific errors

### Detection Errors
- Missing or corrupt TFLite model file
- Interpreter initialization failures
- Performance monitoring and logging

### Web Server Errors
- Exception handling for all routes
- Graceful shutdown on keyboard interrupt
- Resource cleanup on exit

## Performance Considerations

### Memory Management
- Frame copying to prevent race conditions
- Automatic garbage collection
- Efficient numpy array operations

### CPU Optimization
- Detection interval limiting
- Configurable processing parameters
- Thread-safe operations

### Network Efficiency
- MJPEG compression for video streaming
- Minimal JSON payloads for status updates
- Efficient HTTP response handling

## Security Considerations

### Web Interface
- No authentication (intended for local network)
- Input validation on all endpoints
- CORS considerations for local deployment

### System Access
- Systemd service runs as user (not root)
- Limited file system access
- Secure camera resource handling

## Deployment Architecture

### Systemd Service
- Automatic startup on boot
- Automatic restart on failure
- Logging integration
- Resource management

### Virtual Environment
- Isolated Python dependencies
- Version-controlled packages
- Easy deployment and updates

### Update Mechanism
- Git-based updates
- Service restart on updates
- Health check verification

## Monitoring and Logging

### Logging Strategy
- Structured logging with timestamps
- Different log levels (INFO, ERROR, DEBUG)
- Component-specific loggers

### Health Monitoring
- Service status via systemd
- Web interface availability
- Camera and detection health checks

### Metrics Collection
- Frame processing rate
- Detection count
- System uptime
- Error rates

## Future Enhancements

### Potential Improvements
- Machine learning-based detection
- Multiple camera support
- Database logging of detections
- Mobile app interface
- Cloud integration
- Advanced analytics

### Scalability Considerations
- Microservices architecture
- Load balancing for multiple cameras
- Distributed processing
- Cloud deployment options

## Dependencies

### Hardware Dependencies
- Raspberry Pi Zero 2 W (or compatible)
- Raspberry Pi Camera Module v2 (with imx219 sensor)
- Adequate power supply
- Network connectivity

### Software Dependencies
- Python 3.7+
- OpenCV 4.x
- Flask 2.x
- numpy
- systemd (for service management)

## Testing Strategy

### Unit Testing
- Individual component testing
- Mock camera and detection testing
- Configuration validation

### Integration Testing
- End-to-end system testing
- Web interface testing
- Performance benchmarking

### Deployment Testing
- Raspberry Pi deployment testing
- Service management testing
- Update mechanism validation 