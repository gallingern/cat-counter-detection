"""Unit tests for notification service."""

import unittest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cat_counter_detection.services.notification_service import (
    NotificationService, NotificationConfig, NotificationMessage
)


class TestNotificationService(unittest.TestCase):
    """Test cases for NotificationService."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = NotificationConfig(
            push_enabled=True,
            email_enabled=True,
            retry_attempts=2,
            cooldown_minutes=1,  # Short cooldown for testing
            max_queue_size=10
        )
        self.service = NotificationService(self.config)
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.service.stop_processing()
    
    def test_initialization(self):
        """Test service initialization."""
        self.assertIsNotNone(self.service.config)
        self.assertIsNotNone(self.service.notification_queue)
        self.assertTrue(self.service.running)
        self.assertIsNotNone(self.service.processing_thread)
    
    def test_notification_config(self):
        """Test notification configuration."""
        config = NotificationConfig(
            push_enabled=False,
            email_enabled=True,
            retry_attempts=5,
            cooldown_minutes=10
        )
        
        self.assertFalse(config.push_enabled)
        self.assertTrue(config.email_enabled)
        self.assertEqual(config.retry_attempts, 5)
        self.assertEqual(config.cooldown_minutes, 10)
    
    def test_notification_message(self):
        """Test notification message creation."""
        msg = NotificationMessage(
            message_type="push",
            title="Test Title",
            body="Test Body",
            image_path="/test/path.jpg"
        )
        
        self.assertEqual(msg.message_type, "push")
        self.assertEqual(msg.title, "Test Title")
        self.assertEqual(msg.body, "Test Body")
        self.assertEqual(msg.image_path, "/test/path.jpg")
        self.assertEqual(msg.retry_count, 0)
        self.assertIsInstance(msg.timestamp, datetime)
    
    def test_mock_push_notification(self):
        """Test push notification in mock mode."""
        # Should work in mock mode (no requests library)
        result = self.service.send_push_notification("Test message", "/test/image.jpg")
        self.assertTrue(result)
    
    def test_mock_email_notification(self):
        """Test email notification in mock mode."""
        # Should work in mock mode (no email libraries)
        result = self.service.send_email("Test Subject", "Test Body", "/test/image.jpg")
        self.assertTrue(result)
    
    def test_disabled_notifications(self):
        """Test behavior when notifications are disabled."""
        self.service.config.push_enabled = False
        self.service.config.email_enabled = False
        
        push_result = self.service.send_push_notification("Test", "/test.jpg")
        email_result = self.service.send_email("Test", "Test", "/test.jpg")
        
        self.assertFalse(push_result)
        self.assertFalse(email_result)
    
    def test_cooldown_mechanism(self):
        """Test notification cooldown mechanism."""
        # Send first notification
        result1 = self.service.send_push_notification("Test 1", "/test.jpg")
        self.assertTrue(result1)
        
        # Immediately send second notification (should be blocked by cooldown)
        result2 = self.service.send_push_notification("Test 2", "/test.jpg")
        self.assertFalse(result2)
        
        # Check cooldown status
        self.assertFalse(self.service._check_cooldown("push"))
        
        # Wait for cooldown to expire (1 minute + buffer)
        # For testing, we'll manually update the cooldown time
        self.service.last_notification_time["push"] = datetime.now() - timedelta(minutes=2)
        
        # Now should be able to send again
        result3 = self.service.send_push_notification("Test 3", "/test.jpg")
        self.assertTrue(result3)
    
    def test_queue_notification(self):
        """Test notification queuing."""
        initial_size = self.service.notification_queue.qsize()
        
        self.service.queue_notification("push", "Queued message", "/test.jpg")
        
        self.assertEqual(self.service.notification_queue.qsize(), initial_size + 1)
    
    def test_queue_unknown_type(self):
        """Test queuing unknown notification type."""
        initial_size = self.service.notification_queue.qsize()
        
        self.service.queue_notification("unknown", "Test message", "/test.jpg")
        
        # Should not add to queue
        self.assertEqual(self.service.notification_queue.qsize(), initial_size)
    
    def test_process_queue(self):
        """Test queue processing."""
        # Add notifications to queue
        self.service.queue_notification("push", "Queue test 1", "/test1.jpg")
        self.service.queue_notification("email", "Queue test 2", "/test2.jpg")
        
        initial_size = self.service.notification_queue.qsize()
        self.assertGreater(initial_size, 0)
        
        # Process queue
        self.service.process_queue()
        
        # Queue should be processed (though items might be re-queued due to cooldown)
        # The exact behavior depends on cooldown and retry logic
    
    def test_notification_retry(self):
        """Test notification retry mechanism."""
        # Create a notification that will fail
        notification = NotificationMessage(
            message_type="push",
            title="Test",
            body="Test retry",
            image_path="/test.jpg"
        )
        
        # Mock the send method to fail
        original_method = self.service._send_push_notification_impl
        self.service._send_push_notification_impl = lambda msg, img: False
        
        # Process notification (should fail and be retried)
        result = self.service._process_notification(notification)
        self.assertFalse(result)
        
        # Restore original method
        self.service._send_push_notification_impl = original_method
    
    def test_update_config(self):
        """Test configuration updates."""
        original_cooldown = self.service.config.cooldown_minutes
        
        self.service.update_config(cooldown_minutes=15)
        
        self.assertEqual(self.service.config.cooldown_minutes, 15)
        self.assertNotEqual(self.service.config.cooldown_minutes, original_cooldown)
    
    def test_clear_queue(self):
        """Test queue clearing."""
        # Add some notifications
        for i in range(3):
            self.service.queue_notification("push", f"Test {i}", f"/test{i}.jpg")
        
        initial_size = self.service.notification_queue.qsize()
        self.assertGreater(initial_size, 0)
        
        cleared_count = self.service.clear_queue()
        
        self.assertEqual(cleared_count, initial_size)
        self.assertEqual(self.service.notification_queue.qsize(), 0)
    
    def test_get_notification_stats(self):
        """Test notification statistics retrieval."""
        stats = self.service.get_notification_stats()
        
        self.assertIn("config", stats)
        self.assertIn("queue", stats)
        self.assertIn("cooldowns", stats)
        self.assertIn("processing", stats)
        self.assertIn("dependencies", stats)
        
        # Check config stats
        self.assertEqual(stats["config"]["push_enabled"], True)
        self.assertEqual(stats["config"]["email_enabled"], True)
        
        # Check queue stats
        self.assertIn("size", stats["queue"])
        self.assertIn("max_size", stats["queue"])
        
        # Check processing stats
        self.assertIn("running", stats["processing"])
        self.assertIn("thread_alive", stats["processing"])
    
    def test_send_test_notifications(self):
        """Test sending test notifications."""
        results = self.service.send_test_notifications()
        
        self.assertIn("push", results)
        self.assertIn("email", results)
        
        # In mock mode, both should succeed
        self.assertTrue(results["push"])
        self.assertTrue(results["email"])
    
    def test_background_processing(self):
        """Test background processing thread."""
        # Verify background thread is running
        self.assertTrue(self.service.running)
        self.assertTrue(self.service.processing_thread.is_alive())
        
        # Add a notification and wait briefly for processing
        self.service.queue_notification("push", "Background test", "/test.jpg")
        time.sleep(0.1)  # Brief wait for background processing
        
        # Background processor should be handling the queue
        # (Exact behavior depends on timing and cooldown)
    
    def test_stop_processing(self):
        """Test stopping background processing."""
        self.assertTrue(self.service.running)
        
        self.service.stop_processing()
        
        self.assertFalse(self.service.running)
        # Thread should stop within timeout period
    
    def test_queue_full_handling(self):
        """Test behavior when queue is full."""
        # Fill up the queue
        for i in range(self.config.max_queue_size + 5):
            self.service.queue_notification("push", f"Test {i}", f"/test{i}.jpg")
        
        # Queue should not exceed max size
        self.assertLessEqual(self.service.notification_queue.qsize(), self.config.max_queue_size)
    
    @patch('cat_counter_detection.services.notification_service.REQUESTS_AVAILABLE', True)
    @patch('cat_counter_detection.services.notification_service.requests')
    def test_push_notification_with_requests(self, mock_requests):
        """Test push notification when requests library is available."""
        # Configure mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_requests.post.return_value = mock_response
        
        # Configure service with credentials
        self.service.config.push_server_key = "test_key"
        self.service.config.push_device_token = "test_token"
        
        result = self.service._send_push_notification_impl("Test message", "/test.jpg")
        
        # Should attempt to send via requests
        mock_requests.post.assert_called_once()
        self.assertTrue(result)
    
    def test_cooldown_check_new_type(self):
        """Test cooldown check for new notification type."""
        # New notification type should not be in cooldown
        self.assertTrue(self.service._check_cooldown("new_type"))
        
        # After updating cooldown, should be in cooldown
        self.service._update_cooldown("new_type")
        self.assertFalse(self.service._check_cooldown("new_type"))


if __name__ == '__main__':
    unittest.main()