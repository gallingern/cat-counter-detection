# Cat Counter Detection System

![Cat Counter Detection](docs/images/cat-illustration.png)

A smart detection system that monitors your kitchen counter for cats and notifies you when they're detected. Built specifically for Raspberry Pi with Camera Module v2.

## Overview

The Cat Counter Detection System is designed to keep your kitchen counters cat-free by automatically detecting when cats jump on them and sending you notifications. The system uses computer vision to identify both tabby and lynx point cats, even in challenging lighting conditions or on dark countertops.

### Key Features

- **Real-time Cat Detection**: Identifies cats on countertops using advanced computer vision
- **Multi-breed Recognition**: Optimized for both tabby and lynx point cats
- **Instant Notifications**: Sends alerts via multiple channels when cats are detected
- **Web Interface**: Monitor your counter and view detection history from any device
- **Energy Efficient**: Optimized for Raspberry Pi Zero W with low CPU and memory usage
- **Resilient Operation**: Includes comprehensive error handling and automatic recovery
- **Customizable Settings**: Adjust detection sensitivity, notification preferences, and more

## Installation

### Prerequisites

- Raspberry Pi (Zero W or newer) with Raspberry Pi OS
- Raspberry Pi Camera Module v2
- Internet connection for notifications
- Python 3.7+

### Quick Install

1. Clone this repository:
   ```bash
   git clone https://github.com/gallingern/cat-counter-detection.git
   cd cat-counter-detection
   ```

2. Run the installation script:
   ```bash
   ./install.sh
   ```

3. Configure your settings:
   ```bash
   nano config.json
   ```

4. Start the service:
   ```bash
   sudo systemctl start cat-detection
   ```

## Usage

### Web Interface

Access the web interface by navigating to `http://<raspberry-pi-ip>:5000` in your browser.

The interface provides:
- Live camera feed
- Detection history with images
- System status and health metrics
- Configuration options

### Notifications

The system supports multiple notification channels:
- Email notifications with attached images
- Push notifications via services like Pushover
- Custom webhook integration

Configure your preferred notification methods in the web interface or directly in the config file.

## Architecture

The system consists of several key components:

- **Frame Capture Service**: Interfaces with the camera to capture video frames
- **Detection Engine**: Processes frames to identify cats using computer vision
- **Detection Validator**: Filters and validates detections to reduce false positives
- **Storage Service**: Saves detection images and maintains detection history
- **Notification Service**: Sends alerts through configured channels
- **Web Interface**: Provides user control and monitoring capabilities
- **System Monitor**: Ensures system health and handles error recovery

## Development

### Project Structure

```
cat_counter_detection/
├── config/             # Configuration files and defaults
├── models/             # Data models and schemas
├── services/           # Core service components
│   ├── detection_engine.py
│   ├── frame_capture.py
│   ├── notification_service.py
│   └── ...
├── web/                # Web interface components
│   ├── app.py
│   └── templates/
└── utils.py            # Utility functions
```

### Running Tests

```bash
pytest tests/
```

### Performance Optimization

The system includes several optimizations for Raspberry Pi:
- Frame downsampling to reduce processing load
- Model quantization for efficient inference
- Adaptive processing based on system load
- ARM-specific optimizations

## Credits

This project was developed with the assistance of:

- **Kiro**: AI assistant and IDE that helped develop the codebase
- **Vibe Coding**: Provided guidance and best practices for the implementation
- **TensorFlow Lite**: Used for efficient model inference on Raspberry Pi
- **OpenCV**: Used for image processing and basic detection capabilities
- **Flask**: Powers the web interface
- **SQLite**: Provides lightweight database storage
- **Illustration**: The adorable cat illustration by Vibe Coding Design Team

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request