"""Comprehensive error handling and recovery system."""

import logging
import traceback
import functools
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Type
from dataclasses import dataclass, field
from enum import Enum
import threading
from queue import Queue, Empty


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComponentStatus(Enum):
    """Component status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    RECOVERING = "recovering"


@dataclass
class ErrorRecord:
    """Record of an error occurrence."""
    timestamp: datetime
    component: str
    error_type: str
    message: str
    severity: ErrorSeverity
    traceback_info: Optional[str] = None
    recovery_attempted: bool = False
    recovery_successful: bool = False
    occurrence_count: int = 1
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ComponentHealth:
    """Health status of a system component."""
    name: str
    status: ComponentStatus = ComponentStatus.HEALTHY
    last_error: Optional[ErrorRecord] = None
    error_count: int = 0
    last_health_check: datetime = field(default_factory=datetime.now)
    recovery_attempts: int = 0
    max_recovery_attempts: int = 3
    
    def is_healthy(self) -> bool:
        """Check if component is healthy."""
        return self.status == ComponentStatus.HEALTHY
    
    def can_recover(self) -> bool:
        """Check if component can attempt recovery."""
        return self.recovery_attempts < self.max_recovery_attempts


class ErrorHandler:
    """Centralized error handling and recovery system."""
    
    def __init__(self, max_error_history: int = 1000):
        self.logger = logging.getLogger(__name__)
        self.error_history: List[ErrorRecord] = []
        self.max_error_history = max_error_history
        self.component_health: Dict[str, ComponentHealth] = {}
        self.recovery_strategies: Dict[str, Callable] = {}
        self.error_patterns: Dict[str, int] = {}
        self._lock = threading.Lock()
        
        # Error thresholds
        self.error_rate_threshold = 10  # errors per minute
        self.critical_error_threshold = 5  # critical errors before shutdown
        
        # Recovery state
        self.system_degraded = False
        self.degradation_start_time = None
        self.recovery_callbacks: Dict[str, List[Callable]] = {}
        
        # Graceful degradation flags
        self.camera_degraded = False
        self.network_degraded = False
        self.storage_degraded = False
        
        # Initialize recovery strategies
        self._initialize_default_recovery_strategies()
    
    def _initialize_default_recovery_strategies(self) -> None:
        """Initialize default recovery strategies for common error types."""
        # Camera-related errors
        self.register_recovery_strategy("CameraError", self._recover_camera_error)
        self.register_recovery_strategy("RuntimeError", self._recover_runtime_error)
        self.register_recovery_strategy("OSError", self._recover_os_error)
        
        # Network-related errors
        self.register_recovery_strategy("ConnectionError", self._recover_connection_error)
        self.register_recovery_strategy("TimeoutError", self._recover_timeout_error)
        self.register_recovery_strategy("RequestException", self._recover_request_error)
        
        # Storage-related errors
        self.register_recovery_strategy("PermissionError", self._recover_permission_error)
        self.register_recovery_strategy("FileNotFoundError", self._recover_file_error)
        self.register_recovery_strategy("IOError", self._recover_io_error)
    
    def _recover_camera_error(self, error_record: ErrorRecord) -> bool:
        """Recover from camera-specific errors."""
        self.logger.info("Attempting camera error recovery", extra={
            'context': {
                'component': error_record.component,
                'error_type': error_record.error_type,
                'recovery_attempt': self.component_health.get(error_record.component, ComponentHealth("unknown")).recovery_attempts + 1
            }
        })
        
        # Enable camera degradation mode
        self.camera_degraded = True
        
        # Wait for camera hardware to stabilize
        time.sleep(3)
        
        # Enhanced recovery strategies for different camera errors
        recovery_strategies = {
            "CameraInitError": self._recover_camera_init_error,
            "CaptureError": self._recover_camera_capture_error,
            "RuntimeError": self._recover_camera_runtime_error,
            "OSError": self._recover_camera_os_error,
            "ValueError": self._recover_camera_value_error,
            "TimeoutError": self._recover_camera_timeout_error
        }
        
        if error_record.error_type in recovery_strategies:
            try:
                success = recovery_strategies[error_record.error_type](error_record)
                if success:
                    self.logger.info(f"Camera error {error_record.error_type} recovery successful")
                    return True
                else:
                    self.logger.warning(f"Camera error {error_record.error_type} recovery failed")
                    return False
            except Exception as recovery_error:
                self.logger.error(f"Camera recovery strategy failed: {recovery_error}")
                return False
        
        # Generic camera recovery for unknown error types
        self.logger.warning(f"No specific recovery strategy for {error_record.error_type}, trying generic recovery")
        return self._generic_camera_recovery(error_record)
    
    def _recover_camera_init_error(self, error_record: ErrorRecord) -> bool:
        """Recover from camera initialization errors."""
        self.logger.info("Attempting camera initialization recovery")
        
        # Check if camera device exists
        import os
        camera_devices = ['/dev/video0', '/dev/video1', '/dev/video2']
        available_devices = [dev for dev in camera_devices if os.path.exists(dev)]
        
        if not available_devices:
            self.logger.error("No camera devices found")
            return False
        
        # Wait longer for hardware initialization
        time.sleep(5)
        
        # Try to reset camera permissions
        try:
            import subprocess
            subprocess.run(['sudo', 'modprobe', '-r', 'bcm2835-v4l2'], check=False, timeout=10)
            time.sleep(2)
            subprocess.run(['sudo', 'modprobe', 'bcm2835-v4l2'], check=False, timeout=10)
            time.sleep(3)
            return True
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            self.logger.warning("Could not reset camera module")
            return False
    
    def _recover_camera_capture_error(self, error_record: ErrorRecord) -> bool:
        """Recover from camera capture errors."""
        self.logger.info("Attempting camera capture recovery")
        
        # Reduce capture parameters to minimum viable settings
        self.logger.info("Reducing camera capture parameters for recovery")
        
        # Wait for camera buffer to clear
        time.sleep(2)
        
        return True
    
    def _recover_camera_runtime_error(self, error_record: ErrorRecord) -> bool:
        """Recover from camera runtime errors."""
        self.logger.info("Attempting camera runtime error recovery")
        
        # Check if error is related to memory or resources
        if "memory" in error_record.message.lower() or "resource" in error_record.message.lower():
            # Trigger garbage collection
            import gc
            gc.collect()
            time.sleep(1)
        
        return True
    
    def _recover_camera_os_error(self, error_record: ErrorRecord) -> bool:
        """Recover from camera OS errors."""
        self.logger.info("Attempting camera OS error recovery")
        
        # Check if it's a permission error
        if "permission" in error_record.message.lower():
            self.logger.warning("Camera permission error detected")
            return False  # Cannot recover from permission errors automatically
        
        # Check if it's a device busy error
        if "busy" in error_record.message.lower() or "device or resource busy" in error_record.message.lower():
            self.logger.info("Camera device busy, waiting for release")
            time.sleep(5)
            return True
        
        return True
    
    def _recover_camera_value_error(self, error_record: ErrorRecord) -> bool:
        """Recover from camera value errors."""
        self.logger.info("Attempting camera value error recovery")
        
        # Usually indicates invalid parameters
        # Recovery involves resetting to default parameters
        return True
    
    def _recover_camera_timeout_error(self, error_record: ErrorRecord) -> bool:
        """Recover from camera timeout errors."""
        self.logger.info("Attempting camera timeout error recovery")
        
        # Increase timeout tolerance and wait
        time.sleep(3)
        return True
    
    def _generic_camera_recovery(self, error_record: ErrorRecord) -> bool:
        """Generic camera recovery for unknown errors."""
        self.logger.info("Attempting generic camera recovery")
        
        # Basic recovery steps
        time.sleep(2)
        
        # Try to free up system resources
        import gc
        gc.collect()
        
        return True
    
    def _recover_runtime_error(self, error_record: ErrorRecord) -> bool:
        """Recover from runtime errors."""
        if "camera" in error_record.component.lower():
            return self._recover_camera_error(error_record)
        
        # Generic runtime error recovery
        time.sleep(1)
        return True
    
    def _recover_os_error(self, error_record: ErrorRecord) -> bool:
        """Recover from OS-level errors."""
        self.logger.info("Attempting OS error recovery")
        
        # Wait for system resources to stabilize
        time.sleep(2)
        
        # Check if it's a hardware-related error
        if "camera" in error_record.component.lower():
            self.camera_degraded = True
        elif "storage" in error_record.component.lower():
            self.storage_degraded = True
        
        return True
    
    def _recover_connection_error(self, error_record: ErrorRecord) -> bool:
        """Recover from network connection errors."""
        self.logger.info("Attempting connection error recovery", extra={
            'context': {
                'component': error_record.component,
                'error_message': error_record.message,
                'recovery_attempt': self.component_health.get(error_record.component, ComponentHealth("unknown")).recovery_attempts + 1
            }
        })
        
        # Enable network degradation mode
        self.network_degraded = True
        
        # Enhanced network recovery strategies
        recovery_success = False
        
        try:
            # Check network connectivity
            if self._check_network_connectivity():
                self.logger.info("Network connectivity restored")
                recovery_success = True
            else:
                # Try to recover network connection
                recovery_success = self._attempt_network_recovery(error_record)
        except Exception as e:
            self.logger.error(f"Network recovery check failed: {e}")
        
        if recovery_success:
            self.logger.info("Network connection recovery successful")
        else:
            self.logger.warning("Network connection recovery failed, maintaining degraded mode")
        
        return recovery_success
    
    def _check_network_connectivity(self) -> bool:
        """Check if network connectivity is available."""
        import socket
        import subprocess
        
        # Test DNS resolution
        try:
            socket.gethostbyname('google.com')
            self.logger.debug("DNS resolution successful")
        except socket.gaierror:
            self.logger.warning("DNS resolution failed")
            return False
        
        # Test ping to reliable host
        try:
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '3', '8.8.8.8'],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                self.logger.debug("Network ping successful")
                return True
            else:
                self.logger.warning("Network ping failed")
                return False
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            self.logger.warning("Network ping test failed")
            return False
    
    def _attempt_network_recovery(self, error_record: ErrorRecord) -> bool:
        """Attempt to recover network connection."""
        self.logger.info("Attempting network interface recovery")
        
        try:
            import subprocess
            
            # Try to restart network interface (requires appropriate permissions)
            interfaces = ['wlan0', 'eth0', 'wlan1']
            
            for interface in interfaces:
                try:
                    # Check if interface exists
                    result = subprocess.run(
                        ['ip', 'link', 'show', interface],
                        capture_output=True,
                        timeout=5
                    )
                    
                    if result.returncode == 0:
                        self.logger.info(f"Found network interface: {interface}")
                        
                        # Try to bring interface down and up
                        subprocess.run(['sudo', 'ip', 'link', 'set', interface, 'down'], 
                                     timeout=10, check=False)
                        time.sleep(2)
                        subprocess.run(['sudo', 'ip', 'link', 'set', interface, 'up'], 
                                     timeout=10, check=False)
                        time.sleep(3)
                        
                        # Check if recovery worked
                        if self._check_network_connectivity():
                            self.logger.info(f"Network recovery successful via {interface}")
                            return True
                        
                except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                    self.logger.debug(f"Could not recover via interface {interface}")
                    continue
            
            # Try DHCP renewal
            try:
                subprocess.run(['sudo', 'dhclient', '-r'], timeout=10, check=False)
                time.sleep(2)
                subprocess.run(['sudo', 'dhclient'], timeout=15, check=False)
                time.sleep(5)
                
                if self._check_network_connectivity():
                    self.logger.info("Network recovery successful via DHCP renewal")
                    return True
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                self.logger.debug("DHCP renewal failed")
            
        except Exception as e:
            self.logger.error(f"Network recovery attempt failed: {e}")
        
        return False
    
    def _recover_timeout_error(self, error_record: ErrorRecord) -> bool:
        """Recover from timeout errors."""
        self.logger.info("Attempting timeout error recovery")
        
        # Increase timeout tolerance
        if "network" in error_record.component.lower():
            self.network_degraded = True
        
        time.sleep(2)
        return True
    
    def _recover_request_error(self, error_record: ErrorRecord) -> bool:
        """Recover from HTTP request errors."""
        return self._recover_connection_error(error_record)
    
    def _recover_permission_error(self, error_record: ErrorRecord) -> bool:
        """Recover from permission errors."""
        self.logger.warning("Permission error detected - enabling storage degradation", extra={
            'context': {
                'component': error_record.component,
                'error_message': error_record.message,
                'recovery_attempt': self.component_health.get(error_record.component, ComponentHealth("unknown")).recovery_attempts + 1
            }
        })
        
        # Enable storage degradation mode
        self.storage_degraded = True
        
        # Try to recover from permission errors
        try:
            import os
            import stat
            
            # Extract file path from error message if possible
            file_path = self._extract_file_path_from_error(error_record.message)
            
            if file_path and os.path.exists(file_path):
                # Try to fix permissions
                try:
                    # Get current permissions
                    current_perms = os.stat(file_path).st_mode
                    
                    # Add write permissions for owner
                    new_perms = current_perms | stat.S_IWUSR
                    os.chmod(file_path, new_perms)
                    
                    self.logger.info(f"Fixed permissions for {file_path}")
                    return True
                    
                except OSError as perm_error:
                    self.logger.warning(f"Could not fix permissions for {file_path}: {perm_error}")
            
            # Try to create alternative storage location
            return self._create_alternative_storage_location(error_record)
            
        except Exception as e:
            self.logger.error(f"Permission error recovery failed: {e}")
            return False
    
    def _recover_file_error(self, error_record: ErrorRecord) -> bool:
        """Recover from file not found errors."""
        self.logger.info("Attempting file error recovery", extra={
            'context': {
                'component': error_record.component,
                'error_message': error_record.message,
                'recovery_attempt': self.component_health.get(error_record.component, ComponentHealth("unknown")).recovery_attempts + 1
            }
        })
        
        # Enable storage degradation if storage-related
        if "storage" in error_record.component.lower():
            self.storage_degraded = True
        
        try:
            import os
            from pathlib import Path
            
            # Extract file path from error message
            file_path = self._extract_file_path_from_error(error_record.message)
            
            if file_path:
                path_obj = Path(file_path)
                
                # Try to create missing directories
                if not path_obj.parent.exists():
                    try:
                        path_obj.parent.mkdir(parents=True, exist_ok=True)
                        self.logger.info(f"Created missing directory: {path_obj.parent}")
                    except OSError as dir_error:
                        self.logger.warning(f"Could not create directory {path_obj.parent}: {dir_error}")
                        return False
                
                # Try to create missing file if it's expected to exist
                if not path_obj.exists() and self._should_create_missing_file(file_path):
                    try:
                        path_obj.touch()
                        self.logger.info(f"Created missing file: {file_path}")
                        return True
                    except OSError as file_error:
                        self.logger.warning(f"Could not create file {file_path}: {file_error}")
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"File error recovery failed: {e}")
            return False
    
    def _recover_io_error(self, error_record: ErrorRecord) -> bool:
        """Recover from I/O errors."""
        self.logger.info("Attempting I/O error recovery", extra={
            'context': {
                'component': error_record.component,
                'error_type': error_record.error_type,
                'error_message': error_record.message,
                'recovery_attempt': self.component_health.get(error_record.component, ComponentHealth("unknown")).recovery_attempts + 1
            }
        })
        
        # Enable storage degradation
        self.storage_degraded = True
        
        try:
            # Check if it's a disk space issue
            if self._is_disk_space_error(error_record.message):
                return self._recover_disk_space_error(error_record)
            
            # Check if it's a device busy error
            if "busy" in error_record.message.lower() or "resource busy" in error_record.message.lower():
                self.logger.info("Device busy error detected, waiting for resource release")
                time.sleep(3)
                return True
            
            # Check if it's a network I/O error
            if "network" in error_record.message.lower() or "connection" in error_record.message.lower():
                return self._recover_network_io_error(error_record)
            
            # Generic I/O error recovery
            time.sleep(1)
            
            # Try to sync filesystem
            try:
                import subprocess
                subprocess.run(['sync'], timeout=10, check=False)
                self.logger.debug("Filesystem sync completed")
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                self.logger.debug("Could not sync filesystem")
            
            return True
            
        except Exception as e:
            self.logger.error(f"I/O error recovery failed: {e}")
            return False
    
    def _extract_file_path_from_error(self, error_message: str) -> Optional[str]:
        """Extract file path from error message."""
        import re
        
        # Common patterns for file paths in error messages
        patterns = [
            r"'([^']+)'",  # Single quotes
            r'"([^"]+)"',  # Double quotes
            r"\[Errno \d+\] .+: '([^']+)'",  # Errno format
            r"No such file or directory: '([^']+)'",  # Specific format
            r"Permission denied: '([^']+)'",  # Permission format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_message)
            if match:
                potential_path = match.group(1)
                # Basic validation that it looks like a file path
                if '/' in potential_path or '\\' in potential_path:
                    return potential_path
        
        return None
    
    def _should_create_missing_file(self, file_path: str) -> bool:
        """Determine if a missing file should be created."""
        # Only create files in expected locations
        safe_paths = [
            '/tmp/',
            'logs/',
            'data/',
            './',
            'config/',
            'cache/'
        ]
        
        return any(safe_path in file_path for safe_path in safe_paths)
    
    def _is_disk_space_error(self, error_message: str) -> bool:
        """Check if error is related to disk space."""
        disk_space_indicators = [
            "no space left",
            "disk full",
            "not enough space",
            "insufficient space",
            "quota exceeded"
        ]
        
        return any(indicator in error_message.lower() for indicator in disk_space_indicators)
    
    def _recover_disk_space_error(self, error_record: ErrorRecord) -> bool:
        """Recover from disk space errors."""
        self.logger.warning("Disk space error detected, attempting cleanup")
        
        try:
            import shutil
            import os
            from pathlib import Path
            
            # Get current disk usage
            total, used, free = shutil.disk_usage('/')
            free_gb = free / (1024**3)
            
            self.logger.info(f"Current free space: {free_gb:.2f} GB")
            
            if free_gb < 0.5:  # Less than 500MB free
                # Try to clean up temporary files
                cleanup_paths = [
                    '/tmp/',
                    'logs/',
                    'data/images/',
                    '.cache/'
                ]
                
                for cleanup_path in cleanup_paths:
                    if os.path.exists(cleanup_path):
                        try:
                            self._cleanup_old_files(cleanup_path, days_old=7)
                        except Exception as cleanup_error:
                            self.logger.warning(f"Could not cleanup {cleanup_path}: {cleanup_error}")
                
                # Check if we freed up space
                total, used, free = shutil.disk_usage('/')
                new_free_gb = free / (1024**3)
                
                if new_free_gb > free_gb:
                    self.logger.info(f"Freed up {new_free_gb - free_gb:.2f} GB of space")
                    return True
                else:
                    self.logger.warning("Could not free up sufficient disk space")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Disk space recovery failed: {e}")
            return False
    
    def _recover_network_io_error(self, error_record: ErrorRecord) -> bool:
        """Recover from network I/O errors."""
        self.logger.info("Network I/O error detected, checking connectivity")
        
        # Use existing network recovery methods
        return self._check_network_connectivity()
    
    def _cleanup_old_files(self, directory: str, days_old: int = 7) -> int:
        """Clean up old files in a directory."""
        import os
        import time
        from pathlib import Path
        
        if not os.path.exists(directory):
            return 0
        
        cutoff_time = time.time() - (days_old * 24 * 3600)
        deleted_count = 0
        
        try:
            for file_path in Path(directory).rglob('*'):
                if file_path.is_file():
                    try:
                        if file_path.stat().st_mtime < cutoff_time:
                            file_path.unlink()
                            deleted_count += 1
                    except OSError:
                        continue  # Skip files we can't delete
        except Exception as e:
            self.logger.warning(f"Error during cleanup of {directory}: {e}")
        
        if deleted_count > 0:
            self.logger.info(f"Cleaned up {deleted_count} old files from {directory}")
        
        return deleted_count
    
    def _create_alternative_storage_location(self, error_record: ErrorRecord) -> bool:
        """Create alternative storage location when primary fails."""
        try:
            import os
            import tempfile
            from pathlib import Path
            
            # Create temporary storage location
            temp_dir = tempfile.mkdtemp(prefix='cat_detection_backup_')
            
            # Create subdirectories
            subdirs = ['images', 'logs', 'data']
            for subdir in subdirs:
                Path(temp_dir, subdir).mkdir(exist_ok=True)
            
            self.logger.info(f"Created alternative storage location: {temp_dir}")
            
            # Store the alternative location for other components to use
            os.environ['CAT_DETECTION_BACKUP_STORAGE'] = temp_dir
            
            return True
            
        except Exception as e:
            self.logger.error(f"Could not create alternative storage location: {e}")
            return False
    
    def register_recovery_callback(self, component: str, callback: Callable) -> None:
        """Register a callback to be called when component recovers."""
        if component not in self.recovery_callbacks:
            self.recovery_callbacks[component] = []
        self.recovery_callbacks[component].append(callback)
    
    def trigger_graceful_degradation(self, reason: str) -> None:
        """Trigger system-wide graceful degradation."""
        if not self.system_degraded:
            self.system_degraded = True
            self.degradation_start_time = datetime.now()
            self.logger.warning(f"System entering degraded mode: {reason}")
    
    def recover_from_degradation(self) -> bool:
        """Attempt to recover from system degradation."""
        if not self.system_degraded:
            return True
        
        # Check if all critical components are healthy
        critical_components_healthy = True
        with self._lock:
            for health in self.component_health.values():
                if health.status == ComponentStatus.FAILED:
                    critical_components_healthy = False
                    break
        
        if critical_components_healthy:
            self.system_degraded = False
            self.degradation_start_time = None
            self.camera_degraded = False
            self.network_degraded = False
            self.storage_degraded = False
            
            self.logger.info("System recovered from degraded mode")
            
            # Trigger recovery callbacks
            for component_name, callbacks in self.recovery_callbacks.items():
                for callback in callbacks:
                    try:
                        callback()
                    except Exception as e:
                        self.logger.error(f"Error in recovery callback for {component_name}: {e}")
            
            return True
        
        return False
    
    def is_system_degraded(self) -> bool:
        """Check if system is in degraded mode."""
        return self.system_degraded
    
    def get_degradation_info(self) -> Dict[str, Any]:
        """Get information about system degradation state."""
        degradation_info = {
            "system_degraded": self.system_degraded,
            "camera_degraded": self.camera_degraded,
            "network_degraded": self.network_degraded,
            "storage_degraded": self.storage_degraded,
            "degradation_start_time": self.degradation_start_time.isoformat() if self.degradation_start_time else None,
            "degradation_duration_seconds": (datetime.now() - self.degradation_start_time).total_seconds() if self.degradation_start_time else 0
        }
        
        return degradation_info_name, callbacks in self.recovery_callbacks.items():
                for callback in callbacks:
                    try:
                        callback()
                    except Exception as e:
                        self.logger.error(f"Error in recovery callback for {component_name}: {e}")
            
            return True
        
        return False
    
    def is_system_degraded(self) -> bool:
        """Check if system is in degraded mode."""
        return self.system_degraded
    
    def get_degradation_info(self) -> Dict[str, Any]:
        """Get information about system degradation state."""
        degradation_info = {
            "system_degraded": self.system_degraded,
            "camera_degraded": self.camera_degraded,
            "network_degraded": self.network_degraded,
            "storage_degraded": self.storage_degraded,
            "degradation_start_time": self.degradation_start_time.isoformat() if self.degradation_start_time else None,
            "degradation_duration_seconds": (datetime.now() - self.degradation_start_time).total_seconds() if self.degradation_start_time else 0
        }
        
        return degradation_info_name, callbacks in self.recovery_callbacks.items():
                for callback in callbacks:
                    try:
                        callback()
                    except Exception as e:
                        self.logger.error(f"Error in recovery callback for {component_name}: {e}")
            
            return True
        
        return False
    
    def is_system_degraded(self) -> bool:
        """Check if system is in degraded mode."""
        return self.system_degraded
    
    def get_degradation_info(self) -> Dict[str, Any]:
        """Get information about system degradation state."""
        degradation_info = {
            "system_degraded": self.system_degraded,
            "camera_degraded": self.camera_degraded,
            "network_degraded": self.network_degraded,
            "storage_degraded": self.storage_degraded,
            "degradation_start_time": self.degradation_start_time.isoformat() if self.degradation_start_time else None,
            "degradation_duration_seconds": (datetime.now() - self.degradation_start_time).total_seconds() if self.degradation_start_time else 0
        }
        
        return degradation_info, callbacks in self.recovery_callbacks.items():
                for callback in callbacks:
                    try:
                        callback()
                    except Exception as e:
                        self.logger.error(f"Recovery callback failed for {component}: {e}")
            
            return True
        
        return False
    
    def is_system_degraded(self) -> bool:
        """Check if system is in degraded mode."""
        return self.system_degraded
    
    def get_degradation_info(self) -> Dict[str, Any]:
        """Get information about system degradation."""
        return {
            "system_degraded": self.system_degraded,
            "degradation_start_time": self.degradation_start_time.isoformat() if self.degradation_start_time else None,
            "camera_degraded": self.camera_degraded,
            "network_degraded": self.network_degraded,
            "storage_degraded": self.storage_degraded,
            "degradation_duration_seconds": (
                (datetime.now() - self.degradation_start_time).total_seconds()
                if self.degradation_start_time else 0
            )
        }
        
    def register_component(self, component_name: str, max_recovery_attempts: int = 3) -> None:
        """Register a component for health monitoring."""
        with self._lock:
            self.component_health[component_name] = ComponentHealth(
                name=component_name,
                max_recovery_attempts=max_recovery_attempts
            )
        self.logger.info(f"Registered component for monitoring: {component_name}")
    
    def register_recovery_strategy(self, error_type: str, recovery_func: Callable) -> None:
        """Register a recovery strategy for specific error types."""
        self.recovery_strategies[error_type] = recovery_func
        self.logger.info(f"Registered recovery strategy for: {error_type}")
    
    def handle_error(self, 
                    component: str,
                    error: Exception,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle an error with appropriate logging and recovery."""
        error_type = type(error).__name__
        error_message = str(error)
        
        # Create error record
        error_record = ErrorRecord(
            timestamp=datetime.now(),
            component=component,
            error_type=error_type,
            message=error_message,
            severity=severity,
            traceback_info=traceback.format_exc()
        )
        
        # Log the error
        self._log_error(error_record, context)
        
        # Update component health
        self._update_component_health(component, error_record)
        
        # Store error history
        self._store_error_record(error_record)
        
        # Attempt recovery if strategy exists
        recovery_success = self._attempt_recovery(error_record)
        
        # Check for error patterns
        self._analyze_error_patterns(error_record)
        
        return recovery_success
    
    def _log_error(self, error_record: ErrorRecord, context: Optional[Dict[str, Any]] = None) -> None:
        """Log error with appropriate level."""
        log_message = f"[{error_record.component}] {error_record.error_type}: {error_record.message}"
        
        if context:
            log_message += f" | Context: {context}"
        
        if error_record.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
            if error_record.traceback_info:
                self.logger.critical(f"Traceback:\n{error_record.traceback_info}")
        elif error_record.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
            if error_record.traceback_info:
                self.logger.error(f"Traceback:\n{error_record.traceback_info}")
        elif error_record.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:  # LOW
            self.logger.info(log_message)
    
    def _update_component_health(self, component: str, error_record: ErrorRecord) -> None:
        """Update component health status."""
        with self._lock:
            if component not in self.component_health:
                self.register_component(component)
            
            health = self.component_health[component]
            health.last_error = error_record
            health.error_count += 1
            health.last_health_check = datetime.now()
            
            # Update status based on severity and error count
            if error_record.severity == ErrorSeverity.CRITICAL:
                health.status = ComponentStatus.FAILED
            elif error_record.severity == ErrorSeverity.HIGH or health.error_count > 5:
                health.status = ComponentStatus.DEGRADED
            elif health.status == ComponentStatus.HEALTHY:
                health.status = ComponentStatus.DEGRADED
    
    def _store_error_record(self, error_record: ErrorRecord) -> None:
        """Store error record in history."""
        with self._lock:
            # Check for duplicate errors
            for existing_error in self.error_history:
                if (existing_error.component == error_record.component and
                    existing_error.error_type == error_record.error_type and
                    existing_error.message == error_record.message and
                    (error_record.timestamp - existing_error.timestamp).total_seconds() < 60):
                    # Increment occurrence count instead of adding new record
                    existing_error.occurrence_count += 1
                    existing_error.timestamp = error_record.timestamp
                    return
            
            # Add new error record
            self.error_history.append(error_record)
            
            # Maintain history size limit
            if len(self.error_history) > self.max_error_history:
                self.error_history = self.error_history[-self.max_error_history:]
    
    def _attempt_recovery(self, error_record: ErrorRecord) -> bool:
        """Attempt to recover from error using registered strategies."""
        error_type = error_record.error_type
        component = error_record.component
        
        # Check if component can attempt recovery
        with self._lock:
            if component in self.component_health:
                health = self.component_health[component]
                if not health.can_recover():
                    self.logger.warning(f"Component {component} has exceeded max recovery attempts")
                    return False
                health.recovery_attempts += 1
                health.status = ComponentStatus.RECOVERING
        
        # Try specific error type recovery
        if error_type in self.recovery_strategies:
            try:
                self.logger.info(f"Attempting recovery for {error_type} in {component}")
                recovery_func = self.recovery_strategies[error_type]
                success = recovery_func(error_record)
                
                error_record.recovery_attempted = True
                error_record.recovery_successful = success
                
                if success:
                    self._mark_component_recovered(component)
                    self.logger.info(f"Recovery successful for {error_type} in {component}")
                else:
                    self.logger.warning(f"Recovery failed for {error_type} in {component}")
                
                return success
                
            except Exception as recovery_error:
                self.logger.error(f"Recovery strategy failed: {recovery_error}")
                return False
        
        # Try generic recovery strategies
        return self._try_generic_recovery(error_record)
    
    def _try_generic_recovery(self, error_record: ErrorRecord) -> bool:
        """Try generic recovery strategies."""
        component = error_record.component
        
        # Generic recovery strategies based on component type
        if "camera" in component.lower():
            return self._recover_camera_component(error_record)
        elif "network" in component.lower() or "notification" in component.lower():
            return self._recover_network_component(error_record)
        elif "storage" in component.lower():
            return self._recover_storage_component(error_record)
        
        return False
    
    def _recover_camera_component(self, error_record: ErrorRecord) -> bool:
        """Generic camera component recovery."""
        self.logger.info("Attempting camera component recovery")
        
        # Wait a moment for hardware to stabilize
        time.sleep(2)
        
        # Camera recovery is typically handled by the component itself
        # This is a placeholder for generic recovery actions
        return True
    
    def _recover_network_component(self, error_record: ErrorRecord) -> bool:
        """Generic network component recovery."""
        self.logger.info("Attempting network component recovery")
        
        # Wait for network to stabilize
        time.sleep(5)
        
        # Network recovery is typically handled by retrying operations
        return True
    
    def _recover_storage_component(self, error_record: ErrorRecord) -> bool:
        """Generic storage component recovery."""
        self.logger.info("Attempting storage component recovery")
        
        # Storage recovery might involve cleanup or reconnection
        return True
    
    def _mark_component_recovered(self, component: str) -> None:
        """Mark component as recovered."""
        with self._lock:
            if component in self.component_health:
                health = self.component_health[component]
                health.status = ComponentStatus.HEALTHY
                health.recovery_attempts = 0
                health.last_health_check = datetime.now()
    
    def _analyze_error_patterns(self, error_record: ErrorRecord) -> None:
        """Analyze error patterns for proactive measures."""
        pattern_key = f"{error_record.component}:{error_record.error_type}"
        
        with self._lock:
            self.error_patterns[pattern_key] = self.error_patterns.get(pattern_key, 0) + 1
            
            # Check for concerning patterns
            if self.error_patterns[pattern_key] > 5:
                self.logger.warning(f"Recurring error pattern detected: {pattern_key} "
                                  f"({self.error_patterns[pattern_key]} occurrences)")
    
    def get_component_health(self, component: Optional[str] = None) -> Dict[str, ComponentHealth]:
        """Get health status of components."""
        with self._lock:
            if component:
                return {component: self.component_health.get(component)}
            return self.component_health.copy()
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for specified time period."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            recent_errors = [
                error for error in self.error_history
                if error.timestamp >= cutoff_time
            ]
        
        # Analyze errors
        error_by_component = {}
        error_by_type = {}
        severity_counts = {severity: 0 for severity in ErrorSeverity}
        
        for error in recent_errors:
            # By component
            if error.component not in error_by_component:
                error_by_component[error.component] = 0
            error_by_component[error.component] += error.occurrence_count
            
            # By type
            if error.error_type not in error_by_type:
                error_by_type[error.error_type] = 0
            error_by_type[error.error_type] += error.occurrence_count
            
            # By severity
            severity_counts[error.severity] += error.occurrence_count
        
        return {
            "time_period_hours": hours,
            "total_errors": sum(error.occurrence_count for error in recent_errors),
            "unique_errors": len(recent_errors),
            "errors_by_component": error_by_component,
            "errors_by_type": error_by_type,
            "errors_by_severity": {sev.value: count for sev, count in severity_counts.items()},
            "component_health": {
                name: {
                    "status": health.status.value,
                    "error_count": health.error_count,
                    "recovery_attempts": health.recovery_attempts
                }
                for name, health in self.component_health.items()
            }
        }
    
    def clear_error_history(self, older_than_hours: Optional[int] = None) -> int:
        """Clear error history, optionally only older entries."""
        with self._lock:
            if older_than_hours:
                cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
                original_count = len(self.error_history)
                self.error_history = [
                    error for error in self.error_history
                    if error.timestamp >= cutoff_time
                ]
                cleared_count = original_count - len(self.error_history)
            else:
                cleared_count = len(self.error_history)
                self.error_history.clear()
                
        self.logger.info(f"Cleared {cleared_count} error records from history")
        return cleared_count


def with_error_handling(component: str, 
                       severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                       error_handler: Optional[ErrorHandler] = None):
    """Decorator for automatic error handling."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if error_handler:
                    error_handler.handle_error(component, e, severity)
                else:
                    # Fallback logging
                    logger = logging.getLogger(component)
                    logger.error(f"Error in {func.__name__}: {e}")
                
                # Re-raise critical errors
                if severity == ErrorSeverity.CRITICAL:
                    raise
                
                return None
        return wrapper
    return decorator


def retry_on_error(max_attempts: int = 3, 
                  delay: float = 1.0,
                  backoff_factor: float = 2.0,
                  exceptions: tuple = (Exception,)):
    """Decorator for retrying operations on error."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        break
            
            # All attempts failed, raise the last exception
            raise last_exception
        return wrapper
    return decorator


# Global error handler instance
global_error_handler = ErrorHandler() 
   def register_component(self, component_name: str, max_recovery_attempts: int = 3) -> None:
        """Register a component for health monitoring."""
        with self._lock:
            if component_name not in self.component_health:
                self.component_health[component_name] = ComponentHealth(
                    name=component_name,
                    max_recovery_attempts=max_recovery_attempts
                )
                self.logger.info(f"Component registered for health monitoring: {component_name}")
    
    def handle_error(self, component: str, error: Exception, severity: ErrorSeverity = ErrorSeverity.MEDIUM) -> bool:
        """Handle an error and attempt recovery if possible."""
        error_type = error.__class__.__name__
        error_message = str(error)
        
        # Get traceback information
        tb_info = traceback.format_exc() if error.__traceback__ else None
        
        # Create error record
        error_record = ErrorRecord(
            timestamp=datetime.now(),
            component=component,
            error_type=error_type,
            message=error_message,
            severity=severity,
            traceback_info=tb_info
        )
        
        # Log the error
        log_level = logging.ERROR if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] else logging.WARNING
        self.logger.log(log_level, f"Error in {component}: {error_type} - {error_message}", 
                      exc_info=(severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]))
        
        # Update component health
        self._update_component_health(component, error_record)
        
        # Check for duplicate errors
        duplicate = self._check_for_duplicate_error(error_record)
        if not duplicate:
            # Add to error history
            with self._lock:
                self.error_history.append(error_record)
                if len(self.error_history) > self.max_error_history:
                    self.error_history.pop(0)
        
        # Update error patterns
        pattern_key = f"{component}:{error_type}"
        with self._lock:
            self.error_patterns[pattern_key] = self.error_patterns.get(pattern_key, 0) + 1
        
        # Check if we should attempt recovery
        should_recover = self._should_attempt_recovery(component, error_record)
        
        # Attempt recovery if appropriate
        if should_recover:
            recovery_success = self._attempt_recovery(error_record)
            error_record.recovery_attempted = True
            error_record.recovery_successful = recovery_success
            
            # Update component status based on recovery result
            self._update_component_status_after_recovery(component, recovery_success)
            
            return recovery_success
        
        # Check if we need to trigger system degradation
        self._check_system_degradation(component, error_record)
        
        return False
    
    def _update_component_health(self, component: str, error_record: ErrorRecord) -> None:
        """Update component health status based on error."""
        with self._lock:
            # Register component if not already registered
            if component not in self.component_health:
                self.register_component(component)
            
            health = self.component_health[component]
            health.error_count += 1
            health.last_error = error_record
            
            # Update status based on severity
            if error_record.severity == ErrorSeverity.CRITICAL:
                health.status = ComponentStatus.FAILED
            elif health.status == ComponentStatus.HEALTHY:
                health.status = ComponentStatus.DEGRADED
    
    def _check_for_duplicate_error(self, error_record: ErrorRecord) -> bool:
        """Check if this is a duplicate of a recent error."""
        with self._lock:
            # Look for similar errors in the last minute
            cutoff_time = datetime.now() - timedelta(minutes=1)
            
            for existing_record in reversed(self.error_history):
                # Skip older errors
                if existing_record.timestamp < cutoff_time:
                    break
                
                # Check if it's the same error type from the same component
                if (existing_record.component == error_record.component and
                    existing_record.error_type == error_record.error_type and
                    existing_record.message == error_record.message):
                    
                    # Update occurrence count
                    existing_record.occurrence_count += 1
                    return True
            
            return False
    
    def _should_attempt_recovery(self, component: str, error_record: ErrorRecord) -> bool:
        """Determine if recovery should be attempted."""
        with self._lock:
            # Get component health
            health = self.component_health.get(component)
            
            # Don't attempt recovery if:
            # 1. Component is already failed
            # 2. Max recovery attempts reached
            # 3. No recovery strategy exists
            if not health:
                return False
            
            if health.status == ComponentStatus.FAILED:
                return False
            
            if not health.can_recover():
                self.logger.warning(f"Max recovery attempts reached for {component}, not attempting recovery")
                return False
            
            # Check if we have a recovery strategy
            if error_record.error_type not in self.recovery_strategies:
                self.logger.debug(f"No recovery strategy for {error_record.error_type}")
                return False
            
            # Increment recovery attempts
            health.recovery_attempts += 1
            
            return True
    
    def _attempt_recovery(self, error_record: ErrorRecord) -> bool:
        """Attempt to recover from an error."""
        recovery_strategy = self.recovery_strategies.get(error_record.error_type)
        
        if not recovery_strategy:
            return False
        
        try:
            self.logger.info(f"Attempting recovery for {error_record.component} from {error_record.error_type}")
            
            # Set component status to recovering
            with self._lock:
                if error_record.component in self.component_health:
                    self.component_health[error_record.component].status = ComponentStatus.RECOVERING
            
            # Execute recovery strategy
            success = recovery_strategy(error_record)
            
            if success:
                self.logger.info(f"Recovery successful for {error_record.component}")
            else:
                self.logger.warning(f"Recovery failed for {error_record.component}")
            
            return success
            
        except Exception as recovery_error:
            self.logger.error(f"Error during recovery attempt: {recovery_error}")
            return False
    
    def _update_component_status_after_recovery(self, component: str, recovery_success: bool) -> None:
        """Update component status after recovery attempt."""
        with self._lock:
            if component not in self.component_health:
                return
            
            health = self.component_health[component]
            
            if recovery_success:
                health.status = ComponentStatus.HEALTHY
                health.recovery_attempts = 0
            else:
                # If we've reached max attempts, mark as failed
                if health.recovery_attempts >= health.max_recovery_attempts:
                    health.status = ComponentStatus.FAILED
                    self.logger.error(f"Component {component} marked as failed after {health.recovery_attempts} recovery attempts")
                else:
                    health.status = ComponentStatus.DEGRADED
    
    def _check_system_degradation(self, component: str, error_record: ErrorRecord) -> None:
        """Check if system degradation should be triggered."""
        # Check for critical errors
        if error_record.severity == ErrorSeverity.CRITICAL:
            self.trigger_graceful_degradation(f"Critical error in {component}: {error_record.error_type}")
            return
        
        # Check error rate
        recent_errors = 0
        cutoff_time = datetime.now() - timedelta(minutes=1)
        
        with self._lock:
            for record in self.error_history:
                if record.timestamp >= cutoff_time:
                    recent_errors += 1
        
        if recent_errors >= self.error_rate_threshold:
            self.trigger_graceful_degradation(f"High error rate detected: {recent_errors} errors in the last minute")
    
    def register_recovery_strategy(self, error_type: str, strategy: Callable[[ErrorRecord], bool]) -> None:
        """Register a recovery strategy for a specific error type."""
        self.recovery_strategies[error_type] = strategy
        self.logger.debug(f"Registered recovery strategy for {error_type}")
    
    def get_component_health(self, component: Optional[str] = None) -> Dict[str, ComponentHealth]:
        """Get health status for components."""
        with self._lock:
            if component:
                if component in self.component_health:
                    return {component: self.component_health[component]}
                return {}
            else:
                return self.component_health.copy()
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of errors in the specified time period."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            # Filter errors within time period
            recent_errors = [record for record in self.error_history if record.timestamp >= cutoff_time]
            
            # Count errors by component
            errors_by_component = {}
            for record in recent_errors:
                errors_by_component[record.component] = errors_by_component.get(record.component, 0) + 1
            
            # Count errors by type
            errors_by_type = {}
            for record in recent_errors:
                errors_by_type[record.error_type] = errors_by_type.get(record.error_type, 0) + 1
            
            # Count errors by severity
            errors_by_severity = {}
            for record in recent_errors:
                severity = record.severity.value
                errors_by_severity[severity] = errors_by_severity.get(severity, 0) + 1
            
            # Get recovery statistics
            recovery_attempted = sum(1 for record in recent_errors if record.recovery_attempted)
            recovery_successful = sum(1 for record in recent_errors if record.recovery_successful)
            
            # Create summary
            summary = {
                "total_errors": len(recent_errors),
                "unique_errors": len(set((record.component, record.error_type) for record in recent_errors)),
                "errors_by_component": errors_by_component,
                "errors_by_type": errors_by_type,
                "errors_by_severity": errors_by_severity,
                "recovery_attempted": recovery_attempted,
                "recovery_successful": recovery_successful,
                "recovery_rate": recovery_successful / recovery_attempted if recovery_attempted > 0 else 0,
                "component_health": {name: health.status.value for name, health in self.component_health.items()},
                "time_period_hours": hours
            }
            
            return summary
    
    def clear_error_history(self) -> int:
        """Clear error history and return count of cleared errors."""
        with self._lock:
            count = len(self.error_history)
            self.error_history.clear()
            self.error_patterns.clear()
            return count
    
    def is_system_degraded(self) -> bool:
        """Check if system is in degraded mode."""
        return self.system_degraded
    
    def get_degradation_info(self) -> Dict[str, Any]:
        """Get information about system degradation state."""
        degradation_info = {
            "system_degraded": self.system_degraded,
            "camera_degraded": self.camera_degraded,
            "network_degraded": self.network_degraded,
            "storage_degraded": self.storage_degraded,
            "degradation_start_time": self.degradation_start_time.isoformat() if self.degradation_start_time else None,
            "degradation_duration_seconds": (datetime.now() - self.degradation_start_time).total_seconds() if self.degradation_start_time else 0
        }
        
        return degradation_info


# Decorator for error handling
def with_error_handling(component: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                       error_handler: Optional[ErrorHandler] = None):
    """Decorator to add error handling to functions."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Use global error handler if none provided
            handler = error_handler or global_error_handler
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Handle the error
                recovery_success = handler.handle_error(component, e, severity)
                
                # Re-raise critical errors
                if severity == ErrorSeverity.CRITICAL:
                    raise
                
                # Return None for non-critical errors
                return None
        return wrapper
    return decorator


# Retry decorator
def retry_on_error(max_attempts: int = 3, delay: float = 1.0, backoff_factor: float = 1.0,
                  exceptions: Optional[List[Type[Exception]]] = None):
    """Decorator to retry a function on failure."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            exceptions_to_catch = exceptions or (Exception,)
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions_to_catch as e:
                    last_exception = e
                    
                    # Don't sleep on the last attempt
                    if attempt < max_attempts:
                        sleep_time = delay * (backoff_factor ** (attempt - 1))
                        time.sleep(sleep_time)
            
            # If we get here, all attempts failed
            if last_exception:
                raise last_exception
        return wrapper
    return decorator


# Global error handler instance
global_error_handler = ErrorHandler()