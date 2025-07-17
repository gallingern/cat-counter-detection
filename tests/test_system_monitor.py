"""Unit tests for system monitor service."""

import unittest
import time
from unittest.mock import Mock, patch
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cat_counter_detection.services.system_monitor import SystemMonitor, ServiceStatus


class TestSystemMonitor(unittest.TestCase):
    """Test cases for SystemMonitor."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.monitor = SystemMonitor(
            max_cpu_usage=80.0,
            max_memory_usage=80.0,
            max_temperature=80.0,
            check_interval_seconds=1
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        if self.monitor.monitoring_active:
            self.monitor.stop_monitoring()
    
    def test_initialization(self):
        """Test monitor initialization."""
        self.assertEqual(self.monitor.max_cpu_usage, 80.0)
        self.assertEqual(self.monitor.max_memory_usage, 80.0)
        self.assertEqual(self.monitor.max_temperature, 80.0)
        self.assertEqual(self.monitor.check_interval_seconds, 1)
        self.assertFalse(self.monitor.monitoring_active)
        self.assertIsNone(self.monitor.monitoring_thread)
        self.assertEqual(len(self.monitor.services), 0)
    
    def test_register_service(self):
        """Test service registration."""
        # Create mock health check and restart functions
        health_check = Mock(return_value=True)
        restart_func = Mock(return_value=True)
        
        # Register service
        self.monitor.register_service(
            service_name="test_service",
            health_check=health_check,
            restart_func=restart_func,
            check_interval_seconds=30
        )
        
        # Check that service was registered
        self.assertIn("test_service", self.monitor.services)
        service = self.monitor.services["test_service"]
        self.assertEqual(service["name"], "test_service")
        self.assertEqual(service["health_check"], health_check)
        self.assertEqual(service["restart_func"], restart_func)
        self.assertEqual(service["check_interval"], 30)
        self.assertEqual(service["status"], ServiceStatus.UNKNOWN)
        self.assertIsNone(service["last_check"])
        self.assertIsNone(service["last_restart"])
        self.assertEqual(service["restart_count"], 0)
    
    def test_is_service_healthy(self):
        """Test service health check."""
        # Register service with mock health check
        health_check = Mock(return_value=True)
        self.monitor.register_service(
            service_name="test_service",
            health_check=health_check
        )
        
        # Check service health
        is_healthy = self.monitor.is_service_healthy("test_service")
        self.assertTrue(is_healthy)
        health_check.assert_called_once()
        
        # Check that service status was updated
        service = self.monitor.services["test_service"]
        self.assertEqual(service["status"], ServiceStatus.HEALTHY)
        self.assertIsNotNone(service["last_check"])
        
        # Test unhealthy service
        health_check.reset_mock()
        health_check.return_value = False
        
        is_healthy = self.monitor.is_service_healthy("test_service")
        self.assertFalse(is_healthy)
        health_check.assert_called_once()
        
        # Check that service status was updated
        service = self.monitor.services["test_service"]
        self.assertEqual(service["status"], ServiceStatus.CRITICAL)
    
    def test_restart_service(self):
        """Test service restart."""
        # Register service with mock restart function
        restart_func = Mock(return_value=True)
        self.monitor.register_service(
            service_name="test_service",
            health_check=Mock(return_value=False),
            restart_func=restart_func
        )
        
        # Restart service
        success = self.monitor.restart_service("test_service")
        self.assertTrue(success)
        restart_func.assert_called_once()
        
        # Check that service status was updated
        service = self.monitor.services["test_service"]
        self.assertEqual(service["restart_count"], 1)
        self.assertIsNotNone(service["last_restart"])
        
        # Check recovery history
        self.assertEqual(len(self.monitor.recovery_history), 1)
        event = self.monitor.recovery_history[0]
        self.assertEqual(event["service"], "test_service")
        self.assertTrue(event["success"])
        
        # Test failed restart
        restart_func.reset_mock()
        restart_func.return_value = False
        
        success = self.monitor.restart_service("test_service")
        self.assertFalse(success)
        restart_func.assert_called_once()
        
        # Check that service status was updated
        service = self.monitor.services["test_service"]
        self.assertEqual(service["restart_count"], 2)
        
        # Check recovery history
        self.assertEqual(len(self.monitor.recovery_history), 2)
        event = self.monitor.recovery_history[1]
        self.assertEqual(event["service"], "test_service")
        self.assertFalse(event["success"])
    
    def test_trigger_garbage_collection(self):
        """Test garbage collection trigger."""
        with patch('gc.collect') as mock_gc:
            self.monitor.trigger_garbage_collection()
            mock_gc.assert_called_once()
    
    def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring."""
        # Start monitoring
        self.monitor.start_monitoring()
        self.assertTrue(self.monitor.monitoring_active)
        self.assertIsNotNone(self.monitor.monitoring_thread)
        self.assertTrue(self.monitor.monitoring_thread.is_alive())
        
        # Stop monitoring
        self.monitor.stop_monitoring()
        self.assertFalse(self.monitor.monitoring_active)
        
        # Wait for thread to stop
        time.sleep(0.1)
        self.assertFalse(self.monitor.monitoring_thread.is_alive())
    
    def test_get_system_health(self):
        """Test system health information retrieval."""
        health_info = self.monitor.get_system_health()
        
        self.assertIn("system", health_info)
        self.assertIn("services", health_info)
        self.assertIn("monitoring", health_info)
        self.assertIn("thresholds", health_info)
        self.assertIn("recovery_history", health_info)
        
        # Check system stats
        system_stats = health_info["system"]
        self.assertIn("cpu_usage", system_stats)
        self.assertIn("memory_usage", system_stats)
        self.assertIn("temperature", system_stats)
        self.assertIn("disk_usage", system_stats)
        self.assertIn("uptime", system_stats)
        
        # Check monitoring info
        monitoring_info = health_info["monitoring"]
        self.assertIn("active", monitoring_info)
        self.assertIn("check_interval", monitoring_info)
        self.assertEqual(monitoring_info["active"], self.monitor.monitoring_active)
        self.assertEqual(monitoring_info["check_interval"], self.monitor.check_interval_seconds)
        
        # Check thresholds
        thresholds = health_info["thresholds"]
        self.assertEqual(thresholds["max_cpu_usage"], self.monitor.max_cpu_usage)
        self.assertEqual(thresholds["max_memory_usage"], self.monitor.max_memory_usage)
        self.assertEqual(thresholds["max_temperature"], self.monitor.max_temperature)
    
    def test_get_service_status(self):
        """Test service status retrieval."""
        # Register service
        self.monitor.register_service(
            service_name="test_service",
            health_check=Mock(return_value=True)
        )
        
        # Check service health to update status
        self.monitor.is_service_healthy("test_service")
        
        # Get service status
        status = self.monitor.get_service_status("test_service")
        
        self.assertEqual(status["name"], "test_service")
        self.assertEqual(status["status"], ServiceStatus.HEALTHY)
        self.assertIsNotNone(status["last_check"])
        self.assertEqual(status["restart_count"], 0)
        
        # Test non-existent service
        status = self.monitor.get_service_status("nonexistent")
        self.assertIn("error", status)
    
    def test_set_thresholds(self):
        """Test threshold updates."""
        # Update thresholds
        self.monitor.set_thresholds(
            max_cpu_usage=90.0,
            max_memory_usage=85.0,
            max_temperature=85.0
        )
        
        self.assertEqual(self.monitor.max_cpu_usage, 90.0)
        self.assertEqual(self.monitor.max_memory_usage, 85.0)
        self.assertEqual(self.monitor.max_temperature, 85.0)
        
        # Test bounds checking
        self.monitor.set_thresholds(
            max_cpu_usage=110.0,  # Should be clamped to 100
            max_memory_usage=-10.0  # Should be clamped to 0
        )
        
        self.assertEqual(self.monitor.max_cpu_usage, 100.0)
        self.assertEqual(self.monitor.max_memory_usage, 0.0)
    
    @patch('cat_counter_detection.services.system_monitor.PSUTIL_AVAILABLE', False)
    def test_fallbacks_without_psutil(self):
        """Test fallback behavior when psutil is not available."""
        # Create monitor without psutil
        monitor = SystemMonitor()
        
        # Test resource usage functions
        self.assertEqual(monitor.get_cpu_usage(), 0.0)
        self.assertEqual(monitor.get_memory_usage(), 0.0)
        self.assertEqual(monitor.get_temperature(), 0.0)
        self.assertEqual(monitor._get_disk_usage(), 0.0)
        self.assertEqual(monitor._get_uptime(), 0.0)
    
    def test_monitoring_loop_with_services(self):
        """Test monitoring loop with registered services."""
        # Register services with mock functions
        healthy_check = Mock(return_value=True)
        unhealthy_check = Mock(return_value=False)
        restart_func = Mock(return_value=True)
        
        self.monitor.register_service(
            service_name="healthy_service",
            health_check=healthy_check,
            check_interval_seconds=1
        )
        
        self.monitor.register_service(
            service_name="unhealthy_service",
            health_check=unhealthy_check,
            restart_func=restart_func,
            check_interval_seconds=1
        )
        
        # Start monitoring
        self.monitor.start_monitoring()
        
        # Wait for monitoring loop to run
        time.sleep(2)
        
        # Stop monitoring
        self.monitor.stop_monitoring()
        
        # Check that health checks were called
        healthy_check.assert_called()
        unhealthy_check.assert_called()
        
        # Check that restart was attempted for unhealthy service
        restart_func.assert_called()
        
        # Check service statuses
        self.assertEqual(self.monitor.services["healthy_service"]["status"], ServiceStatus.HEALTHY)
        self.assertEqual(self.monitor.services["unhealthy_service"]["status"], ServiceStatus.CRITICAL)
    
    def test_recovery_history_limit(self):
        """Test recovery history size limit."""
        # Set small history limit for testing
        self.monitor.max_history_entries = 3
        
        # Add multiple recovery events
        for i in range(5):
            self.monitor._add_recovery_event(
                service_name=f"service_{i}",
                success=True
            )
        
        # Check that history is limited to max entries
        self.assertEqual(len(self.monitor.recovery_history), 3)
        
        # Check that oldest entries were removed
        self.assertEqual(self.monitor.recovery_history[0]["service"], "service_2")
        self.assertEqual(self.monitor.recovery_history[1]["service"], "service_3")
        self.assertEqual(self.monitor.recovery_history[2]["service"], "service_4")


if __name__ == '__main__':
    unittest.main()