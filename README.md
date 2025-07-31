# Simple Cat Detector System

A lightweight cat detector system for Raspberry Pi Zero 2 W with Camera Module v2.

## Overview

This project provides a simple cat detector system that:
- Captures video from the Raspberry Pi Camera Module
- Detects cats using an INT8 TFLite object detection model (SSDLite MobileNet V2)
- Uses libcamera for camera capture and OpenCV for image processing
- Displays the live feed with detection results via a web interface

## Requirements

- Raspberry Pi Zero 2 W (or compatible model)
- Raspberry Pi Camera Module v2 (with imx219 sensor)
- Raspberry Pi OS 64-bit (Bookworm or newer recommended)
- libcamera-utils (for camera capture)
- OpenCV (for image processing)
- tflite-runtime (TensorFlow Lite runtime for object detection)

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/gallingern/cat-detector.git
   cd cat-detector
   ```

2. Run the installation script:
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

   This will install libcamera-utils for camera capture, OpenCV for image processing, and tflite-runtime for inference.

   The system includes a pre-trained COCO INT8 quantized model that can detect cats.
3. The script will:
   - Install required dependencies
   - Set up a Python virtual environment
   - Enable the camera module
   - Create and start a systemd service

4. Access the web interface at `http://[your-pi-ip]:5000`

## Updating

To update the system:

```bash
./update.sh
```

This will pull the latest changes from the repository and restart the service.

## Service Management

The system runs as a systemd service with robust single-instance protection:

- **Check service status**: `./check_service.sh`
- **View logs**: `sudo journalctl -u cat-detector -f`
- **Restart service**: `sudo systemctl restart cat-detector`
- **Stop service**: `sudo systemctl stop cat-detector`
- **Start service**: `sudo systemctl start cat-detector`

The service includes multiple protection mechanisms to prevent multiple instances:
- Systemd service management with proper start/stop handling
- PID file management with atomic writes
- Process cleanup on service restart
- Signal handlers for graceful shutdown

## Manual Usage

If you prefer to run the system manually:

1. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```

2. Run the detector script:
   ```bash
   python start_detector.py
   ```

3. Access the web interface at `http://localhost:5000`

## Troubleshooting

- **Camera not working**: Ensure the camera is properly connected and enabled (`raspi-config`)
- **Web interface not accessible**: Check if the service is running (`systemctl status cat-detector`)
- **Detector not working**: Ensure the TFLite model is present in the models directory and tflite-runtime is installed
- **Multiple instances running**: Use `./check_service.sh` to diagnose and fix service issues
- **Service won't start**: Check logs with `sudo journalctl -u cat-detector -f`

## License

This project is licensed under the MIT License - see the LICENSE file for details.