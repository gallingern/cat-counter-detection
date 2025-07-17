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

### Detailed Deployment Guide

#### 1. Clone the Repository

SSH into your Raspberry Pi and clone the repository:

```bash
ssh pi@your-pi-ip-address
mkdir -p projects
cd projects
git clone https://github.com/gallingern/cat-counter-detection.git
cd cat-counter-detection
```

#### 2. Run the Installation Script

Execute the installation script:

```bash
chmod +x install.sh
./install.sh
```

The script will:
- Check if you're running on a Raspberry Pi
- Verify Python version (3.7+ required)
- Check for camera module
- Create required directories
- Install system dependencies
- Install Python dependencies
- Set up configuration
- Create and enable a systemd service

#### 3. Configure the System

Edit the configuration file to match your environment:

```bash
nano config.json
```

Key settings to adjust:
- `detection_roi`: Set the region of interest for your kitchen counter
- `push_notifications_enabled`: Set to `true` if you want push notifications
- `email_notifications_enabled`: Set to `true` if you want email notifications
- `email_settings`: Configure if email notifications are enabled

#### 4. Start the Service

Start the detection service:

```bash
sudo systemctl start cat-detection
```

Check the service status:

```bash
sudo systemctl status cat-detection
```

#### 5. Access the Web Interface

Open a web browser and navigate to:

```
http://your-pi-ip-address:5000
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

### Testing on Raspberry Pi

#### Basic Functionality Testing

1. **Camera Feed Test**:
   - Check if the live feed is visible in the web interface
   - Verify the camera is capturing at the expected resolution and frame rate

2. **Detection Test**:
   - Place a cat (or cat image) on your kitchen counter
   - Verify that the system detects the cat
   - Check that a notification is sent (if configured)
   - Verify the detection is logged in the history

3. **Configuration Test**:
   - Change settings in the web interface
   - Verify that changes take effect without requiring a restart

#### Advanced Testing

For comprehensive end-to-end testing, perform these additional tests:

1. **Cat Type Testing**:
   - Test with both lynx point (mostly white) and tabby (mostly brown) cats
   - Verify detection works on the black kitchen counter
   - Test different lighting conditions

2. **Notification Testing**:
   - Verify push notifications are received on your mobile device
   - Check email notifications with attached images (if configured)
   - Test notification cooldown and rate limiting

3. **Performance Testing**:
   - Monitor CPU usage (`top` command)
   - Check memory usage
   - Verify the system maintains at least 1 FPS
   - Run for 24+ hours to test stability

4. **Error Recovery Testing**:
   - Temporarily disconnect the camera and verify recovery
   - Simulate network outages for notification testing
   - Test automatic restart after reboot

### System Maintenance

#### Backup Configuration

Create a backup of your configuration and data:

```bash
./backup.sh
```

This creates a timestamped backup in the `backups/` directory.

#### Restore from Backup

Restore from a previous backup:

```bash
./restore.sh backups/cat_detection_backup_YYYYMMDD_HHMMSS.tar.gz
```

#### Update the System

Update the system software and dependencies:

```bash
./update.sh
```

#### View Logs

Check the system logs for troubleshooting:

```bash
sudo journalctl -u cat-detection -f
```

#### Troubleshooting

1. **Camera Issues**:
   - Run `vcgencmd get_camera` to verify camera detection
   - Check camera ribbon cable connection
   - Enable camera in `raspi-config` if needed

2. **Service Won't Start**:
   - Check logs: `sudo journalctl -u cat-detection -e`
   - Verify Python dependencies are installed
   - Check file permissions

3. **Detection Problems**:
   - Adjust `confidence_threshold` in config.json
   - Modify `detection_roi` to focus on the counter area
   - Check lighting conditions

4. **Web Interface Inaccessible**:
   - Verify the service is running
   - Check firewall settings
   - Confirm the Pi's IP address

5. **Performance Issues**:
   - Lower the resolution in the frame capture service
   - Reduce the target FPS
   - Enable adaptive performance in config.json

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