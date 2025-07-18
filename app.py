"""
Main application for the simple cat detection system.
"""

import logging
import time
import threading
from flask import Flask, Response, render_template
import cv2
import numpy as np
from . import config
from .camera import Camera
from .detector import CatDetector

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

def initialize():
    """Initialize the camera and detector."""
    global camera, detector
    
    try:
        logger.info("Initializing camera...")
        camera = Camera()
        camera.start()
        
        logger.info("Initializing detector...")
        detector = CatDetector()
        
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

def process_frames():
    """Process frames from the camera in a loop."""
    global camera, detector, frame_count, detection_count
    global last_frame, last_annotated_frame, processing
    
    logger.info("Starting frame processing loop")
    processing = True
    
    while processing:
        try:
            # Get a frame from the camera
            frame = camera.get_frame()
            if frame is None:
                time.sleep(0.1)
                continue
            
            # Run detection
            detections, annotated_frame = detector.detect(frame)
            
            # Update global variables
            frame_count += 1
            detection_count += len(detections)
            last_frame = frame
            last_annotated_frame = annotated_frame
            
            # Sleep briefly to reduce CPU usage
            time.sleep(0.01)
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            time.sleep(1.0)
    
    logger.info("Frame processing loop stopped")

def generate_frames():
    """Generate frames for the MJPEG stream."""
    global last_annotated_frame
    
    while True:
        # Wait for a frame to be available
        if last_annotated_frame is None:
            time.sleep(0.1)
            continue
        
        # Convert to JPEG
        ret, jpeg = cv2.imencode('.jpg', last_annotated_frame)
        frame_bytes = jpeg.tobytes()
        
        # Yield the frame in MJPEG format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

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
    global frame_count, detection_count
    
    return {
        'frame_count': frame_count,
        'detection_count': detection_count,
        'uptime': time.time() - start_time
    }

def start_app():
    """Start the application."""
    global start_time
    
    # Initialize the system
    if not initialize():
        logger.error("Failed to initialize system")
        return False
    
    # Start the frame processing thread
    start_time = time.time()
    processing_thread = threading.Thread(target=process_frames)
    processing_thread.daemon = True
    processing_thread.start()
    
    try:
        # Start the Flask app
        logger.info(f"Starting web server on {config.WEB_HOST}:{config.WEB_PORT}")
        app.run(host=config.WEB_HOST, port=config.WEB_PORT, debug=config.DEBUG_MODE, threaded=True)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down")
    except Exception as e:
        logger.error(f"Error running web server: {e}")
    finally:
        # Clean up
        global processing
        processing = False
        cleanup()
    
    return True

if __name__ == '__main__':
    start_app()