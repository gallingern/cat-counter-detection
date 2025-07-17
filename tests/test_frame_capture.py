"""Unit tests for frame capture service."""

import unittest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cat_counter_detection.services.frame_capture import FrameCaptureService


class TestFrameCaptureService(unittest.TestCase):
    """Test cases for FrameCaptureService."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = FrameCaptureService(resolution=(320, 240), framerate=2.0)
    
    def tearDown(self):
        """Clean up after tests."""
        if self.service._capturing:
            self.service.stop_capture()
    
    def test_initialization(self):
        """Test service initialization."""
        self.assertEqual(self.service.resolution, (320, 240))
        self.assertEqual(self.service.framerate, 2.0)
        self.assertFalse(self.service._capturing)
        self.assertIsNone(self.service._latest_frame)
    
    def test_mock_capture_start_stop(self):
        """Test starting and stopping mock capture."""
        # Start capture
        self.service.start_capture()
        self.assertTrue(self.service._capturing)
        self.assertIsNotNone(self.service._capture_thread)
        
        # Wait a moment for frame generation
        time.sleep(0.5)
        
        # Check that frames are being generated
        frame = self.service.get_frame()
        self.assertIsNotNone(frame)
        
        # Stop capture
        self.service.stop_capture()
        self.assertFalse(self.service._capturing)
    
    def test_get_frame_when_not_capturing(self):
        """Test getting frame when not capturing."""
        frame = self.service.get_frame()
        self.assertIsNone(frame)
    
    def test_camera_info(self):
        """Test camera information retrieval."""
        info = self.service.get_camera_info()
        
        self.assertIn("available", info)
        self.assertIn("capturing", info)
        self.assertIn("resolution", info)
        self.assertIn("framerate", info)
        self.assertIn("hardware_available", info)
        self.assertIn("latest_frame_available", info)
        
        self.assertEqual(info["resolution"], (320, 240))
        self.assertEqual(info["framerate"], 2.0)
        self.assertFalse(info["capturing"])
    
    def test_set_resolution(self):
        """Test resolution change."""
        original_resolution = self.service.resolution
        new_resolution = (640, 480)
        
        self.service.set_resolution(new_resolution)
        self.assertEqual(self.service.resolution, new_resolution)
        
        # Test that same resolution doesn't trigger change
        self.service.set_resolution(new_resolution)
        self.assertEqual(self.service.resolution, new_resolution)
    
    def test_set_framerate(self):
        """Test framerate change with bounds checking."""
        # Test normal framerate
        self.service.set_framerate(5.0)
        self.assertEqual(self.service.framerate, 5.0)
        
        # Test lower bound
        self.service.set_framerate(0.05)
        self.assertEqual(self.service.framerate, 0.1)
        
        # Test upper bound
        self.service.set_framerate(50.0)
        self.assertEqual(self.service.framerate, 30.0)
    
    def test_thread_safety(self):
        """Test thread safety of frame access."""
        self.service.start_capture()
        
        # Start multiple threads accessing frames
        results = []
        
        def get_frames():
            for _ in range(10):
                frame = self.service.get_frame()
                results.append(frame is not None)
                time.sleep(0.1)
        
        threads = [threading.Thread(target=get_frames) for _ in range(3)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should have gotten some frames
        self.assertTrue(any(results))
        
        self.service.stop_capture()
    
    @patch('cat_counter_detection.services.frame_capture.CAMERA_AVAILABLE', False)
    def test_mock_mode_when_no_hardware(self):
        """Test that mock mode works when no camera hardware available."""
        service = FrameCaptureService()
        service.start_capture()
        
        # Should still be capturing in mock mode
        self.assertTrue(service._capturing)
        
        # Wait for mock frame generation
        time.sleep(0.5)
        
        frame = service.get_frame()
        self.assertIsNotNone(frame)
        
        service.stop_capture()
    
    def test_capture_loop_error_handling(self):
        """Test error handling in capture loop."""
        self.service.start_capture()
        
        # Simulate an error by setting invalid state
        original_method = self.service._generate_mock_frame
        
        def error_method():
            raise Exception("Test error")
        
        self.service._generate_mock_frame = error_method
        
        # Should continue running despite errors
        time.sleep(1.0)
        self.assertTrue(self.service._capturing)
        
        # Restore original method
        self.service._generate_mock_frame = original_method
        
        self.service.stop_capture()


if __name__ == '__main__':
    unittest.main()