#!/usr/bin/env python3
"""Entry point for the Cat Counter Detection system."""

import os
import sys
import logging
import time
import traceback
from cat_counter_detection.detection_pipeline import DetectionPipeline
from cat_counter_detection.config_manager import ConfigManager

def main():
    """Main entry point for the detection system."""
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    logger = logging.getLogger("start_detection")
    logger.info("Starting Cat Counter Detection System")
    
    # Log Python version and environment info
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    
    try:
        # Check if web app module exists
        web_app_path = os.path.join("cat_counter_detection", "web", "app.py")
        if os.path.exists(web_app_path):
            logger.info(f"Web app module found at {web_app_path}")
            
            # Try to import the web app module
            try:
                logger.info("Attempting to import web app module...")
                from cat_counter_detection.web.app import app as web_app
                logger.info("Web app module imported successfully")
                
                # Start web server in a separate thread
                import threading
                def start_web_server():
                    logger.info("Starting web server on port 5000...")
                    try:
                        web_app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
                    except Exception as e:
                        logger.error(f"Web server failed to start: {e}")
                        traceback.print_exc()
                
                web_thread = threading.Thread(target=start_web_server, daemon=True)
                web_thread.start()
                logger.info("Web server thread started")
            except ImportError as e:
                logger.error(f"Failed to import web app module: {e}")
                traceback.print_exc()
        else:
            logger.warning(f"Web app module not found at {web_app_path}")
        
        # Initialize configuration
        logger.info("Initializing configuration manager...")
        config_manager = ConfigManager()
        
        # Initialize and start the detection pipeline
        logger.info("Initializing detection pipeline...")
        pipeline = DetectionPipeline(config_manager)
        
        logger.info("Starting detection pipeline...")
        if not pipeline.start():
            logger.error("Failed to start detection pipeline")
            return 1
        
        logger.info("Detection pipeline started successfully")
        
        # Keep the main thread running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            # Stop the pipeline gracefully
            pipeline.stop()
            logger.info("Detection pipeline stopped")
        
        return 0
        
    except Exception as e:
        logger.error(f"Detection system failed: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())