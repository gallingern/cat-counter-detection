#!/usr/bin/env python3
"""Entry point for the Cat Counter Detection system."""

import os
import sys
import logging
import time
from cat_counter_detection.detection_pipeline import DetectionPipeline
from cat_counter_detection.config_manager import ConfigManager

def main():
    """Main entry point for the detection system."""
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    logger = logging.getLogger("start_detection")
    logger.info("Starting Cat Counter Detection System")
    
    try:
        # Initialize configuration
        config_manager = ConfigManager()
        
        # Initialize and start the detection pipeline
        pipeline = DetectionPipeline(config_manager)
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
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())