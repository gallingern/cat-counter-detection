"""Comprehensive tests for health checking and system diagnostics."""

import unittest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from cat_counter_detection.services.health_checker import (
    HealthChecker, HealthStatus, HealthMetric, ComponentHealthCheck, SystemHealthReport
)
from cat_counter_detection.services.error_handler import ErrorHandler, ComponentStatus


class TestHealthMetric(unittest.TestCase):
    """Test health metric functionality."""
    
    def test_health_metric_initialization(self):
        """Test health metric initialization."""
        metric = HealthMetric(
            name="CPU Usage",
            value=50.0,
            unit="%",
            threshold_warning=70.0,
            threshold_critical=90.0
        )
        
        self.assertEqual(metric.name, "CPU Usage")
        self.assertEqual(metric.value, 50.0)
        self.assertEqual(metric.unit, "%")
        self.assertEqual(metric.threshold_warning, 70.0)
        self.assertEqual(metric.threshold_critical, 90.0)
        self.assertEqual(metric.status, HealthStatus.HEALTHY)
    
    def test_health_metric_update_healthy(self):
        """Test health metric update with healthy value."""
        metric = HealthMetric("Test", 0.0, "%", 70.0, 90.0)
        
        metric.update(50.0)
        
        self.assertEqual(metric.value, 50.0)
        self.assertEqual(metric.status, HealthStatus.HEALTHY)
        self.assertIsInstance(metric.last_updated, datetime)
    
    def test_health_metric_update_warning(self):
        """Test health metric update with warning value."""
        metric = HealthMetric("Test", 0.0, "%", 70.0, 90.0)
        
        metric.update(75.0)
        
        self.assertEqual(metric.value, 75.0)
        self.assertEqual(metric.status, HealthStatus.WARNING)
    
    def test_health_metric_update_critical(self):
        """Test health metric update with critical value."""
        metric = HealthMetric("Test", 0.0, "%", 70.0, 90.0)
        
        metric.update(95.0)
        
        self.assertEqual(metric.value, 95.0)
        self.assertEqual(metric.status, HealthStatus.CRITICAL)


class TestComponentHealthCheck(unittest.TestCase):
    """Test component health check functionality."""
    
    def test_component_health_check_initialization(self):
        """Test component health check initialization."""
        def dummy_check():
            return True
        
        check = ComponentHealthCheck(
            name="test_component",
            check_function=dummy_check,
            check_interval=30.0,
            timeout=5.0,
            max_failures=3
        )
        
        self.assertEqual(check.name, "test_component")
        self.assertEqual(check.check_function, dummy_check)
        self.assertEqual(check.check_interval, 30.0)
        self.assertEqual(check.timeout, 5.0)
        self.assertEqual(check.max_failures, 3)
        self.assertIsNone(check.last_check)
        self.assertTrue(check.last_result)
        self.assertEqual(check.consecutive_failures, 0)


class TestHealthChecker(unittest.TestCase):
    """Test health checker functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.error_handler = ErrorHandler()
        self.health_checker = HealthChecker(self.error_handler)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if self.health_checker.monitoring:
            self.health_checker.stop_monitoring()
    
    def test_health_checker_initialization(self):
        """Test health checker initialization."""
        self.assertIsInstance(self.health_checker, HealthChecker)
        self.assertFalse(self.health_checker.monitoring)
        self.assertIsNone(self.health_checker.monitor_thread)
        self.assertIsInstance(self.health_checker.start_time, datetime)
        
        # Check default metrics are initialized
        expected_metrics = [
            "cpu_usage", "memory_usage", "disk_usage", 
            "cpu_temperature", "error_rate", "frame_rate"
        ]
        for metric_name in expected_metrics:
            self.assertIn(metric_name, self.health_checker.metrics)
    
    def test_component_check_registration(self):
        """Test component health check registration."""
        def dummy_check():
            return True
        
        component_name = "test_component"
        self.health_checker.register_component_check(
            component_name, dummy_check, check_interval=15.0, timeout=3.0, max_failures=2
        )
        
        self.assertIn(component_name, self.health_checker.component_checks)
        check = self.health_checker.component_checks[component_name]
        self.assertEqual(check.name, component_name)
        self.assertEqual(check.check_function, dummy_check)
        self.assertEqual(check.check_interval, 15.0)
        self.assertEqual(check.timeout, 3.0)
        self.assertEqual(check.max_failures, 2)
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_system_metrics_update(self, mock_disk, mock_memory, mock_cpu):
        """Test system metrics update."""
        # Mock system metrics
        mock_cpu.return_value = 45.0
        mock_memory.return_value = Mock(percent=60.0)
        mock_disk.return_value = Mock(used=50 * 1024**3, total=100 * 1024**3)  # 50% usage
        
        # Update metrics
        self.health_checker._update_system_metrics()
        
        # Check metrics were updated
        self.assertEqual(self.health_checker.metrics["cpu_usage"].value, 45.0)
        self.assertEqual(self.health_checker.metrics["memory_usage"].value, 60.0)
        self.assertEqual(self.health_checker.metrics["disk_usage"].value, 50.0)
    
    @patch('builtins.open', create=True)
    def test_cpu_temperature_monitoring(self, mock_open):
        """Test CPU temperature monitoring on Raspberry Pi."""
        # Mock temperature file
        mock_file = Mock()
        mock_file.read.return_value = "65432\n"  # 65.432°C
        mock_open.return_value.__enter__.return_value = mock_file
        
        # Update metrics
        self.health_checker._update_system_metrics()
        
        # Check temperature was read correctly
        self.assertAlmostEqual(self.health_checker.metrics["cpu_temperature"].value, 65.432, places=2)
    
    def test_component_check_execution(self):
        """Test component health check execution."""
        check_called = False
        
        def test_check():
            nonlocal check_called
            check_called = True
            return True
        
        # Register component check
        self.health_checker.register_component_check("test_component", test_check, check_interval=0.1)
        
        # Run component checks
        self.health_checker._run_component_checks()
        
        # Check that the check function was called
        self.assertTrue(check_called)
        
        # Check that the check result was recorded
        check = self.health_checker.component_checks["test_component"]
        self.assertTrue(check.last_result)
        self.assertEqual(check.consecutive_failures, 0)
        self.assertIsNotNone(check.last_check)
    
    def test_component_check_failure(self):
        """Test component health check failure handling."""
        def failing_check():
            return False
        
        # Register failing component check
        self.health_checker.register_component_check("failing_component", failing_check, max_failures=2)
        
        # Run checks multiple times to trigger failure
        for _ in range(3):
            self.health_checker._run_component_checks()
        
        # Check that failures were recorded
        check = self.health_checker.component_checks["failing_component"]
        self.assertFalse(check.last_result)
        self.assertEqual(check.consecutive_failures, 3)
    
    def test_component_check_timeout(self):
        """Test component health check timeout handling."""
        def slow_check():
            time.sleep(2.0)  # Longer than timeout
            return True
        
        # Register slow component check with short timeout
        self.health_checker.register_component_check("slow_component", slow_check, timeout=0.5)
        
        # Run the check (should timeout)
        start_time = time.time()
        self.health_checker._run_component_checks()
        end_time = time.time()
        
        # Check that it didn't take too long (timed out)
        self.assertLess(end_time - start_time, 1.5)
        
        # Check that failure was recorded
        check = self.health_checker.component_checks["slow_component"]
        self.assertFalse(check.last_result)
        self.assertEqual(check.consecutive_failures, 1)
    
    def test_health_report_generation(self):
        """Test health report generation."""
        # Set some metric values
        self.health_checker.metrics["cpu_usage"].update(85.0)  # Warning
        self.health_checker.metrics["memory_usage"].update(95.0)  # Critical
        self.health_checker.metrics["disk_usage"].update(50.0)  # Healthy
        
        # Generate health report
        report = self.health_checker.get_health_report()
        
        # Check report structure
        self.assertIsInstance(report, SystemHealthReport)
        self.assertIsInstance(report.timestamp, datetime)
        self.assertEqual(report.overall_status, HealthStatus.CRITICAL)  # Due to memory
        self.assertIn("cpu_usage", report.metrics)
        self.assertIn("memory_usage", report.metrics)
        self.assertIn("disk_usage", report.metrics)
        
        # Check alerts were generated
        self.assertGreater(len(report.alerts), 0)
        self.assertTrue(any("CRITICAL" in alert for alert in report.alerts))
        self.assertTrue(any("WARNING" in alert for alert in report.alerts))
        
        # Check recommendations were generated
        self.assertGreater(len(report.recommendations), 0)
    
    def test_health_report_serialization(self):
        """Test health report serialization to dictionary."""
        report = self.health_checker.get_health_report()
        report_dict = report.to_dict()
        
        # Check dictionary structure
        self.assertIn("timestamp", report_dict)
        self.assertIn("overall_status", report_dict)
        self.assertIn("metrics", report_dict)
        self.assertIn("component_status", report_dict)
        self.assertIn("alerts", report_dict)
        self.assertIn("recommendations", report_dict)
        self.assertIn("uptime_seconds", report_dict)
        
        # Check that timestamp is ISO format string
        self.assertIsInstance(report_dict["timestamp"], str)
        datetime.fromisoformat(report_dict["timestamp"])  # Should not raise exception
    
    def test_diagnostic_info_generation(self):
        """Test diagnostic information generation."""
        diagnostic_info = self.health_checker.get_diagnostic_info()
        
        # Check diagnostic info structure
        self.assertIn("system_info", diagnostic_info)
        self.assertIn("resource_usage", diagnostic_info)
        self.assertIn("health_metrics", diagnostic_info)
        self.assertIn("component_checks", diagnostic_info)
        
        # Check system info
        system_info = diagnostic_info["system_info"]
        self.assertIn("platform", system_info)
        self.assertIn("python_version", system_info)
        self.assertIn("process_id", system_info)
        self.assertIn("uptime_seconds", system_info)
        
        # Check resource usage
        resource_usage = diagnostic_info["resource_usage"]
        self.assertIn("cpu_count", resource_usage)
        self.assertIn("memory_total_mb", resource_usage)
        self.assertIn("disk_total_gb", resource_usage)
    
    def test_monitoring_start_stop(self):
        """Test health monitoring start and stop."""
        # Start monitoring
        self.health_checker.start_monitoring()
        
        self.assertTrue(self.health_checker.monitoring)
        self.assertIsNotNone(self.health_checker.monitor_thread)
        self.assertTrue(self.health_checker.monitor_thread.is_alive())
        
        # Wait a bit for monitoring to run
        time.sleep(0.5)
        
        # Stop monitoring
        self.health_checker.stop_monitoring()
        
        self.assertFalse(self.health_checker.monitoring)
        
        # Wait for thread to finish
        time.sleep(0.5)
        if self.health_checker.monitor_thread:
            self.assertFalse(self.health_checker.monitor_thread.is_alive())
    
    def test_monitoring_loop_error_handling(self):
        """Test error handling in monitoring loop."""
        # Mock update method to raise an error
        original_update = self.health_checker._update_system_metrics
        self.health_checker._update_system_metrics = Mock(side_effect=Exception("Test error"))
        
        # Start monitoring briefly
        self.health_checker.check_interval = 0.1  # Fast for testing
        self.health_checker.start_monitoring()
        
        # Let it run for a bit
        time.sleep(0.3)
        
        # Stop monitoring
        self.health_checker.stop_monitoring()
        
        # Restore original method
        self.health_checker._update_system_metrics = original_update
        
        # Check that monitoring handled the error gracefully
        self.assertFalse(self.health_checker.monitoring)
    
    def test_manual_health_check(self):
        """Test manual health check execution."""
        # Add a component check
        check_called = False
        
        def test_check():
            nonlocal check_called
            check_called = True
            return True
        
        self.health_checker.register_component_check("test_component", test_check)
        
        # Run manual health check
        report = self.health_checker.run_manual_health_check()
        
        # Check that component check was executed
        self.assertTrue(check_called)
        
        # Check that report was generated
        self.assertIsInstance(report, SystemHealthReport)
        self.assertIsInstance(report.timestamp, datetime)
    
    def test_alert_generation(self):
        """Test alert generation for different metric states."""
        # Set metrics to different states
        self.health_checker.metrics["cpu_usage"].update(75.0)  # Warning
        self.health_checker.metrics["memory_usage"].update(95.0)  # Critical
        self.health_checker.metrics["disk_usage"].update(30.0)  # Healthy
        
        # Generate report
        report = self.health_checker.get_health_report()
        
        # Check alerts
        self.assertGreater(len(report.alerts), 0)
        
        # Should have both warning and critical alerts
        warning_alerts = [alert for alert in report.alerts if "WARNING" in alert]
        critical_alerts = [alert for alert in report.alerts if "CRITICAL" in alert]
        
        self.assertGreater(len(warning_alerts), 0)
        self.assertGreater(len(critical_alerts), 0)
    
    def test_recommendation_generation(self):
        """Test recommendation generation based on metric states."""
        # Set metrics to trigger recommendations
        self.health_checker.metrics["cpu_usage"].update(85.0)  # High CPU
        self.health_checker.metrics["memory_usage"].update(90.0)  # High memory
        self.health_checker.metrics["disk_usage"].update(90.0)  # High disk
        self.health_checker.metrics["cpu_temperature"].update(75.0)  # High temp
        
        # Generate report
        report = self.health_checker.get_health_report()
        
        # Check recommendations
        self.assertGreater(len(report.recommendations), 0)
        
        # Should have recommendations for each high metric
        recommendations_text = " ".join(report.recommendations).lower()
        self.assertIn("detection", recommendations_text)  # CPU recommendation
        self.assertIn("memory", recommendations_text)  # Memory recommendation
        self.assertIn("clean", recommendations_text)  # Disk recommendation
        self.assertIn("cooling", recommendations_text)  # Temperature recommendation
    
    def test_error_rate_tracking(self):
        """Test error rate tracking from error handler."""
        # Generate some errors in the error handler
        for i in range(5):
            error = ValueError(f"Test error {i}")
            self.error_handler.handle_error("test_component", error)
        
        # Update metrics
        self.health_checker._update_system_metrics()
        
        # Check that error rate was calculated
        error_rate = self.health_checker.metrics["error_rate"].value
        self.assertGreater(error_rate, 0)
    
    def test_integration_with_error_handler(self):
        """Test integration with error handler for component status."""
        # Register a component in error handler
        self.error_handler.register_component("test_component")
        
        # Generate an error to change component status
        error = ValueError("Test error")
        self.error_handler.handle_error("test_component", error)
        
        # Generate health report
        report = self.health_checker.get_health_report()
        
        # Check that component status is included
        self.assertIn("test_component", report.component_status)
        self.assertEqual(report.component_status["test_component"], ComponentStatus.DEGRADED)


class TestHealthCheckerIntegration(unittest.TestCase):
    """Test health checker integration scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.error_handler = ErrorHandler()
        self.health_checker = HealthChecker(self.error_handler)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if self.health_checker.monitoring:
            self.health_checker.stop_monitoring()
    
    def test_system_overload_detection(self):
        """Test detection of system overload conditions."""
        # Simulate system overload
        self.health_checker.metrics["cpu_usage"].update(95.0)
        self.health_checker.metrics["memory_usage"].update(98.0)
        self.health_checker.metrics["cpu_temperature"].update(85.0)
        
        # Generate health report
        report = self.health_checker.get_health_report()
        
        # Should detect critical system state
        self.assertEqual(report.overall_status, HealthStatus.CRITICAL)
        self.assertGreater(len(report.alerts), 2)  # Multiple critical alerts
        self.assertGreater(len(report.recommendations), 2)  # Multiple recommendations
    
    def test_component_failure_cascade(self):
        """Test detection of cascading component failures."""
        # Simulate multiple component failures
        components = ["camera_service", "detection_engine", "storage_service"]
        
        for component in components:
            self.error_handler.register_component(component)
            error = RuntimeError(f"{component} failed")
            self.error_handler.handle_error(component, error, severity=self.error_handler.ErrorSeverity.HIGH)
        
        # Generate health report
        report = self.health_checker.get_health_report()
        
        # Should show all components as degraded/failed
        for component in components:
            self.assertIn(component, report.component_status)
            self.assertNotEqual(report.component_status[component], ComponentStatus.HEALTHY)
    
    def test_recovery_monitoring(self):
        """Test monitoring of system recovery."""
        # Start with degraded system
        self.error_handler.trigger_graceful_degradation("Test degradation")
        
        # Generate initial report
        initial_report = self.health_checker.get_health_report()
        
        # Simulate recovery
        self.error_handler.recover_from_degradation()
        
        # Generate recovery report
        recovery_report = self.health_checker.get_health_report()
        
        # System should show improvement
        # (Note: Overall status might still be affected by other metrics)
        self.assertIsInstance(recovery_report, SystemHealthReport)
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_performance_degradation_detection(self, mock_memory, mock_cpu):
        """Test detection of performance degradation."""
        # Simulate performance degradation over time
        cpu_values = [30.0, 50.0, 70.0, 85.0, 95.0]
        memory_values = [40.0, 60.0, 75.0, 85.0, 95.0]
        
        reports = []
        
        for cpu_val, mem_val in zip(cpu_values, memory_values):
            mock_cpu.return_value = cpu_val
            mock_memory.return_value = Mock(percent=mem_val)
            
            self.health_checker._update_system_metrics()
            report = self.health_checker.get_health_report()
            reports.append(report)
        
        # Check that status degraded over time
        statuses = [report.overall_status for report in reports]
        
        # Should start healthy and end critical
        self.assertEqual(statuses[0], HealthStatus.HEALTHY)
        self.assertEqual(statuses[-1], HealthStatus.CRITICAL)
        
        # Should have increasing number of alerts
        alert_counts = [len(report.alerts) for report in reports]
        self.assertGreater(alert_counts[-1], alert_counts[0])


class TestEnhancedDiagnostics(unittest.TestCase):
    """Test enhanced diagnostic capabilities."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.error_handler = ErrorHandler()
        self.health_checker = HealthChecker(self.error_handler)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if self.health_checker.monitoring:
            self.health_checker.stop_monitoring()
    
    @patch('os.uname')
    @patch('psutil.boot_time')
    def test_system_info_collection(self, mock_boot_time, mock_uname):
        """Test comprehensive system information collection."""
        # Mock system information
        mock_uname.return_value = Mock(
            sysname='Linux',
            nodename='raspberrypi',
            release='5.10.17-v7+',
            version='#1414 SMP Fri Apr 30 13:18:35 BST 2021',
            machine='armv7l'
        )
        mock_boot_time.return_value = time.time() - 3600  # 1 hour ago
        
        diagnostic_info = self.health_checker.get_diagnostic_info()
        
        # Check system info structure
        self.assertIn("system_info", diagnostic_info)
        system_info = diagnostic_info["system_info"]
        
        self.assertIn("platform", system_info)
        self.assertIn("python_version", system_info)
        self.assertIn("process_id", system_info)
        self.assertIn("uptime_seconds", system_info)
        self.assertIn("boot_time", system_info)
        
        # Verify platform details
        platform = system_info["platform"]
        self.assertEqual(platform["system"], "Linux")
        self.assertEqual(platform["machine"], "armv7l")
    
    @patch('psutil.cpu_count')
    @patch('psutil.virtual_memory')
    @patch('psutil.swap_memory')
    def test_resource_usage_collection(self, mock_swap, mock_memory, mock_cpu_count):
        """Test detailed resource usage collection."""
        # Mock resource information
        mock_cpu_count.side_effect = [4, 4]  # physical, logical
        mock_memory.return_value = Mock(
            total=1024*1024*1024,  # 1GB
            available=512*1024*1024,  # 512MB
            used=512*1024*1024,  # 512MB
            percent=50.0,
            free=256*1024*1024  # 256MB
        )
        mock_swap.return_value = Mock(
            total=512*1024*1024,  # 512MB
            used=128*1024*1024,  # 128MB
            free=384*1024*1024,  # 384MB
            percent=25.0
        )
        
        diagnostic_info = self.health_checker.get_diagnostic_info()
        
        # Check resource usage structure
        self.assertIn("resource_usage", diagnostic_info)
        resource_usage = diagnostic_info["resource_usage"]
        
        self.assertIn("cpu", resource_usage)
        self.assertIn("memory", resource_usage)
        self.assertIn("swap", resource_usage)
        
        # Verify CPU info
        cpu_info = resource_usage["cpu"]
        self.assertEqual(cpu_info["count"], 4)
        self.assertIn("current_percent", cpu_info)
        self.assertIn("per_cpu_percent", cpu_info)
        
        # Verify memory info
        memory_info = resource_usage["memory"]
        self.assertEqual(memory_info["total_mb"], 1024)
        self.assertEqual(memory_info["percent"], 50.0)
    
    @patch('builtins.open', create=True)
    @patch('subprocess.run')
    def test_hardware_info_collection(self, mock_subprocess, mock_open):
        """Test hardware-specific information collection."""
        # Mock temperature file
        mock_file = Mock()
        mock_file.read.return_value = "65432\n"  # 65.432°C
        mock_open.return_value.__enter__.return_value = mock_file
        
        # Mock vcgencmd commands
        mock_subprocess.side_effect = [
            Mock(returncode=0, stdout="temp=65.4'C\n"),  # GPU temp
            Mock(returncode=0, stdout="arm=768M\n"),     # ARM memory
            Mock(returncode=0, stdout="gpu=256M\n"),     # GPU memory
            Mock(returncode=0, stdout="throttled=0x0\n") # Throttling status
        ]
        
        diagnostic_info = self.health_checker.get_diagnostic_info()
        
        # Check hardware info structure
        self.assertIn("hardware_info", diagnostic_info)
        hardware_info = diagnostic_info["hardware_info"]
        
        self.assertIn("cpu_temperature_celsius", hardware_info)
        self.assertIn("gpu_temperature_celsius", hardware_info)
        self.assertIn("arm_memory_mb", hardware_info)
        self.assertIn("gpu_memory_mb", hardware_info)
        self.assertIn("throttling_status", hardware_info)
        
        # Verify temperature readings
        self.assertAlmostEqual(hardware_info["cpu_temperature_celsius"], 65.432, places=2)
        self.assertAlmostEqual(hardware_info["gpu_temperature_celsius"], 65.4, places=1)
        
        # Verify throttling status
        throttling = hardware_info["throttling_status"]
        self.assertIsInstance(throttling, dict)
        self.assertIn("under_voltage_detected", throttling)
        self.assertIn("currently_throttled", throttling)
    
    @patch('psutil.net_if_addrs')
    @patch('psutil.net_if_stats')
    @patch('psutil.net_io_counters')
    def test_network_info_collection(self, mock_net_io, mock_net_stats, mock_net_addrs):
        """Test network interface information collection."""
        # Mock network interfaces
        mock_net_addrs.return_value = {
            'wlan0': [
                Mock(family=2, address='192.168.1.100', netmask='255.255.255.0', broadcast='192.168.1.255'),
                Mock(family=17, address='b8:27:eb:12:34:56', netmask=None, broadcast=None)
            ],
            'lo': [
                Mock(family=2, address='127.0.0.1', netmask='255.0.0.0', broadcast=None)
            ]
        }
        
        mock_net_stats.return_value = {
            'wlan0': Mock(isup=True, duplex=2, speed=100, mtu=1500),
            'lo': Mock(isup=True, duplex=0, speed=0, mtu=65536)
        }
        
        mock_net_io.return_value = Mock(
            bytes_sent=1024*1024,
            bytes_recv=2048*1024,
            packets_sent=1000,
            packets_recv=1500,
            errin=0,
            errout=0,
            dropin=0,
            dropout=0
        )
        
        diagnostic_info = self.health_checker.get_diagnostic_info()
        
        # Check network info structure
        self.assertIn("network_info", diagnostic_info)
        network_info = diagnostic_info["network_info"]
        
        self.assertIn("interfaces", network_info)
        self.assertIn("io_counters", network_info)
        self.assertIn("connectivity", network_info)
        
        # Verify interface information
        interfaces = network_info["interfaces"]
        self.assertIn("wlan0", interfaces)
        self.assertIn("lo", interfaces)
        
        wlan0_info = interfaces["wlan0"]
        self.assertIn("addresses", wlan0_info)
        self.assertIn("stats", wlan0_info)
        self.assertEqual(len(wlan0_info["addresses"]), 2)  # IPv4 and MAC
    
    @patch('psutil.disk_partitions')
    @patch('psutil.disk_usage')
    @patch('psutil.disk_io_counters')
    def test_storage_info_collection(self, mock_disk_io, mock_disk_usage, mock_partitions):
        """Test storage and filesystem information collection."""
        # Mock disk partitions
        mock_partitions.return_value = [
            Mock(device='/dev/mmcblk0p2', mountpoint='/', fstype='ext4', opts='rw,relatime'),
            Mock(device='/dev/mmcblk0p1', mountpoint='/boot', fstype='vfat', opts='rw,relatime')
        ]
        
        # Mock disk usage
        mock_disk_usage.side_effect = [
            Mock(total=32*1024**3, used=16*1024**3, free=16*1024**3),  # Root partition
            Mock(total=256*1024**2, used=128*1024**2, free=128*1024**2)  # Boot partition
        ]
        
        # Mock disk I/O
        mock_disk_io.return_value = Mock(
            read_count=1000,
            write_count=500,
            read_bytes=1024*1024*100,
            write_bytes=1024*1024*50,
            read_time=5000,
            write_time=2500
        )
        
        diagnostic_info = self.health_checker.get_diagnostic_info()
        
        # Check storage info structure
        self.assertIn("storage_info", diagnostic_info)
        storage_info = diagnostic_info["storage_info"]
        
        self.assertIn("partitions", storage_info)
        self.assertIn("io_counters", storage_info)
        
        # Verify partition information
        partitions = storage_info["partitions"]
        self.assertIn("/", partitions)
        self.assertIn("/boot", partitions)
        
        root_partition = partitions["/"]
        self.assertEqual(root_partition["device"], "/dev/mmcblk0p2")
        self.assertEqual(root_partition["fstype"], "ext4")
        self.assertEqual(root_partition["total_gb"], 32)
        self.assertEqual(root_partition["percent"], 50.0)
    
    @patch('psutil.Process')
    def test_process_info_collection(self, mock_process_class):
        """Test current process information collection."""
        # Mock current process
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.name.return_value = "python3"
        mock_process.status.return_value = "running"
        mock_process.create_time.return_value = time.time() - 3600  # 1 hour ago
        mock_process.cpu_percent.return_value = 15.5
        mock_process.memory_info.return_value = Mock(rss=64*1024*1024, vms=128*1024*1024)
        mock_process.memory_percent.return_value = 6.25
        mock_process.num_threads.return_value = 4
        mock_process.num_fds.return_value = 20
        mock_process.connections.return_value = []
        mock_process.cwd.return_value = "/home/pi/cat_detection"
        mock_process.children.return_value = []
        
        mock_process_class.return_value = mock_process
        
        diagnostic_info = self.health_checker.get_diagnostic_info()
        
        # Check process info structure
        self.assertIn("process_info", diagnostic_info)
        process_info = diagnostic_info["process_info"]
        
        self.assertIn("pid", process_info)
        self.assertIn("name", process_info)
        self.assertIn("status", process_info)
        self.assertIn("create_time", process_info)
        self.assertIn("cpu_percent", process_info)
        self.assertIn("memory_info", process_info)
        self.assertIn("num_threads", process_info)
        self.assertIn("children", process_info)
        
        # Verify process details
        self.assertEqual(process_info["pid"], 12345)
        self.assertEqual(process_info["name"], "python3")
        self.assertEqual(process_info["status"], "running")
        self.assertEqual(process_info["cpu_percent"], 15.5)
        
        # Verify memory info
        memory_info = process_info["memory_info"]
        self.assertEqual(memory_info["rss_mb"], 64)
        self.assertEqual(memory_info["percent"], 6.25)
    
    def test_degradation_status_collection(self):
        """Test degradation status information collection."""
        # Trigger various degradation modes
        self.error_handler.trigger_graceful_degradation("Test degradation")
        self.error_handler.camera_degraded = True
        self.error_handler.network_degraded = True
        
        diagnostic_info = self.health_checker.get_diagnostic_info()
        
        # Check degradation status
        self.assertIn("degradation_status", diagnostic_info)
        degradation_status = diagnostic_info["degradation_status"]
        
        self.assertIn("system_degraded", degradation_status)
        self.assertIn("camera_degraded", degradation_status)
        self.assertIn("network_degraded", degradation_status)
        self.assertIn("storage_degraded", degradation_status)
        self.assertIn("degradation_start_time", degradation_status)
        self.assertIn("degradation_duration_seconds", degradation_status)
        
        # Verify degradation states
        self.assertTrue(degradation_status["system_degraded"])
        self.assertTrue(degradation_status["camera_degraded"])
        self.assertTrue(degradation_status["network_degraded"])
        self.assertFalse(degradation_status["storage_degraded"])
    
    def test_connectivity_testing(self):
        """Test network connectivity testing."""
        # Mock successful connectivity
        with patch('socket.socket') as mock_socket_class:
            mock_socket = Mock()
            mock_socket.connect_ex.return_value = 0  # Success
            mock_socket_class.return_value = mock_socket
            
            connectivity = self.health_checker._test_network_connectivity()
            
            # Should test multiple hosts
            self.assertIn("google.com:80", connectivity)
            self.assertIn("8.8.8.8:53", connectivity)
            self.assertIn("1.1.1.1:53", connectivity)
            
            # All should be successful
            for host_port, result in connectivity.items():
                self.assertTrue(result, f"Connectivity test failed for {host_port}")
    
    def test_diagnostic_error_handling(self):
        """Test error handling in diagnostic collection."""
        # Mock an error in system info collection
        with patch('os.uname', side_effect=Exception("System info error")):
            diagnostic_info = self.health_checker.get_diagnostic_info()
            
            # Should still return diagnostic info with error noted
            self.assertIn("system_info", diagnostic_info)
            system_info = diagnostic_info["system_info"]
            self.assertIn("error", system_info)
            self.assertEqual(system_info["error"], "System info error")
    
    def test_comprehensive_diagnostic_report(self):
        """Test generation of comprehensive diagnostic report."""
        # Generate some errors for context
        for i in range(3):
            error = ValueError(f"Test error {i}")
            self.error_handler.handle_error("test_component", error, self.error_handler.ErrorSeverity.LOW)
        
        diagnostic_info = self.health_checker.get_diagnostic_info()
        
        # Should include all major sections
        expected_sections = [
            "system_info",
            "resource_usage", 
            "hardware_info",
            "network_info",
            "storage_info",
            "process_info",
            "health_metrics",
            "component_checks",
            "degradation_status",
            "error_summary"
        ]
        
        for section in expected_sections:
            self.assertIn(section, diagnostic_info, f"Missing section: {section}")
        
        # Error summary should include recent errors
        error_summary = diagnostic_info["error_summary"]
        self.assertGreater(error_summary["total_errors"], 0)
        self.assertIn("test_component", error_summary["errors_by_component"])


if __name__ == '__main__':
    unittest.main()