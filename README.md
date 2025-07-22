# Simple Cat Detection System

A lightweight cat detection system for Raspberry Pi Zero 2 W with Camera Module v2.

## Overview

This project provides a simple cat detection system that:
- Captures video from the Raspberry Pi Camera Module
- Detects cats using an INT8 TFLite object detection model (replaces OpenCV Haar cascades)
- Uses OpenCV for image processing and camera capture
- Displays the live feed with detection results via a web interface

## Requirements

- Raspberry Pi Zero 2 W (or compatible model)
- Raspberry Pi Camera Module v2 (with imx219 sensor)
- Raspberry Pi OS 64-bit (Bookworm or newer recommended)
- libcamera-utils (for camera capture)
- OpenCV (for image processing and camera capture)
- tflite-runtime (TensorFlow Lite runtime for object detection)

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/simple-cat-detection.git
   cd simple-cat-detection
   ```

2. Run the installation script:
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

   This will install libcamera-utils for camera capture, OpenCV for image processing, and tflite-runtime for inference.

   The installer will automatically download a COCO-trained INT8 quantized model that can detect cats.
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

## Manual Usage

If you prefer to run the system manually:

1. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```

2. Run the detection script:
   ```bash
   python start_detection.py
   ```

3. Access the web interface at `http://localhost:5000`

## Troubleshooting

- **Camera not working**: Ensure the camera is properly connected and enabled (`raspi-config`)
- **Web interface not accessible**: Check if the service is running (`systemctl status cat-detection`)
- **Detection not working**: Ensure the TFLite model was downloaded successfully and tflite-runtime is installed

## License

This project is licensed under the MIT License - see the LICENSE file for details.