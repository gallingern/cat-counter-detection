"""
Main application for the simple cat detector system.
"""

import logging
import time
import threading
import os
import sys
import signal
from flask import Flask, Response, render_template
import cv2
import numpy as np
try:
    from . import config
    from .camera import Camera
    from .tflite_detector import TFLiteDetector as Detector
except ImportError:
    import config
    from camera import Camera
    from tflite_detector import TFLiteDetector as Detector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize camera and detector
camera = None
detector = None

# Global variables
frame_count = 0
detection_count = 0
last_frame = None
last_annotated_frame = None
processing = False
start_time = None
PID_FILE = '/tmp/cat-detector.pid'

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    global processing
    processing = False
    cleanup()
    remove_pid_file()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def check_pid_file():
    """Check if another instance is already running."""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                pid_content = f.read().strip()
                if not pid_content:
                    logger.warning("PID file is empty, removing it")
                    os.remove(PID_FILE)
                    return True
                pid = int(pid_content)
            
            # Check if process is actually running
            os.kill(pid, 0)  # This will raise OSError if process doesn't exist
            
            # Process is running, check if it's our own process
            if pid == os.getpid():
                logger.info("PID file contains our own PID, continuing")
                return True
            else:
                logger.error(f"Another instance is already running (PID: {pid})")
                return False
                
        except (ValueError, OSError) as e:
            # PID file exists but process is dead or invalid, remove stale file
            logger.info(f"Removing stale PID file: {e}")
            try:
                os.remove(PID_FILE)
            except OSError:
                pass
    return True

def create_pid_file():
    """Create PID file for this instance."""
    try:
        # Use atomic write to prevent race conditions
        temp_pid_file = PID_FILE + '.tmp'
        with open(temp_pid_file, 'w') as f:
            f.write(str(os.getpid()))
        os.rename(temp_pid_file, PID_FILE)
        logger.info(f"Created PID file with PID {os.getpid()}")
        return True
    except Exception as e:
        logger.error(f"Failed to create PID file: {e}")
        return False

def remove_pid_file():
    """Remove PID file."""
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except OSError:
        pass

def initialize():
    """Initialize the camera and detector."""
    global camera, detector
    
    try:
        logger.info("Initializing camera...")
        camera = Camera()
        camera.start()
        
        logger.info("Initializing detector...")
        detector = Detector(config.MODEL_PATH)
        
        logger.info("System initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing system: {e}")
        return False

def cleanup():
    """Clean up resources."""
    global camera
    
    if camera:
        logger.info("Stopping camera...")
        camera.stop()
    
    # Remove PID file
    remove_pid_file()

def process_frames():
    """Process frames from the camera in a loop."""
    global camera, detector, frame_count, detection_count
    global last_frame, last_annotated_frame, processing
    
    logger.info("Starting frame processing loop (ultra efficiency)")
    processing = True
    
    while processing:
        try:
            # Check if camera and detector are available
            if camera is None or detector is None:
                logger.error("Camera or detector not initialized")
                time.sleep(5.0)  # Very long sleep for ultra efficiency
                continue
            
            # Get a frame from the camera
            frame = camera.get_frame()
            if frame is None:
                time.sleep(1.0)  # Moderate sleep when no frame
                continue
            
            # Get motion detection status
            motion_detected = camera.get_motion_status()
            
            # Run detection only when motion is detected
            detections, annotated_frame = detector.detect(frame, motion_detected)
            
            # Update global variables
            frame_count += 1
            detection_count += len(detections)
            last_frame = frame
            last_annotated_frame = annotated_frame
            
            # Sleep moderately to reduce CPU usage while maintaining responsiveness
            time.sleep(1.0)
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            time.sleep(5.0)  # Very long sleep on error
    
    logger.info("Frame processing loop stopped")

def generate_frames():
    """Generate frames for the MJPEG stream."""
    global last_annotated_frame
    
    while True:
        try:
            # Wait for a frame to be available
            if last_annotated_frame is None:
                time.sleep(0.1)
                continue
            
            # Convert to JPEG
            ret, jpeg = cv2.imencode('.jpg', last_annotated_frame)
            if not ret:
                logger.error("Failed to encode frame to JPEG")
                time.sleep(0.1)
                continue
                
            frame_bytes = jpeg.tobytes()
            
            # Yield the frame in MJPEG format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        except Exception as e:
            logger.error(f"Error generating frame: {e}")
            time.sleep(0.1)

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Video streaming route."""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
def status():
    """Return system status as JSON."""
    global frame_count, detection_count, start_time
    
    uptime = time.time() - start_time if start_time else 0
    
    return {
        'frame_count': frame_count,
        'detection_count': detection_count,
        'uptime': uptime
    }

def start_app():
    """Start the application."""
    global start_time
    
    # Check if another instance is already running
    if not check_pid_file():
        logger.error("Another instance is already running. Exiting.")
        return False
    
    # Create PID file for this instance
    if not create_pid_file():
        logger.error("Failed to create PID file. Exiting.")
        return False
    
    try:
        # Initialize the system
        if not initialize():
            logger.error("Failed to initialize system")
            return False
    
    # Start the frame processing thread
    start_time = time.time()
    processing_thread = threading.Thread(target=process_frames)
    processing_thread.daemon = True
    processing_thread.start()
    
    # Try to start the Flask app with retry logic
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            # Start the Flask app
            logger.info(f"Starting web server on {config.WEB_HOST}:{config.WEB_PORT} (attempt {attempt + 1}/{max_retries})")
            app.run(host=config.WEB_HOST, port=config.WEB_PORT, debug=config.DEBUG_MODE, threaded=True)
            break  # Success, exit retry loop
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down")
            break
        except OSError as e:
            if "Address already in use" in str(e):
                logger.error(f"Port {config.WEB_PORT} is already in use (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    logger.info(f"Waiting {retry_delay} seconds before retry...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error("Max retries reached. Exiting.")
                    return False
            else:
                logger.error(f"OSError running web server: {e}")
                return False
        except Exception as e:
            logger.error(f"Error running web server: {e}")
            return False
    finally:
        # Clean up
        global processing
        processing = False
        cleanup()
        remove_pid_file()
    
    return True

if __name__ == '__main__':
    start_app()
elif __name__ == 'app':
    # When run as a module, start the app
    start_app()
