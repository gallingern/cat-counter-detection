"""Flask web application for cat counter detection system."""

import logging
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from flask import Flask, render_template, jsonify, request, Response, send_file
from ..detection_pipeline import DetectionPipeline
from ..config_manager import ConfigManager

# Handle Flask import gracefully
try:
    from flask import Flask
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    Flask = None

logger = logging.getLogger(__name__)


class CatCounterWebApp:
    """Flask web application for the cat counter detection system."""
    
    def __init__(self, pipeline: Optional[DetectionPipeline] = None):
        """Initialize web application."""
        if not FLASK_AVAILABLE:
            raise ImportError("Flask is not available. Please install Flask to use the web interface.")
        
        self.app = Flask(__name__, 
                        template_folder='templates',
                        static_folder='static')
        
        # Initialize pipeline
        self.pipeline = pipeline or DetectionPipeline()
        
        # Configure Flask app
        self.app.config['SECRET_KEY'] = 'cat-counter-secret-key-change-in-production'
        self.app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
        
        # Setup routes
        self._setup_routes()
        
        logger.info("Cat Counter web application initialized")
    
    def _setup_routes(self):
        """Setup Flask routes."""
        
        @self.app.route('/')
        def index():
            """Main dashboard page."""
            return render_template('index.html')
        
        @self.app.route('/live')
        def live_feed():
            """Live camera feed page."""
            return render_template('live.html')
        
        @self.app.route('/history')
        def history():
            """Detection history page."""
            return render_template('history.html')
        
        @self.app.route('/config')
        def config():
            """Configuration page."""
            return render_template('config.html')
        
        # API Routes
        @self.app.route('/api/status')
        def api_status():
            """Get system status."""
            try:
                status = self.pipeline.get_status()
                return jsonify({
                    'success': True,
                    'data': status
                })
            except Exception as e:
                logger.error(f"Error getting status: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/start', methods=['POST'])
        def api_start():
            """Start detection pipeline."""
            try:
                success = self.pipeline.start()
                return jsonify({
                    'success': success,
                    'message': 'Pipeline started' if success else 'Pipeline already running'
                })
            except Exception as e:
                logger.error(f"Error starting pipeline: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/stop', methods=['POST'])
        def api_stop():
            """Stop detection pipeline."""
            try:
                self.pipeline.stop()
                return jsonify({
                    'success': True,
                    'message': 'Pipeline stopped'
                })
            except Exception as e:
                logger.error(f"Error stopping pipeline: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/config', methods=['GET'])
        def api_get_config():
            """Get current configuration."""
            try:
                config = self.pipeline.config_manager.get_config()
                config_dict = {
                    'confidence_threshold': config.confidence_threshold,
                    'detection_roi': config.detection_roi,
                    'monitoring_enabled': config.monitoring_enabled,
                    'monitoring_start_hour': config.monitoring_start_hour,
                    'monitoring_end_hour': config.monitoring_end_hour,
                    'push_notifications_enabled': config.push_notifications_enabled,
                    'email_notifications_enabled': config.email_notifications_enabled,
                    'notification_cooldown_minutes': config.notification_cooldown_minutes,
                    'max_storage_days': config.max_storage_days,
                    'image_quality': config.image_quality,
                    'target_fps': config.target_fps,
                    'max_cpu_usage': config.max_cpu_usage
                }
                return jsonify({
                    'success': True,
                    'data': config_dict
                })
            except Exception as e:
                logger.error(f"Error getting config: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/config', methods=['POST'])
        def api_update_config():
            """Update configuration."""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        'success': False,
                        'error': 'No data provided'
                    }), 400
                
                # Update configuration
                self.pipeline.update_configuration(**data)
                
                return jsonify({
                    'success': True,
                    'message': 'Configuration updated successfully'
                })
            except Exception as e:
                logger.error(f"Error updating config: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/detections')
        def api_detections():
            """Get detection history."""
            try:
                # Get query parameters
                limit = request.args.get('limit', 50, type=int)
                days = request.args.get('days', 7, type=int)
                
                # Get detections
                detections = self.pipeline.get_recent_detections(limit)
                
                # Convert to JSON-serializable format
                detection_data = []
                for detection in detections:
                    detection_data.append({
                        'timestamp': detection.timestamp.isoformat(),
                        'cat_count': detection.cat_count,
                        'confidence_score': detection.confidence_score,
                        'image_path': detection.image_path,
                        'bounding_boxes': [
                            {
                                'x': bbox.x,
                                'y': bbox.y,
                                'width': bbox.width,
                                'height': bbox.height,
                                'confidence': bbox.confidence
                            }
                            for bbox in detection.bounding_boxes
                        ]
                    })
                
                return jsonify({
                    'success': True,
                    'data': detection_data
                })
            except Exception as e:
                logger.error(f"Error getting detections: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/test-detection', methods=['POST'])
        def api_test_detection():
            """Trigger a test detection."""
            try:
                success = self.pipeline.trigger_test_detection()
                return jsonify({
                    'success': success,
                    'message': 'Test detection triggered' if success else 'Failed to trigger test detection'
                })
            except Exception as e:
                logger.error(f"Error triggering test detection: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/cleanup', methods=['POST'])
        def api_cleanup():
            """Trigger data cleanup."""
            try:
                self.pipeline.cleanup_old_data()
                return jsonify({
                    'success': True,
                    'message': 'Data cleanup completed'
                })
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/image/<path:filename>')
        def api_image(filename):
            """Serve detection images."""
            try:
                # Security: only allow files from images directory
                images_dir = self.pipeline.storage_service.images_dir
                file_path = os.path.join(images_dir, filename)
                
                # Check if file exists and is within images directory
                if not os.path.exists(file_path):
                    return jsonify({
                        'success': False,
                        'error': 'Image not found'
                    }), 404
                
                # Security check: ensure file is within images directory
                if not os.path.abspath(file_path).startswith(os.path.abspath(images_dir)):
                    return jsonify({
                        'success': False,
                        'error': 'Access denied'
                    }), 403
                
                return send_file(file_path)
            except Exception as e:
                logger.error(f"Error serving image {filename}: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/live-feed')
        def api_live_feed():
            """Live camera feed endpoint (MJPEG stream)."""
            def generate_frames():
                """Generate frames for MJPEG stream."""
                while True:
                    try:
                        # Get frame from pipeline
                        frame = self.pipeline.frame_capture.get_frame()
                        
                        if frame is not None:
                            # Convert frame to JPEG
                            frame_bytes = self._frame_to_jpeg(frame)
                            
                            # Yield frame in MJPEG format
                            yield (b'--frame\\r\\n'
                                   b'Content-Type: image/jpeg\\r\\n\\r\\n' + frame_bytes + b'\\r\\n')
                        else:
                            # No frame available, send placeholder
                            placeholder = self._create_placeholder_frame()
                            yield (b'--frame\\r\\n'
                                   b'Content-Type: image/jpeg\\r\\n\\r\\n' + placeholder + b'\\r\\n')
                        
                        # Control frame rate
                        import time
                        time.sleep(1.0 / max(1.0, self.pipeline.config.target_fps))
                        
                    except Exception as e:
                        logger.error(f"Error in live feed: {e}")
                        break
            
            return Response(generate_frames(),
                          mimetype='multipart/x-mixed-replace; boundary=frame')
        
        @self.app.route('/api/storage-stats')
        def api_storage_stats():
            """Get storage usage statistics."""
            try:
                stats = self.pipeline.storage_service.get_storage_usage()
                stats_dict = {
                    'total_space_mb': stats.total_space_mb,
                    'used_space_mb': stats.used_space_mb,
                    'available_space_mb': stats.available_space_mb,
                    'detection_count': stats.detection_count,
                    'oldest_detection': stats.oldest_detection,
                    'newest_detection': stats.newest_detection
                }
                return jsonify({
                    'success': True,
                    'data': stats_dict
                })
            except Exception as e:
                logger.error(f"Error getting storage stats: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/test-notifications', methods=['POST'])
        def api_test_notifications():
            """Test notification delivery."""
            try:
                results = self.pipeline.notification_service.send_test_notifications()
                return jsonify({
                    'success': True,
                    'data': results
                })
            except Exception as e:
                logger.error(f"Error testing notifications: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
    
    def _frame_to_jpeg(self, frame) -> bytes:
        """Convert frame to JPEG bytes."""
        try:
            # Handle different frame formats
            if hasattr(frame, 'shape'):  # numpy array
                try:
                    import cv2
                    # Convert to BGR for OpenCV
                    if len(frame.shape) == 3 and frame.shape[2] == 3:
                        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    else:
                        frame_bgr = frame
                    
                    # Encode as JPEG
                    _, buffer = cv2.imencode('.jpg', frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    return buffer.tobytes()
                except ImportError:
                    # Fallback without OpenCV
                    return self._create_placeholder_frame()
            else:
                # Not a numpy array, create placeholder
                return self._create_placeholder_frame()
                
        except Exception as e:
            logger.error(f"Error converting frame to JPEG: {e}")
            return self._create_placeholder_frame()
    
    def _create_placeholder_frame(self) -> bytes:
        """Create a placeholder frame when camera is not available."""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import io
            
            # Create a simple placeholder image
            img = Image.new('RGB', (640, 480), color='gray')
            draw = ImageDraw.Draw(img)
            
            # Add text
            text = "Camera Not Available"
            try:
                # Try to use a font
                font = ImageFont.load_default()
                draw.text((320, 240), text, fill='white', font=font, anchor='mm')
            except:
                # Fallback without font
                draw.text((280, 240), text, fill='white')
            
            # Convert to JPEG bytes
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            return buffer.getvalue()
            
        except ImportError:
            # Fallback: return minimal placeholder
            return b"Placeholder image data"
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """Run the Flask application."""
        logger.info(f"Starting Cat Counter web interface on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug, threaded=True)
    
    def get_app(self):
        """Get the Flask app instance for external WSGI servers."""
        return self.app


def create_app(pipeline: Optional[DetectionPipeline] = None) -> Flask:
    """Factory function to create Flask app."""
    web_app = CatCounterWebApp(pipeline)
    return web_app.get_app()


if __name__ == '__main__':
    # Run the web application directly
    app = CatCounterWebApp()
    app.run(debug=True)