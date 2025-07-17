"""Comprehensive tests for error handling and recovery mechanisms."""

import unittest
import time
import threading
import socket
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from cat_counter_detection.services.error_handler import (
    ErrorHandler, ErrorSeverity, ComponentStatus, ErrorRecord, ComponentHealth,
    with_error_handling, retry_on_error, global_error_handler
)


class TestErrorHandler(unittest.TestCase):
    """Test error handler functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.error_handler = ErrorHandler(max_error_history=100)
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.error_handler.clear_error_history()
    
    def test_error_handler_initialization(self):
        """Test error handler initialization."""
        self.assertIsInstance(self.error_handler, ErrorHandler)
        self.assertEqual(len(self.error_handler.error_history), 0)
        self.assertEqual(len(self.error_handler.component_health), 0)
        self.assertFalse(self.error_handler.system_degraded)
        self.assertFalse(self.error_handler.camera_degraded)
        self.assertFalse(self.error_handler.network_degraded)
        self.assertFalse(self.error_handler.storage_degraded)
    
    def test_component_registration(self):
        """Test component registration for health monitoring."""
        component_name = "test_component"
        self.error_handler.register_component(component_name, max_recovery_attempts=5)
        
        self.assertIn(component_name, self.error_handler.component_health)
        health = self.error_handler.component_health[component_name]
        self.assertEqual(health.name, component_name)
        self.assertEqual(health.status, ComponentStatus.HEALTHY)
        self.assertEqual(health.max_recovery_attempts, 5)
    
    def test_recovery_strategy_registration(self):
        """Test recovery strategy registration."""
        def mock_recovery(error_record):
            return True
        
        error_type = "TestError"
        self.error_handler.register_recovery_strategy(error_type, mock_recovery)
        
        self.assertIn(error_type, self.error_handler.recovery_strategies)
        self.assertEqual(self.error_handler.recovery_strategies[error_type], mock_recovery)
    
    def test_error_handling_basic(self):
        """Test basic error handling."""
        component = "test_component"
        error = ValueError("Test error")
        
        # Handle the error
        result = self.error_handler.handle_error(component, error, ErrorSeverity.MEDIUM)
        
        # Check error was recorded
        self.assertEqual(len(self.error_handler.error_history), 1)
        error_record = self.error_handler.error_history[0]
        self.assertEqual(error_record.component, component)
        self.assertEqual(error_record.error_type, "ValueError")
        self.assertEqual(error_record.message, "Test error")
        self.assertEqual(error_record.severity, ErrorSeverity.MEDIUM)
        
        # Check component health was updated
        self.assertIn(component, self.error_handler.component_health)
        health = self.error_handler.component_health[component]
        self.assertEqual(health.error_count, 1)
        self.assertEqual(health.status, ComponentStatus.DEGRADED)
    
    def test_error_handling_with_recovery(self):
        """Test error handling with successful recovery."""
        component = "test_component"
        error = RuntimeError("Test runtime error")
        
        # Mock recovery strategy
        def mock_recovery(error_record):
            return True
        
        self.error_handler.register_recovery_strategy("RuntimeError", mock_recovery)
        
        # Handle the error
        result = self.error_handler.handle_error(component, error, ErrorSeverity.MEDIUM)
        
        # Check recovery was attempted and successful
        self.assertTrue(result)
        error_record = self.error_handler.error_history[0]
        self.assertTrue(error_record.recovery_attempted)
        self.assertTrue(error_record.recovery_successful)
        
        # Check component was marked as recovered
        health = self.error_handler.component_health[component]
        self.assertEqual(health.status, ComponentStatus.HEALTHY)
    
    def test_error_handling_failed_recovery(self):
        """Test error handling with failed recovery."""
        component = "test_component"
        error = RuntimeError("Test runtime error")
        
        # Mock failing recovery strategy
        def mock_recovery(error_record):
            return False
        
        self.error_handler.register_recovery_strategy("RuntimeError", mock_recovery)
        
        # Handle the error
        result = self.error_handler.handle_error(component, error, ErrorSeverity.MEDIUM)
        
        # Check recovery was attempted but failed
        self.assertFalse(result)
        error_record = self.error_handler.error_history[0]
        self.assertTrue(error_record.recovery_attempted)
        self.assertFalse(error_record.recovery_successful)
    
    def test_critical_error_handling(self):
        """Test handling of critical errors."""
        component = "test_component"
        error = Exception("Critical system error")
        
        # Handle critical error
        self.error_handler.handle_error(component, error, ErrorSeverity.CRITICAL)
        
        # Check component status is set to failed
        health = self.error_handler.component_health[component]
        self.assertEqual(health.status, ComponentStatus.FAILED)
    
    def test_error_pattern_detection(self):
        """Test error pattern detection."""
        component = "test_component"
        error_type = "ValueError"
        
        # Generate multiple similar errors
        for i in range(6):
            error = ValueError(f"Test error {i}")
            self.error_handler.handle_error(component, error, ErrorSeverity.LOW)
        
        # Check pattern was detected
        pattern_key = f"{component}:{error_type}"
        self.assertIn(pattern_key, self.error_handler.error_patterns)
        self.assertEqual(self.error_handler.error_patterns[pattern_key], 6)
    
    def test_duplicate_error_consolidation(self):
        """Test that duplicate errors are consolidated."""
        component = "test_component"
        error = ValueError("Duplicate error")
        
        # Handle same error multiple times within 60 seconds
        for i in range(3):
            self.error_handler.handle_error(component, error, ErrorSeverity.LOW)
        
        # Should only have one error record with occurrence count of 3
        self.assertEqual(len(self.error_handler.error_history), 1)
        error_record = self.error_handler.error_history[0]
        self.assertEqual(error_record.occurrence_count, 3)
    
    def test_graceful_degradation(self):
        """Test graceful degradation functionality."""
        reason = "System overload"
        
        # Trigger degradation
        self.error_handler.trigger_graceful_degradation(reason)
        
        # Check degradation state
        self.assertTrue(self.error_handler.is_system_degraded())
        self.assertIsNotNone(self.error_handler.degradation_start_time)
        
        degradation_info = self.error_handler.get_degradation_info()
        self.assertTrue(degradation_info["system_degraded"])
        self.assertIsNotNone(degradation_info["degradation_start_time"])
    
    def test_recovery_from_degradation(self):
        """Test recovery from system degradation."""
        # Trigger degradation
        self.error_handler.trigger_graceful_degradation("Test degradation")
        self.assertTrue(self.error_handler.is_system_degraded())
        
        # Attempt recovery (should succeed with no failed components)
        result = self.error_handler.recover_from_degradation()
        
        # Check recovery was successful
        self.assertTrue(result)
        self.assertFalse(self.error_handler.is_system_degraded())
        self.assertFalse(self.error_handler.camera_degraded)
        self.assertFalse(self.error_handler.network_degraded)
        self.assertFalse(self.error_handler.storage_degraded)
    
    def test_recovery_callbacks(self):
        """Test recovery callback functionality."""
        callback_called = False
        
        def recovery_callback():
            nonlocal callback_called
            callback_called = True
        
        component = "test_component"
        self.error_handler.register_recovery_callback(component, recovery_callback)
        
        # Trigger degradation and recovery
        self.error_handler.trigger_graceful_degradation("Test")
        self.error_handler.recover_from_degradation()
        
        # Check callback was called
        self.assertTrue(callback_called)
    
    def test_camera_error_recovery(self):
        """Test camera-specific error recovery."""
        component = "camera_service"
        error = RuntimeError("Camera initialization failed")
        
        # Handle camera error
        result = self.error_handler.handle_error(component, error, ErrorSeverity.HIGH)
        
        # Check camera degradation was enabled
        self.assertTrue(self.error_handler.camera_degraded)
    
    def test_network_error_recovery(self):
        """Test network-specific error recovery."""
        component = "notification_service"
        error = ConnectionError("Network connection failed")
        
        # Handle network error
        result = self.error_handler.handle_error(component, error, ErrorSeverity.MEDIUM)
        
        # Check network degradation was enabled
        self.assertTrue(self.error_handler.network_degraded)
    
    def test_storage_error_recovery(self):
        """Test storage-specific error recovery."""
        component = "storage_service"
        error = PermissionError("Permission denied")
        
        # Handle storage error
        result = self.error_handler.handle_error(component, error, ErrorSeverity.MEDIUM)
        
        # Check storage degradation was enabled
        self.assertTrue(self.error_handler.storage_degraded)
    
    def test_max_recovery_attempts(self):
        """Test maximum recovery attempts limit."""
        component = "test_component"
        self.error_handler.register_component(component, max_recovery_attempts=2)
        
        # Mock failing recovery strategy
        def mock_recovery(error_record):
            return False
        
        self.error_handler.register_recovery_strategy("ValueError", mock_recovery)
        
        # Exceed max recovery attempts
        for i in range(3):
            error = ValueError(f"Test error {i}")
            result = self.error_handler.handle_error(component, error, ErrorSeverity.MEDIUM)
        
        # Check that recovery was not attempted on the third error
        health = self.error_handler.component_health[component]
        self.assertEqual(health.recovery_attempts, 2)  # Should not exceed max
    
    def test_error_summary_generation(self):
        """Test error summary generation."""
        # Generate various errors
        components = ["comp1", "comp2", "comp3"]
        error_types = ["ValueError", "RuntimeError", "IOError"]
        severities = [ErrorSeverity.LOW, ErrorSeverity.MEDIUM, ErrorSeverity.HIGH]
        
        for i in range(10):
            component = components[i % len(components)]
            error_type = error_types[i % len(error_types)]
            severity = severities[i % len(severities)]
            
            if error_type == "ValueError":
                error = ValueError(f"Test error {i}")
            elif error_type == "RuntimeError":
                error = RuntimeError(f"Test error {i}")
            else:
                error = IOError(f"Test error {i}")
            
            self.error_handler.handle_error(component, error, severity)
        
        # Get error summary
        summary = self.error_handler.get_error_summary(hours=1)
        
        # Check summary structure
        self.assertIn("total_errors", summary)
        self.assertIn("unique_errors", summary)
        self.assertIn("errors_by_component", summary)
        self.assertIn("errors_by_type", summary)
        self.assertIn("errors_by_severity", summary)
        self.assertIn("component_health", summary)
        
        # Check counts
        self.assertEqual(summary["total_errors"], 10)
        self.assertEqual(len(summary["errors_by_component"]), 3)
        self.assertEqual(len(summary["errors_by_type"]), 3)
    
    def test_error_history_cleanup(self):
        """Test error history cleanup functionality."""
        # Add some errors
        for i in range(10):
            error = ValueError(f"Test error {i}")
            self.error_handler.handle_error("test_component", error, ErrorSeverity.LOW)
        
        self.assertEqual(len(self.error_handler.error_history), 10)
        
        # Clear all history
        cleared_count = self.error_handler.clear_error_history()
        
        self.assertEqual(cleared_count, 10)
        self.assertEqual(len(self.error_handler.error_history), 0)
    
    def test_component_health_status(self):
        """Test component health status tracking."""
        component = "test_component"
        
        # Initially healthy
        self.error_handler.register_component(component)
        health = self.error_handler.get_component_health(component)[component]
        self.assertTrue(health.is_healthy())
        self.assertTrue(health.can_recover())
        
        # After error, should be degraded
        error = ValueError("Test error")
        self.error_handler.handle_error(component, error, ErrorSeverity.MEDIUM)
        
        health = self.error_handler.get_component_health(component)[component]
        self.assertFalse(health.is_healthy())
        self.assertEqual(health.status, ComponentStatus.DEGRADED)


class TestErrorHandlingDecorators(unittest.TestCase):
    """Test error handling decorators."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.error_handler = ErrorHandler()
    
    def test_with_error_handling_decorator_success(self):
        """Test error handling decorator with successful function."""
        @with_error_handling("test_component", ErrorSeverity.MEDIUM, self.error_handler)
        def test_function():
            return "success"
        
        result = test_function()
        self.assertEqual(result, "success")
        self.assertEqual(len(self.error_handler.error_history), 0)
    
    def test_with_error_handling_decorator_error(self):
        """Test error handling decorator with error."""
        @with_error_handling("test_component", ErrorSeverity.MEDIUM, self.error_handler)
        def test_function():
            raise ValueError("Test error")
        
        result = test_function()
        self.assertIsNone(result)  # Should return None for non-critical errors
        self.assertEqual(len(self.error_handler.error_history), 1)
    
    def test_with_error_handling_decorator_critical_error(self):
        """Test error handling decorator with critical error."""
        @with_error_handling("test_component", ErrorSeverity.CRITICAL, self.error_handler)
        def test_function():
            raise ValueError("Critical error")
        
        # Critical errors should be re-raised
        with self.assertRaises(ValueError):
            test_function()
        
        self.assertEqual(len(self.error_handler.error_history), 1)
    
    def test_retry_on_error_decorator_success(self):
        """Test retry decorator with successful function."""
        call_count = 0
        
        @retry_on_error(max_attempts=3, delay=0.1)
        def test_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = test_function()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 1)
    
    def test_retry_on_error_decorator_eventual_success(self):
        """Test retry decorator with eventual success."""
        call_count = 0
        
        @retry_on_error(max_attempts=3, delay=0.1)
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        result = test_function()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)
    
    def test_retry_on_error_decorator_all_attempts_fail(self):
        """Test retry decorator when all attempts fail."""
        call_count = 0
        
        @retry_on_error(max_attempts=3, delay=0.1)
        def test_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent error")
        
        with self.assertRaises(ValueError):
            test_function()
        
        self.assertEqual(call_count, 3)
    
    def test_retry_on_error_decorator_backoff(self):
        """Test retry decorator with exponential backoff."""
        call_times = []
        
        @retry_on_error(max_attempts=3, delay=0.1, backoff_factor=2.0)
        def test_function():
            call_times.append(time.time())
            raise ValueError("Test error")
        
        start_time = time.time()
        with self.assertRaises(ValueError):
            test_function()
        
        # Check that delays increased exponentially
        self.assertEqual(len(call_times), 3)
        if len(call_times) >= 2:
            delay1 = call_times[1] - call_times[0]
            self.assertGreaterEqual(delay1, 0.1)  # First delay
        if len(call_times) >= 3:
            delay2 = call_times[2] - call_times[1]
            self.assertGreaterEqual(delay2, 0.2)  # Second delay (doubled)


class TestErrorRecoveryScenarios(unittest.TestCase):
    """Test specific error recovery scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.error_handler = ErrorHandler()
    
    def test_camera_disconnection_recovery(self):
        """Test recovery from camera disconnection."""
        component = "frame_capture"
        error = OSError("Camera device not found")
        
        # Handle camera disconnection error
        result = self.error_handler.handle_error(component, error, ErrorSeverity.HIGH)
        
        # Check that camera degradation mode was enabled
        self.assertTrue(self.error_handler.camera_degraded)
        
        # Check component status
        health = self.error_handler.component_health[component]
        self.assertEqual(health.status, ComponentStatus.DEGRADED)
    
    def test_camera_init_error_recovery(self):
        """Test recovery from camera initialization errors."""
        component = "frame_capture"
        error = RuntimeError("Camera initialization failed")
        
        # Mock the camera device check
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            
            # Handle camera init error
            result = self.error_handler.handle_error(component, error, ErrorSeverity.HIGH)
            
            # Check that recovery was attempted
            self.assertTrue(self.error_handler.camera_degraded)
    
    def test_camera_capture_error_recovery(self):
        """Test recovery from camera capture errors."""
        component = "frame_capture"
        
        # Register specific recovery strategy
        def mock_capture_recovery(error_record):
            return True
        
        self.error_handler.register_recovery_strategy("CaptureError", mock_capture_recovery)
        
        # Create a custom error type
        class CaptureError(Exception):
            pass
        
        error = CaptureError("Frame capture failed")
        
        # Handle capture error
        result = self.error_handler.handle_error(component, error, ErrorSeverity.MEDIUM)
        
        # Check that recovery was successful
        self.assertTrue(result)
    
    def test_network_timeout_recovery(self):
        """Test recovery from network timeout."""
        component = "notification_service"
        error = TimeoutError("Network request timed out")
        
        # Handle network timeout error
        result = self.error_handler.handle_error(component, error, ErrorSeverity.MEDIUM)
        
        # Check that network degradation mode was enabled
        self.assertTrue(self.error_handler.network_degraded)
    
    def test_network_connectivity_check(self):
        """Test network connectivity checking."""
        # Mock successful network check
        with patch('socket.gethostbyname') as mock_dns, \
             patch('subprocess.run') as mock_subprocess:
            
            mock_dns.return_value = '8.8.8.8'
            mock_subprocess.return_value.returncode = 0
            
            # Test connectivity check
            result = self.error_handler._check_network_connectivity()
            self.assertTrue(result)
    
    def test_network_connectivity_failure(self):
        """Test network connectivity failure detection."""
        # Mock failed network check
        with patch('socket.gethostbyname') as mock_dns:
            mock_dns.side_effect = socket.gaierror("DNS resolution failed")
            
            # Test connectivity check
            result = self.error_handler._check_network_connectivity()
            self.assertFalse(result)
    
    def test_storage_permission_recovery(self):
        """Test recovery from storage permission error."""
        component = "storage_service"
        error = PermissionError("Permission denied: '/path/to/file'")
        
        # Mock file operations
        with patch('os.path.exists') as mock_exists, \
             patch('os.stat') as mock_stat, \
             patch('os.chmod') as mock_chmod:
            
            mock_exists.return_value = True
            mock_stat.return_value.st_mode = 0o644
            
            # Handle storage permission error
            result = self.error_handler.handle_error(component, error, ErrorSeverity.MEDIUM)
            
            # Check that storage degradation mode was enabled
            self.assertTrue(self.error_handler.storage_degraded)
    
    def test_file_not_found_recovery(self):
        """Test recovery from file not found errors."""
        component = "storage_service"
        error = FileNotFoundError("No such file or directory: '/path/to/missing/file.txt'")
        
        # Mock file operations
        with patch('pathlib.Path.mkdir') as mock_mkdir, \
             patch('pathlib.Path.touch') as mock_touch, \
             patch('pathlib.Path.exists') as mock_exists:
            
            mock_exists.side_effect = lambda: False  # File doesn't exist
            
            # Handle file not found error
            result = self.error_handler.handle_error(component, error, ErrorSeverity.MEDIUM)
            
            # Check that recovery was attempted
            self.assertTrue(self.error_handler.storage_degraded)
    
    def test_disk_space_error_recovery(self):
        """Test recovery from disk space errors."""
        component = "storage_service"
        error = IOError("No space left on device")
        
        # Mock disk usage and cleanup
        with patch('shutil.disk_usage') as mock_disk_usage, \
             patch.object(self.error_handler, '_cleanup_old_files') as mock_cleanup:
            
            # Simulate low disk space initially, then more space after cleanup
            mock_disk_usage.side_effect = [
                (100 * 1024**3, 99.5 * 1024**3, 0.5 * 1024**3),  # 0.5GB free initially
                (100 * 1024**3, 98 * 1024**3, 2 * 1024**3)       # 2GB free after cleanup
            ]
            mock_cleanup.return_value = 10  # 10 files cleaned
            
            # Handle disk space error
            result = self.error_handler.handle_error(component, error, ErrorSeverity.HIGH)
            
            # Check that cleanup was attempted
            mock_cleanup.assert_called()
    
    def test_io_error_with_device_busy(self):
        """Test recovery from device busy I/O errors."""
        component = "storage_service"
        error = IOError("Device or resource busy")
        
        # Handle device busy error
        start_time = time.time()
        result = self.error_handler.handle_error(component, error, ErrorSeverity.MEDIUM)
        end_time = time.time()
        
        # Check that it waited (recovery includes sleep)
        # Note: This is a simplified test - in practice we'd mock time.sleep
        self.assertTrue(self.error_handler.storage_degraded)
    
    def test_memory_exhaustion_recovery(self):
        """Test recovery from memory exhaustion."""
        component = "detection_engine"
        error = MemoryError("Out of memory")
        
        # Handle memory error
        result = self.error_handler.handle_error(component, error, ErrorSeverity.CRITICAL)
        
        # Check component status
        health = self.error_handler.component_health[component]
        self.assertEqual(health.status, ComponentStatus.FAILED)
    
    def test_alternative_storage_creation(self):
        """Test creation of alternative storage location."""
        # Test alternative storage creation
        with patch('tempfile.mkdtemp') as mock_mkdtemp, \
             patch('pathlib.Path.mkdir') as mock_mkdir, \
             patch('os.environ.__setitem__') as mock_setenv:
            
            mock_mkdtemp.return_value = '/tmp/cat_detection_backup_12345'
            
            result = self.error_handler._create_alternative_storage_location(
                ErrorRecord(datetime.now(), "storage", "PermissionError", "Test", ErrorSeverity.MEDIUM)
            )
            
            self.assertTrue(result)
            mock_mkdtemp.assert_called_once()
            mock_setenv.assert_called_once()
    
    def test_file_path_extraction(self):
        """Test extraction of file paths from error messages."""
        test_cases = [
            ("No such file or directory: '/path/to/file.txt'", "/path/to/file.txt"),
            ("Permission denied: '/home/user/data.db'", "/home/user/data.db"),
            ("[Errno 2] No such file or directory: '/tmp/test.log'", "/tmp/test.log"),
            ("Invalid file path", None),
            ("Error with 'relative/path.txt'", "relative/path.txt")
        ]
        
        for error_message, expected_path in test_cases:
            result = self.error_handler._extract_file_path_from_error(error_message)
            self.assertEqual(result, expected_path, f"Failed for: {error_message}")
    
    def test_disk_space_error_detection(self):
        """Test detection of disk space related errors."""
        disk_space_errors = [
            "No space left on device",
            "Disk full error occurred",
            "Not enough space available",
            "Insufficient space for operation",
            "Quota exceeded for user"
        ]
        
        non_disk_errors = [
            "Permission denied",
            "File not found",
            "Network timeout",
            "Invalid argument"
        ]
        
        for error_msg in disk_space_errors:
            self.assertTrue(self.error_handler._is_disk_space_error(error_msg))
        
        for error_msg in non_disk_errors:
            self.assertFalse(self.error_handler._is_disk_space_error(error_msg))
    
    def test_concurrent_error_handling(self):
        """Test concurrent error handling from multiple threads."""
        errors_handled = []
        
        def handle_errors(thread_id):
            for i in range(5):
                error = ValueError(f"Thread {thread_id} error {i}")
                result = self.error_handler.handle_error(f"component_{thread_id}", error, ErrorSeverity.LOW)
                errors_handled.append((thread_id, i, result))
        
        # Create multiple threads
        threads = []
        for thread_id in range(3):
            thread = threading.Thread(target=handle_errors, args=(thread_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check that all errors were handled
        self.assertEqual(len(errors_handled), 15)  # 3 threads * 5 errors each
        self.assertEqual(len(self.error_handler.error_history), 15)
    
    def test_cleanup_old_files(self):
        """Test cleanup of old files."""
        # Mock file system operations
        with patch('pathlib.Path.rglob') as mock_rglob, \
             patch('pathlib.Path.is_file') as mock_is_file, \
             patch('pathlib.Path.stat') as mock_stat, \
             patch('pathlib.Path.unlink') as mock_unlink:
            
            # Create mock files
            old_file = Mock()
            old_file.is_file.return_value = True
            old_file.stat.return_value.st_mtime = time.time() - (10 * 24 * 3600)  # 10 days old
            
            new_file = Mock()
            new_file.is_file.return_value = True
            new_file.stat.return_value.st_mtime = time.time() - (1 * 24 * 3600)   # 1 day old
            
            mock_rglob.return_value = [old_file, new_file]
            
            # Test cleanup
            deleted_count = self.error_handler._cleanup_old_files('/test/dir', days_old=7)
            
            # Should delete only the old file
            self.assertEqual(deleted_count, 1)
            old_file.unlink.assert_called_once()
            new_file.unlink.assert_not_called()


class TestEnhancedErrorRecovery(unittest.TestCase):
    """Test enhanced error recovery mechanisms."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.error_handler = ErrorHandler()
    
    def test_camera_module_reset_recovery(self):
        """Test camera module reset recovery strategy."""
        component = "frame_capture"
        
        # Mock subprocess calls for module reset and camera device check
        with patch('subprocess.run') as mock_subprocess, \
             patch('os.path.exists') as mock_exists:
            
            mock_subprocess.return_value.returncode = 0
            mock_exists.return_value = True  # Mock camera device exists
            
            # Test camera init error recovery
            error_record = ErrorRecord(
                datetime.now(), component, "CameraInitError", "Camera init failed", ErrorSeverity.HIGH
            )
            
            result = self.error_handler._recover_camera_init_error(error_record)
            
            # Should attempt module reset
            self.assertEqual(mock_subprocess.call_count, 2)  # modprobe -r and modprobe
    
    def test_network_interface_recovery(self):
        """Test network interface recovery strategy."""
        component = "notification_service"
        
        # Mock network interface operations
        with patch('subprocess.run') as mock_subprocess, \
             patch.object(self.error_handler, '_check_network_connectivity') as mock_connectivity:
            
            # Mock successful interface operations
            mock_subprocess.return_value.returncode = 0
            mock_connectivity.return_value = True
            
            error_record = ErrorRecord(
                datetime.now(), component, "ConnectionError", "Network failed", ErrorSeverity.MEDIUM
            )
            
            result = self.error_handler._attempt_network_recovery(error_record)
            
            # Should attempt interface recovery
            self.assertTrue(result)
    
    def test_storage_permission_fix(self):
        """Test storage permission fixing."""
        component = "storage_service"
        
        # Mock file permission operations
        with patch('os.path.exists') as mock_exists, \
             patch('os.stat') as mock_stat, \
             patch('os.chmod') as mock_chmod:
            
            mock_exists.return_value = True
            mock_stat.return_value.st_mode = 0o644
            
            error_record = ErrorRecord(
                datetime.now(), component, "PermissionError", 
                "Permission denied: '/test/file.txt'", ErrorSeverity.MEDIUM
            )
            
            result = self.error_handler._recover_permission_error(error_record)
            
            # Should attempt to fix permissions
            mock_chmod.assert_called_once()
    
    def test_graceful_degradation_with_recovery_callbacks(self):
        """Test graceful degradation with recovery callbacks."""
        callback_called = False
        callback_component = None
        
        def recovery_callback():
            nonlocal callback_called, callback_component
            callback_called = True
            callback_component = "test_component"
        
        # Register callback
        self.error_handler.register_recovery_callback("test_component", recovery_callback)
        
        # Trigger degradation
        self.error_handler.trigger_graceful_degradation("Test degradation")
        
        # Attempt recovery
        result = self.error_handler.recover_from_degradation()
        
        # Check callback was called
        self.assertTrue(result)
        self.assertTrue(callback_called)
        self.assertEqual(callback_component, "test_component")
    
    def test_error_pattern_analysis_and_response(self):
        """Test error pattern analysis and proactive response."""
        component = "test_component"
        
        # Generate pattern of similar errors
        for i in range(6):
            error = ValueError(f"Recurring error pattern {i}")
            self.error_handler.handle_error(component, error, ErrorSeverity.LOW)
        
        # Check that pattern was detected
        pattern_key = f"{component}:ValueError"
        self.assertIn(pattern_key, self.error_handler.error_patterns)
        self.assertEqual(self.error_handler.error_patterns[pattern_key], 6)
    
    def test_system_resource_monitoring_integration(self):
        """Test integration with system resource monitoring."""
        # This would typically integrate with the health checker
        # For now, test that error handler can trigger resource cleanup
        
        component = "detection_engine"
        error = RuntimeError("Memory allocation failed")
        
        # Mock garbage collection
        with patch('gc.collect') as mock_gc:
            result = self.error_handler.handle_error(component, error, ErrorSeverity.HIGH)
            
            # Should trigger garbage collection for memory-related errors
            # (This happens in the camera runtime error recovery)
            if "memory" in error.args[0].lower():
                mock_gc.assert_called()


class TestErrorHandlingIntegration(unittest.TestCase):
    """Test error handling integration with other system components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.error_handler = ErrorHandler()
    
    def test_logging_integration(self):
        """Test integration with structured logging."""
        component = "test_component"
        error = ValueError("Test error with context")
        context = {"user_id": "123", "operation": "test_op"}
        
        # Handle error with context
        with patch.object(self.error_handler.logger, 'error') as mock_log_error:
            result = self.error_handler.handle_error(component, error, ErrorSeverity.MEDIUM, context)
            
            # Check that error was logged
            mock_log_error.assert_called()
    
    def test_health_checker_integration(self):
        """Test integration with health checker."""
        # This test would verify that error handler properly updates
        # component health status that can be read by health checker
        
        component = "test_component"
        error = RuntimeError("Component failure")
        
        # Handle error
        self.error_handler.handle_error(component, error, ErrorSeverity.HIGH)
        
        # Check component health status
        health_info = self.error_handler.get_component_health(component)
        self.assertIn(component, health_info)
        self.assertEqual(health_info[component].status, ComponentStatus.DEGRADED)
    
    def test_configuration_based_recovery(self):
        """Test recovery strategies based on configuration."""
        # Test that recovery strategies can be configured
        # This would typically read from configuration files
        
        component = "configurable_component"
        
        # Register custom recovery strategy
        def custom_recovery(error_record):
            return True
        
        self.error_handler.register_recovery_strategy("CustomError", custom_recovery)
        
        # Verify strategy is registered
        self.assertIn("CustomError", self.error_handler.recovery_strategies)
        self.assertEqual(self.error_handler.recovery_strategies["CustomError"], custom_recovery)


if __name__ == '__main__':
    unittest.main()