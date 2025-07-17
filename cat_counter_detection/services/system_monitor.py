"""System monitoring and auto-recovery service."""

import logging
import os
import time
import threading
import gc
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from .interfaces import SystemMonitorInterface

# Handle optional imports gracefully
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

logger = logging.getLogger(__name__)


class ServiceStatus:
    """Status of a monitored service."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class SystemMonitor(SystemMonitorInterface):
    """System monitoring and auto-recovery service."""
    
    def __init__(self, 
                 max_cpu_usage: float = 80.0,
                 max_memory_usage: float = 80.0,
                 max_temperature: float = 80.0,
                 check_interval_seconds: int = 60):
        """
        Initialize system monitor.
        
        Args:
            max_cpu_usage: Maximum allowed CPU usage percentage
            max_memory_usage: Maximum allowed memory usage percentage
            max_temperature: Maximum allowed temperature in Celsius
            check_interval_seconds: Interval between health checks
        """
        self.max_cpu_usage = max_cpu_usage
        self.max_memory_usage = max_memory_usage
        self.max_temperature = max_temperature
        self.check_interval_seconds = check_interval_seconds
        
        # Service registry
        self.services: Dict[str, Dict[str, Any]] = {}
        
        # Monitoring state
        self.monitoring_active = False
        self.monitoring_thread = None
        self.last_check_time = None
        self.system_stats = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "temperature": 0.0,
            "disk_usage": 0.0,
            "uptime": 0.0,
            "last_updated": None
        }
        
        # Recovery history
        self.recovery_history: List[Dict[str, Any]] = []
        self.max_history_entries = 100
    
    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        if not PSUTIL_AVAILABLE:
            return 0.0
        
        try:
            return psutil.cpu_percent(interval=0.1)
        except Exception as e:
            logger.error(f"Error getting CPU usage: {e}")
            return 0.0
    
    def get_memory_usage(self) -> float:
        """Get current memory usage percentage."""
        if not PSUTIL_AVAILABLE:
            return 0.0
        
        try:
            return psutil.virtual_memory().percent
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return 0.0
    
    def get_temperature(self) -> float:
        """Get system temperature in Celsius."""
        if not PSUTIL_AVAILABLE:
            return 0.0
        
        try:
            temps = psutil.sensors_temperatures()
            if not temps:
                return 0.0
            
            # Try to find CPU temperature
            for name, entries in temps.items():
                if name.lower() in ('cpu_thermal', 'coretemp', 'cpu'):
                    return max(entry.current for entry in entries)
            
            # If no CPU temp found, return the highest temperature
            return max(entry.current for entries in temps.values() for entry in entries)
            
        except Exception as e:
            logger.error(f"Error getting temperature: {e}")
            return 0.0
    
    def is_service_healthy(self, service_name: str) -> bool:
        """Check if a service is healthy."""
        if service_name not in self.services:
            logger.warning(f"Service {service_name} not registered for health checks")
            return False
        
        service = self.services[service_name]
        
        try:
            # Call health check function
            if service["health_check"]:
                is_healthy = service["health_check"]()
                
                # Update service status
                service["last_check"] = datetime.now()
                service["status"] = ServiceStatus.HEALTHY if is_healthy else ServiceStatus.CRITICAL
                
                return is_healthy
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking health of {service_name}: {e}")
            service["status"] = ServiceStatus.UNKNOWN
            service["last_error"] = str(e)
            return False
    
    def restart_service(self, service_name: str) -> bool:
        """Restart a failed service."""
        if service_name not in self.services:
            logger.warning(f"Service {service_name} not registered for restart")
            return False
        
        service = self.services[service_name]
        
        try:
            # Call restart function
            if service["restart_func"]:
                success = service["restart_func"]()
                
                # Update service status
                service["last_restart"] = datetime.now()
                service["restart_count"] += 1
                
                # Add to recovery history
                self._add_recovery_event(service_name, success)
                
                if success:
                    logger.info(f"Successfully restarted service {service_name}")
                else:
                    logger.error(f"Failed to restart service {service_name}")
                
                return success
            
            return False
            
        except Exception as e:
            logger.error(f"Error restarting {service_name}: {e}")
            service["last_error"] = str(e)
            
            # Add to recovery history
            self._add_recovery_event(service_name, False, str(e))
            
            return False
    
    def trigger_garbage_collection(self) -> None:
        """Trigger garbage collection to free memory."""
        try:
            # Get memory before GC
            before = self.get_memory_usage()
            
            # Run garbage collection
            gc.collect()
            
            # Get memory after GC
            after = self.get_memory_usage()
            
            logger.info(f"Garbage collection completed: {before:.1f}% -> {after:.1f}% memory usage")
            
        except Exception as e:
            logger.error(f"Error during garbage collection: {e}")
    
    def register_service(self, 
                       service_name: str,
                       health_check: Callable[[], bool],
                       restart_func: Optional[Callable[[], bool]] = None,
                       check_interval_seconds: Optional[int] = None) -> None:
        """
        Register a service for health monitoring.
        
        Args:
            service_name: Unique name for the service
            health_check: Function that returns True if service is healthy
            restart_func: Function to restart the service
            check_interval_seconds: Custom check interval for this service
        """
        self.services[service_name] = {
            "name": service_name,
            "health_check": health_check,
            "restart_func": restart_func,
            "check_interval": check_interval_seconds or self.check_interval_seconds,
            "status": ServiceStatus.UNKNOWN,
            "last_check": None,
            "last_restart": None,
            "restart_count": 0,
            "last_error": None
        }
        
        logger.info(f"Registered service {service_name} for health monitoring")
    
    def start_monitoring(self) -> None:
        """Start system monitoring."""
        if self.monitoring_active:
            logger.warning("Monitoring is already active")
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger.info("System monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop system monitoring."""
        self.monitoring_active = False
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5.0)
        
        logger.info("System monitoring stopped")
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                # Update system stats
                self._update_system_stats()
                
                # Check for resource issues
                self._check_resource_usage()
                
                # Check service health
                self._check_services_health()
                
                # Update last check time
                self.last_check_time = datetime.now()
                
                # Sleep until next check
                time.sleep(self.check_interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.check_interval_seconds)
    
    def _update_system_stats(self) -> None:
        """Update system statistics."""
        self.system_stats = {
            "cpu_usage": self.get_cpu_usage(),
            "memory_usage": self.get_memory_usage(),
            "temperature": self.get_temperature(),
            "disk_usage": self._get_disk_usage(),
            "uptime": self._get_uptime(),
            "last_updated": datetime.now()
        }
    
    def _check_resource_usage(self) -> None:
        """Check system resource usage and take action if needed."""
        # Check CPU usage with automatic adjustments
        if self.system_stats["cpu_usage"] > self.max_cpu_usage:
            logger.warning(f"High CPU usage: {self.system_stats['cpu_usage']:.1f}% (max: {self.max_cpu_usage:.1f}%)")
            self._handle_high_cpu_usage()
        
        # Check memory usage with automatic adjustments
        if self.system_stats["memory_usage"] > self.max_memory_usage:
            logger.warning(f"High memory usage: {self.system_stats['memory_usage']:.1f}% (max: {self.max_memory_usage:.1f}%)")
            self._handle_high_memory_usage()
        
        # Check temperature with automatic adjustments
        if self.system_stats["temperature"] > self.max_temperature:
            logger.warning(f"High temperature: {self.system_stats['temperature']:.1f}°C (max: {self.max_temperature:.1f}°C)")
            self._handle_high_temperature()
    
    def _handle_high_cpu_usage(self) -> None:
        """Handle high CPU usage with automatic adjustments."""
        try:
            # Trigger performance optimization callback if available
            for service_name, service in self.services.items():
                if hasattr(service, 'optimize_for_high_cpu'):
                    try:
                        service['optimize_for_high_cpu']()
                        logger.info(f"Applied CPU optimization to {service_name}")
                    except Exception as e:
                        logger.error(f"Error applying CPU optimization to {service_name}: {e}")
            
            # Add recovery event
            self._add_recovery_event("system", True, "High CPU usage - applied optimizations")
            
        except Exception as e:
            logger.error(f"Error handling high CPU usage: {e}")
            self._add_recovery_event("system", False, f"High CPU handling failed: {e}")
    
    def _handle_high_memory_usage(self) -> None:
        """Handle high memory usage with automatic adjustments."""
        try:
            # Trigger garbage collection
            self.trigger_garbage_collection()
            
            # Wait a moment and check if memory usage improved
            import time
            time.sleep(2)
            new_memory_usage = self.get_memory_usage()
            
            if new_memory_usage < self.system_stats["memory_usage"]:
                logger.info(f"Memory usage improved: {self.system_stats['memory_usage']:.1f}% -> {new_memory_usage:.1f}%")
                self._add_recovery_event("memory", True, "Garbage collection successful")
            else:
                logger.warning("Garbage collection did not significantly reduce memory usage")
                self._add_recovery_event("memory", False, "Garbage collection insufficient")
                
                # Try more aggressive memory management
                self._aggressive_memory_cleanup()
            
        except Exception as e:
            logger.error(f"Error handling high memory usage: {e}")
            self._add_recovery_event("memory", False, f"Memory handling failed: {e}")
    
    def _handle_high_temperature(self) -> None:
        """Handle high temperature with automatic adjustments."""
        try:
            # Trigger performance throttling for temperature control
            for service_name, service in self.services.items():
                if hasattr(service, 'throttle_for_temperature'):
                    try:
                        service['throttle_for_temperature']()
                        logger.info(f"Applied temperature throttling to {service_name}")
                    except Exception as e:
                        logger.error(f"Error applying temperature throttling to {service_name}: {e}")
            
            # Add recovery event
            self._add_recovery_event("temperature", True, "High temperature - applied throttling")
            
        except Exception as e:
            logger.error(f"Error handling high temperature: {e}")
            self._add_recovery_event("temperature", False, f"Temperature handling failed: {e}")
    
    def _aggressive_memory_cleanup(self) -> None:
        """Perform aggressive memory cleanup for ARM systems."""
        try:
            import gc
            
            # Force multiple garbage collection cycles
            for i in range(3):
                collected = gc.collect()
                logger.debug(f"Aggressive GC cycle {i+1}: collected {collected} objects")
            
            # Clear any available caches
            if hasattr(gc, 'set_threshold'):
                # Temporarily set very aggressive GC thresholds
                old_thresholds = gc.get_threshold()
                gc.set_threshold(100, 5, 5)  # Very aggressive
                
                # Restore after a brief period
                import threading
                def restore_thresholds():
                    import time
                    time.sleep(30)  # 30 seconds
                    gc.set_threshold(*old_thresholds)
                    logger.info("Restored normal GC thresholds")
                
                threading.Thread(target=restore_thresholds, daemon=True).start()
                logger.info("Applied aggressive GC thresholds temporarily")
            
        except Exception as e:
            logger.error(f"Error during aggressive memory cleanup: {e}")
    
    def _check_services_health(self) -> None:
        """Check health of all registered services."""
        for service_name, service in self.services.items():
            # Check if it's time to check this service
            if (service["last_check"] is None or 
                (datetime.now() - service["last_check"]).total_seconds() >= service["check_interval"]):
                
                # Check service health
                is_healthy = self.is_service_healthy(service_name)
                
                # If unhealthy, try to restart
                if not is_healthy and service["restart_func"]:
                    logger.warning(f"Service {service_name} is unhealthy, attempting restart")
                    self.restart_service(service_name)
    
    def _get_disk_usage(self) -> float:
        """Get disk usage percentage."""
        if not PSUTIL_AVAILABLE:
            return 0.0
        
        try:
            return psutil.disk_usage('/').percent
        except Exception as e:
            logger.error(f"Error getting disk usage: {e}")
            return 0.0
    
    def _get_uptime(self) -> float:
        """Get system uptime in seconds."""
        if not PSUTIL_AVAILABLE:
            return 0.0
        
        try:
            return time.time() - psutil.boot_time()
        except Exception as e:
            logger.error(f"Error getting uptime: {e}")
            return 0.0
    
    def _add_recovery_event(self, 
                          service_name: str, 
                          success: bool, 
                          error_message: Optional[str] = None) -> None:
        """Add a recovery event to history."""
        event = {
            "timestamp": datetime.now(),
            "service": service_name,
            "success": success,
            "error": error_message,
            "system_stats": {
                "cpu_usage": self.system_stats["cpu_usage"],
                "memory_usage": self.system_stats["memory_usage"]
            }
        }
        
        self.recovery_history.append(event)
        
        # Trim history if needed
        if len(self.recovery_history) > self.max_history_entries:
            self.recovery_history = self.recovery_history[-self.max_history_entries:]
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get complete system health information."""
        return {
            "system": self.system_stats,
            "services": {
                name: {
                    "status": service["status"],
                    "last_check": service["last_check"],
                    "last_restart": service["last_restart"],
                    "restart_count": service["restart_count"],
                    "last_error": service["last_error"]
                }
                for name, service in self.services.items()
            },
            "monitoring": {
                "active": self.monitoring_active,
                "last_check": self.last_check_time,
                "check_interval": self.check_interval_seconds
            },
            "thresholds": {
                "max_cpu_usage": self.max_cpu_usage,
                "max_memory_usage": self.max_memory_usage,
                "max_temperature": self.max_temperature
            },
            "recovery_history": [
                {
                    "timestamp": event["timestamp"].isoformat(),
                    "service": event["service"],
                    "success": event["success"],
                    "error": event["error"]
                }
                for event in self.recovery_history[-5:]  # Last 5 events
            ]
        }
    
    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """Get status of a specific service."""
        if service_name not in self.services:
            return {"error": f"Service {service_name} not found"}
        
        service = self.services[service_name]
        return {
            "name": service["name"],
            "status": service["status"],
            "last_check": service["last_check"].isoformat() if service["last_check"] else None,
            "last_restart": service["last_restart"].isoformat() if service["last_restart"] else None,
            "restart_count": service["restart_count"],
            "last_error": service["last_error"]
        }
    
    def set_thresholds(self, 
                     max_cpu_usage: Optional[float] = None,
                     max_memory_usage: Optional[float] = None,
                     max_temperature: Optional[float] = None) -> None:
        """Update monitoring thresholds."""
        if max_cpu_usage is not None:
            self.max_cpu_usage = max(0.0, min(100.0, max_cpu_usage))
        
        if max_memory_usage is not None:
            self.max_memory_usage = max(0.0, min(100.0, max_memory_usage))
        
        if max_temperature is not None:
            self.max_temperature = max(0.0, max_temperature)
        
        logger.info(f"Updated monitoring thresholds: CPU={self.max_cpu_usage}%, "
                   f"Memory={self.max_memory_usage}%, Temp={self.max_temperature}°C")