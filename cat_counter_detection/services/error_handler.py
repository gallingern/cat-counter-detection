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
    UNKNOWN = "unknown"


@dataclass
class ErrorRecord:
    """Record of an error occurrence."""
    component_name: str
    error: Exception
    severity: ErrorSeverity
    timestamp: datetime = field(default_factory=datetime.now)
    traceback_str: str = ""
    handled: bool = False
    recovery_attempted: bool = False
    recovery_successful: bool = False


class ErrorHandler:
    """Central error handling system with recovery mechanisms."""
    
    def __init__(self):
        """Initialize error handler."""
        self.logger = logging.getLogger("error_handler")
        self.error_records: List[ErrorRecord] = []
        self.component_error_counts: Dict[str, int] = {}
        self.component_recovery_attempts: Dict[str, int] = {}
        self.component_max_recovery_attempts: Dict[str, int] = {}
        self.recovery_callbacks: Dict[str, List[Callable]] = {}
        self.error_queue = Queue()
        self.processing_thread = None
        self.running = False
        
        # Component status tracking
        self.component_status: Dict[str, ComponentStatus] = {}
        
        # System degradation state
        self.system_degraded = False
        self.camera_degraded = False
        self.network_degraded = False
        self.storage_degraded = False
        self.degradation_start_time = None
        
        # Start background processing
        self.start_processing()
    
    def register_component(self, component_name: str, max_recovery_attempts: int = 3) -> None:
        """Register a component for error handling."""
        self.component_error_counts[component_name] = 0
        self.component_recovery_attempts[component_name] = 0
        self.component_max_recovery_attempts[component_name] = max_recovery_attempts
        self.recovery_callbacks[component_name] = []
        self.component_status[component_name] = ComponentStatus.HEALTHY
        self.logger.debug(f"Component registered: {component_name}")
    
    def register_recovery_callback(self, component_name: str, callback: Callable) -> None:
        """Register a recovery callback for a component."""
        if component_name not in self.recovery_callbacks:
            self.recovery_callbacks[component_name] = []
        
        self.recovery_callbacks[component_name].append(callback)
        self.logger.debug(f"Recovery callback registered for {component_name}")
    
    def register_recovery_strategy(self, error_type: str, recovery_function: Callable) -> None:
        """Register a recovery strategy for a specific error type."""
        if not hasattr(self, 'recovery_strategies'):
            self.recovery_strategies = {}
        
        self.recovery_strategies[error_type] = recovery_function
        self.logger.debug(f"Recovery strategy registered for error type: {error_type}")
    
    def handle_error(self, component_name: str, error: Exception, severity: ErrorSeverity) -> None:
        """Handle an error from a component."""
        # Create error record
        error_record = ErrorRecord(
            component_name=component_name,
            error=error,
            severity=severity,
            traceback_str=traceback.format_exc()
        )
        
        # Add to records
        self.error_records.append(error_record)
        
        # Update error count
        if component_name in self.component_error_counts:
            self.component_error_counts[component_name] += 1
        else:
            self.component_error_counts[component_name] = 1
        
        # Update component status
        if component_name in self.component_status:
            if severity == ErrorSeverity.CRITICAL:
                self.component_status[component_name] = ComponentStatus.FAILED
            elif severity == ErrorSeverity.HIGH:
                self.component_status[component_name] = ComponentStatus.DEGRADED
        
        # Log error
        self.logger.error(f"Error in {component_name}: {error} (Severity: {severity.value})")
        
        # Queue for processing
        self.error_queue.put(error_record)
        
        # Update system degradation state for critical errors
        if severity == ErrorSeverity.CRITICAL:
            self._update_degradation_state(component_name)
    
    def _update_degradation_state(self, component_name: str) -> None:
        """Update system degradation state based on component."""
        self.system_degraded = True
        
        if self.degradation_start_time is None:
            self.degradation_start_time = datetime.now()
        
        if "camera" in component_name.lower():
            self.camera_degraded = True
        elif "network" in component_name.lower() or "notification" in component_name.lower():
            self.network_degraded = True
        elif "storage" in component_name.lower() or "database" in component_name.lower():
            self.storage_degraded = True
    
    def start_processing(self) -> None:
        """Start background error processing."""
        if self.running:
            return
        
        self.running = True
        self.processing_thread = threading.Thread(target=self._process_errors, daemon=True)
        self.processing_thread.start()
        self.logger.debug("Error processing thread started")
    
    def stop_processing(self) -> None:
        """Stop background error processing."""
        self.running = False
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5.0)
        self.logger.debug("Error processing thread stopped")
    
    def _process_errors(self) -> None:
        """Background thread for processing errors."""
        while self.running:
            try:
                # Get error from queue with timeout
                try:
                    error_record = self.error_queue.get(timeout=1.0)
                except Empty:
                    continue
                
                # Mark as handled
                error_record.handled = True
                
                # Attempt recovery if component is registered
                component_name = error_record.component_name
                if component_name in self.component_recovery_attempts:
                    # Check if max attempts reached
                    if self.component_recovery_attempts[component_name] < self.component_max_recovery_attempts[component_name]:
                        # Attempt recovery
                        self.component_recovery_attempts[component_name] += 1
                        error_record.recovery_attempted = True
                        
                        # Execute recovery callbacks
                        if component_name in self.recovery_callbacks and self.recovery_callbacks[component_name]:
                            try:
                                for callback in self.recovery_callbacks[component_name]:
                                    callback()
                                error_record.recovery_successful = True
                                self.logger.info(f"Recovery attempted for {component_name} (Attempt {self.component_recovery_attempts[component_name]})")
                                
                                # Update component status on successful recovery
                                if component_name in self.component_status:
                                    self.component_status[component_name] = ComponentStatus.HEALTHY
                                
                            except Exception as e:
                                self.logger.error(f"Recovery failed for {component_name}: {e}")
                    else:
                        self.logger.warning(f"Max recovery attempts reached for {component_name}")
                
                # Mark task as done
                self.error_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error in error processing thread: {e}")
                time.sleep(5.0)  # Wait longer on error
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        return {
            "total_errors": len(self.error_records),
            "component_error_counts": self.component_error_counts,
            "component_recovery_attempts": self.component_recovery_attempts,
            "system_degraded": self.system_degraded,
            "camera_degraded": self.camera_degraded,
            "network_degraded": self.network_degraded,
            "storage_degraded": self.storage_degraded
        }
    
    def reset_error_counts(self, component_name: Optional[str] = None) -> None:
        """Reset error counts for a component or all components."""
        if component_name:
            if component_name in self.component_error_counts:
                self.component_error_counts[component_name] = 0
                self.component_recovery_attempts[component_name] = 0
                self.component_status[component_name] = ComponentStatus.HEALTHY
        else:
            for component in self.component_error_counts:
                self.component_error_counts[component] = 0
                self.component_recovery_attempts[component] = 0
                self.component_status[component] = ComponentStatus.HEALTHY
    
    def attempt_system_recovery(self) -> bool:
        """Attempt recovery for all degraded components."""
        if not self.system_degraded:
            return False
        
        recovery_success = True
        
        # Trigger recovery callbacks
        for component_name, callbacks in self.recovery_callbacks.items():
            for callback in callbacks:
                try:
                    callback()
                    # Update component status on successful recovery
                    if component_name in self.component_status:
                        self.component_status[component_name] = ComponentStatus.HEALTHY
                except Exception as e:
                    self.logger.error(f"Error in recovery callback for {component_name}: {e}")
                    recovery_success = False
        
        if recovery_success:
            self.system_degraded = False
            self.camera_degraded = False
            self.network_degraded = False
            self.storage_degraded = False
            self.degradation_start_time = None
            self.logger.info("System recovery successful")
        
        return recovery_success
    
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
    
    def is_system_degraded(self) -> bool:
        """Check if system is in degraded mode."""
        return self.system_degraded
    
    def get_component_health(self) -> Dict[str, ComponentStatus]:
        """Get health status of all registered components."""
        return self.component_status
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of errors in the last N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Filter errors by time
        recent_errors = [e for e in self.error_records if e.timestamp >= cutoff_time]
        
        # Count errors by component and severity
        component_counts = {}
        severity_counts = {
            ErrorSeverity.LOW.value: 0,
            ErrorSeverity.MEDIUM.value: 0,
            ErrorSeverity.HIGH.value: 0,
            ErrorSeverity.CRITICAL.value: 0
        }
        
        for error in recent_errors:
            # Count by component
            if error.component_name not in component_counts:
                component_counts[error.component_name] = 0
            component_counts[error.component_name] += 1
            
            # Count by severity
            severity_counts[error.severity.value] += 1
        
        return {
            "total_errors": len(recent_errors),
            "component_counts": component_counts,
            "severity_counts": severity_counts,
            "time_period_hours": hours
        }


# Create global error handler instance
global_error_handler = ErrorHandler()


def with_error_handling(component_name: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM):
    """Decorator for functions to add error handling."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                global_error_handler.handle_error(component_name, e, severity)
                # Re-raise critical errors
                if severity == ErrorSeverity.CRITICAL:
                    raise
                # Return None for non-critical errors
                return None
        return wrapper
    return decorator


def retry_on_error(max_retries: int = 3, delay_seconds: float = 1.0, 
                  backoff_factor: float = 2.0, component_name: str = "unknown",
                  severity: ErrorSeverity = ErrorSeverity.MEDIUM):
    """Decorator for retrying functions on failure with exponential backoff."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay_seconds
            
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    
                    # Log and handle error
                    error_msg = f"Error in {func.__name__} (retry {retries}/{max_retries}): {e}"
                    if retries >= max_retries:
                        global_error_handler.handle_error(component_name, e, severity)
                        if severity == ErrorSeverity.CRITICAL:
                            raise
                        return None
                    
                    # Log warning for retry
                    logging.warning(error_msg)
                    
                    # Wait before retry with exponential backoff
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
            
            return None  # Should not reach here, but just in case
        return wrapper
    return decorator