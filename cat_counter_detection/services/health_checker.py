"""System health checking and diagnostic service."""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import os
import psutil
from cat_counter_detection.logging_config import get_logger
from cat_counter_detection.services.error_handler import ErrorHandler, ErrorSeverity, ComponentStatus


class HealthStatus(Enum):
    """Overall system health status."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    FAILED = "failed"


@dataclass
class HealthMetric:
    """Individual health metric."""
    name: str
    value: float
    unit: str
    threshold_warning: float
    threshold_critical: float
    status: HealthStatus = HealthStatus.HEALTHY
    last_updated: datetime = field(default_factory=datetime.now)
    
    def update(self, value: float) -> None:
        """Update metric value and determine status."""
        self.value = value
        self.last_updated = datetime.now()
        
        if value >= self.threshold_critical:
            self.status = HealthStatus.CRITICAL
        elif value >= self.threshold_warning:
            self.status = HealthStatus.WARNING
        else:
            self.status = HealthStatus.HEALTHY


@dataclass
class ComponentHealthCheck:
    """Health check configuration for a component."""
    name: str
    check_function: Callable[[], bool]
    check_interval: float = 30.0  # seconds
    timeout: float = 5.0  # seconds
    last_check: Optional[datetime] = None
    last_result: bool = True
    consecutive_failures: int = 0
    max_failures: int = 3


@dataclass
class SystemHealthReport:
    """Complete system health report."""
    timestamp: datetime
    overall_status: HealthStatus
    metrics: Dict[str, HealthMetric]
    component_status: Dict[str, ComponentStatus]
    alerts: List[str]
    recommendations: List[str]
    uptime_seconds: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "overall_status": self.overall_status.value,
            "metrics": {
                name: {
                    "value": metric.value,
                    "unit": metric.unit,
                    "status": metric.status.value,
                    "last_updated": metric.last_updated.isoformat()
                }
                for name, metric in self.metrics.items()
            },
            "component_status": {
                name: status.value for name, status in self.component_status.items()
            },
            "alerts": self.alerts,
            "recommendations": self.recommendations,
            "uptime_seconds": self.uptime_seconds
        }


class HealthChecker:
    """Comprehensive system health monitoring and diagnostics."""
    
    def __init__(self, error_handler: Optional[ErrorHandler] = None):
        self.logger = get_logger("health_checker")
        self.error_handler = error_handler
        
        # Health metrics
        self.metrics: Dict[str, HealthMetric] = {}
        self.component_checks: Dict[str, ComponentHealthCheck] = {}
        
        # Monitoring state
        self.monitoring = False
        self.monitor_thread = None
        self.start_time = datetime.now()
        self.check_interval = 10.0  # seconds
        
        # Initialize default metrics
        self._initialize_default_metrics()
        
        self.logger.info("Health checker initialized")
    
    def _initialize_default_metrics(self) -> None:
        """Initialize default system metrics."""
        # CPU usage
        self.metrics["cpu_usage"] = HealthMetric(
            name="CPU Usage",
            value=0.0,
            unit="%",
            threshold_warning=70.0,
            threshold_critical=90.0
        )
        
        # Memory usage
        self.metrics["memory_usage"] = HealthMetric(
            name="Memory Usage",
            value=0.0,
            unit="%",
            threshold_warning=80.0,
            threshold_critical=95.0
        )
        
        # Disk usage
        self.metrics["disk_usage"] = HealthMetric(
            name="Disk Usage",
            value=0.0,
            unit="%",
            threshold_warning=85.0,
            threshold_critical=95.0
        )
        
        # Temperature (if available)
        self.metrics["cpu_temperature"] = HealthMetric(
            name="CPU Temperature",
            value=0.0,
            unit="°C",
            threshold_warning=70.0,
            threshold_critical=80.0
        )
        
        # Error rate
        self.metrics["error_rate"] = HealthMetric(
            name="Error Rate",
            value=0.0,
            unit="errors/min",
            threshold_warning=5.0,
            threshold_critical=10.0
        )
        
        # Frame processing rate
        self.metrics["frame_rate"] = HealthMetric(
            name="Frame Rate",
            value=0.0,
            unit="fps",
            threshold_warning=0.5,  # Below 0.5 FPS is warning
            threshold_critical=0.1  # Below 0.1 FPS is critical
        )
    
    def register_component_check(self, name: str, check_function: Callable[[], bool],
                               check_interval: float = 30.0, timeout: float = 5.0,
                               max_failures: int = 3) -> None:
        """Register a health check for a component."""
        self.component_checks[name] = ComponentHealthCheck(
            name=name,
            check_function=check_function,
            check_interval=check_interval,
            timeout=timeout,
            max_failures=max_failures
        )
        self.logger.info(f"Registered health check for component: {name}")
    
    def start_monitoring(self) -> None:
        """Start continuous health monitoring."""
        if self.monitoring:
            self.logger.warning("Health monitoring is already running")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Health monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop health monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        self.logger.info("Health monitoring stopped")
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.monitoring:
            try:
                # Update system metrics
                self._update_system_metrics()
                
                # Run component health checks
                self._run_component_checks()
                
                # Check for alerts
                self._check_alerts()
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                if self.error_handler:
                    self.error_handler.handle_error(
                        "health_checker", e, ErrorSeverity.MEDIUM
                    )
                else:
                    self.logger.error(f"Error in health monitoring loop: {e}")
                
                time.sleep(self.check_interval)
    
    def _update_system_metrics(self) -> None:
        """Update system performance metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics["cpu_usage"].update(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.metrics["memory_usage"].update(memory.percent)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.metrics["disk_usage"].update(disk_percent)
            
            # CPU temperature (Raspberry Pi specific)
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp_millidegrees = int(f.read().strip())
                    temp_celsius = temp_millidegrees / 1000.0
                    self.metrics["cpu_temperature"].update(temp_celsius)
            except (FileNotFoundError, ValueError):
                # Temperature monitoring not available
                pass
            
            # Error rate from error handler
            if self.error_handler:
                error_summary = self.error_handler.get_error_summary(hours=1)
                error_rate = error_summary["total_errors"] / 60.0  # errors per minute
                self.metrics["error_rate"].update(error_rate)
            
        except Exception as e:
            self.logger.error(f"Error updating system metrics: {e}")
    
    def _run_component_checks(self) -> None:
        """Run health checks for all registered components."""
        current_time = datetime.now()
        
        for check in self.component_checks.values():
            # Check if it's time to run this check
            if (check.last_check is None or 
                (current_time - check.last_check).total_seconds() >= check.check_interval):
                
                try:
                    # Run the health check with timeout
                    result = self._run_check_with_timeout(check)
                    
                    if result:
                        check.consecutive_failures = 0
                        check.last_result = True
                    else:
                        check.consecutive_failures += 1
                        check.last_result = False
                        
                        # Handle component failure
                        if check.consecutive_failures >= check.max_failures:
                            self._handle_component_failure(check)
                    
                    check.last_check = current_time
                    
                except Exception as e:
                    self.logger.error(f"Error running health check for {check.name}: {e}")
                    check.consecutive_failures += 1
                    check.last_result = False
    
    def _run_check_with_timeout(self, check: ComponentHealthCheck) -> bool:
        """Run a health check with timeout."""
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Health check timeout for {check.name}")
        
        # Set timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(check.timeout))
        
        try:
            result = check.check_function()
            signal.alarm(0)  # Cancel timeout
            return result
        except TimeoutError:
            self.logger.warning(f"Health check timeout for {check.name}")
            return False
        except Exception as e:
            signal.alarm(0)  # Cancel timeout
            self.logger.error(f"Health check error for {check.name}: {e}")
            return False
    
    def _handle_component_failure(self, check: ComponentHealthCheck) -> None:
        """Handle component failure."""
        self.logger.error(f"Component {check.name} has failed health checks "
                         f"{check.consecutive_failures} times")
        
        if self.error_handler:
            # Create a synthetic error for the failed component
            error = RuntimeError(f"Component {check.name} failed health check")
            self.error_handler.handle_error(
                check.name, error, ErrorSeverity.HIGH
            )
    
    def _check_alerts(self) -> None:
        """Check for alert conditions and log warnings."""
        for metric in self.metrics.values():
            if metric.status == HealthStatus.CRITICAL:
                self.logger.critical(f"CRITICAL: {metric.name} is {metric.value}{metric.unit}")
            elif metric.status == HealthStatus.WARNING:
                self.logger.warning(f"WARNING: {metric.name} is {metric.value}{metric.unit}")
    
    def get_health_report(self) -> SystemHealthReport:
        """Generate comprehensive health report."""
        # Determine overall status
        overall_status = HealthStatus.HEALTHY
        alerts = []
        recommendations = []
        
        # Check metric statuses
        for metric in self.metrics.values():
            if metric.status == HealthStatus.CRITICAL:
                overall_status = HealthStatus.CRITICAL
                alerts.append(f"CRITICAL: {metric.name} is {metric.value}{metric.unit}")
            elif metric.status == HealthStatus.WARNING and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.WARNING
                alerts.append(f"WARNING: {metric.name} is {metric.value}{metric.unit}")
        
        # Get component status from error handler
        component_status = {}
        if self.error_handler:
            health_info = self.error_handler.get_component_health()
            component_status = {
                name: health.status for name, health in health_info.items()
            }
        
        # Generate recommendations
        if self.metrics["cpu_usage"].status != HealthStatus.HEALTHY:
            recommendations.append("Consider reducing detection frequency or frame resolution")
        
        if self.metrics["memory_usage"].status != HealthStatus.HEALTHY:
            recommendations.append("Restart services to free memory or reduce image quality")
        
        if self.metrics["disk_usage"].status != HealthStatus.HEALTHY:
            recommendations.append("Clean up old detection images and logs")
        
        if self.metrics["cpu_temperature"].status != HealthStatus.HEALTHY:
            recommendations.append("Check cooling and reduce system load")
        
        # Calculate uptime
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return SystemHealthReport(
            timestamp=datetime.now(),
            overall_status=overall_status,
            metrics=self.metrics.copy(),
            component_status=component_status,
            alerts=alerts,
            recommendations=recommendations,
            uptime_seconds=uptime
        )
    
    def get_diagnostic_info(self) -> Dict[str, Any]:
        """Get detailed diagnostic information."""
        diagnostic_info = {
            "system_info": self._get_system_info(),
            "resource_usage": self._get_resource_usage(),
            "hardware_info": self._get_hardware_info(),
            "network_info": self._get_network_info(),
            "storage_info": self._get_storage_info(),
            "process_info": self._get_process_info(),
            "health_metrics": {
                name: {
                    "value": metric.value,
                    "unit": metric.unit,
                    "status": metric.status.value,
                    "thresholds": {
                        "warning": metric.threshold_warning,
                        "critical": metric.threshold_critical
                    },
                    "last_updated": metric.last_updated.isoformat()
                }
                for name, metric in self.metrics.items()
            },
            "component_checks": {
                name: {
                    "last_check": check.last_check.isoformat() if check.last_check else None,
                    "last_result": check.last_result,
                    "consecutive_failures": check.consecutive_failures,
                    "max_failures": check.max_failures,
                    "check_interval": check.check_interval,
                    "timeout": check.timeout
                }
                for name, check in self.component_checks.items()
            },
            "degradation_status": self._get_degradation_status()
        }
        
        # Add error handler information if available
        if self.error_handler:
            error_summary = self.error_handler.get_error_summary(hours=24)
            diagnostic_info["error_summary"] = error_summary
            diagnostic_info["degradation_info"] = self.error_handler.get_degradation_info()
        
        return diagnostic_info
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get detailed system information."""
        try:
            uname = os.uname()
            return {
                "platform": {
                    "system": uname.sysname,
                    "node": uname.nodename,
                    "release": uname.release,
                    "version": uname.version,
                    "machine": uname.machine
                },
                "python_version": {
                    "version": os.sys.version,
                    "version_info": {
                        "major": os.sys.version_info.major,
                        "minor": os.sys.version_info.minor,
                        "micro": os.sys.version_info.micro
                    }
                },
                "process_id": os.getpid(),
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error getting system info: {e}")
            return {"error": str(e)}
    
    def _get_resource_usage(self) -> Dict[str, Any]:
        """Get detailed resource usage information."""
        try:
            cpu_info = {
                "count": psutil.cpu_count(),
                "count_logical": psutil.cpu_count(logical=True),
                "current_percent": psutil.cpu_percent(interval=1),
                "per_cpu_percent": psutil.cpu_percent(interval=1, percpu=True),
                "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else None
            }
            
            memory = psutil.virtual_memory()
            memory_info = {
                "total_mb": memory.total / (1024 * 1024),
                "available_mb": memory.available / (1024 * 1024),
                "used_mb": memory.used / (1024 * 1024),
                "percent": memory.percent,
                "free_mb": memory.free / (1024 * 1024)
            }
            
            # Add swap information
            swap = psutil.swap_memory()
            swap_info = {
                "total_mb": swap.total / (1024 * 1024),
                "used_mb": swap.used / (1024 * 1024),
                "free_mb": swap.free / (1024 * 1024),
                "percent": swap.percent
            }
            
            return {
                "cpu": cpu_info,
                "memory": memory_info,
                "swap": swap_info
            }
        except Exception as e:
            self.logger.error(f"Error getting resource usage: {e}")
            return {"error": str(e)}
    
    def _get_hardware_info(self) -> Dict[str, Any]:
        """Get hardware-specific information."""
        hardware_info = {}
        
        try:
            # CPU temperature (Raspberry Pi specific)
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp_millidegrees = int(f.read().strip())
                    hardware_info["cpu_temperature_celsius"] = temp_millidegrees / 1000.0
            except (FileNotFoundError, ValueError, PermissionError):
                hardware_info["cpu_temperature_celsius"] = None
            
            # GPU temperature (if available)
            try:
                import subprocess
                result = subprocess.run(['vcgencmd', 'measure_temp'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    temp_str = result.stdout.strip()
                    if 'temp=' in temp_str:
                        temp_value = temp_str.split('=')[1].replace("'C", "")
                        hardware_info["gpu_temperature_celsius"] = float(temp_value)
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, 
                    FileNotFoundError, ValueError):
                hardware_info["gpu_temperature_celsius"] = None
            
            # Memory split (Raspberry Pi)
            try:
                import subprocess
                result = subprocess.run(['vcgencmd', 'get_mem', 'arm'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    arm_mem = result.stdout.strip().split('=')[1]
                    hardware_info["arm_memory_mb"] = arm_mem
                
                result = subprocess.run(['vcgencmd', 'get_mem', 'gpu'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    gpu_mem = result.stdout.strip().split('=')[1]
                    hardware_info["gpu_memory_mb"] = gpu_mem
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, 
                    FileNotFoundError):
                pass
            
            # Throttling status (Raspberry Pi)
            try:
                import subprocess
                result = subprocess.run(['vcgencmd', 'get_throttled'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    throttled_hex = result.stdout.strip().split('=')[1]
                    throttled_int = int(throttled_hex, 16)
                    hardware_info["throttling_status"] = {
                        "raw_value": throttled_hex,
                        "under_voltage_detected": bool(throttled_int & 0x1),
                        "arm_frequency_capped": bool(throttled_int & 0x2),
                        "currently_throttled": bool(throttled_int & 0x4),
                        "soft_temperature_limit": bool(throttled_int & 0x8),
                        "under_voltage_occurred": bool(throttled_int & 0x10000),
                        "arm_frequency_capping_occurred": bool(throttled_int & 0x20000),
                        "throttling_occurred": bool(throttled_int & 0x40000),
                        "soft_temperature_limit_occurred": bool(throttled_int & 0x80000)
                    }
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, 
                    FileNotFoundError, ValueError):
                hardware_info["throttling_status"] = None
            
        except Exception as e:
            self.logger.error(f"Error getting hardware info: {e}")
            hardware_info["error"] = str(e)
        
        return hardware_info
    
    def _get_network_info(self) -> Dict[str, Any]:
        """Get network interface information."""
        try:
            network_info = {}
            
            # Network interfaces
            interfaces = psutil.net_if_addrs()
            interface_stats = psutil.net_if_stats()
            
            network_info["interfaces"] = {}
            for interface_name, addresses in interfaces.items():
                interface_info = {
                    "addresses": [],
                    "stats": {}
                }
                
                # Address information
                for addr in addresses:
                    addr_info = {
                        "family": str(addr.family),
                        "address": addr.address,
                        "netmask": addr.netmask,
                        "broadcast": addr.broadcast
                    }
                    interface_info["addresses"].append(addr_info)
                
                # Interface statistics
                if interface_name in interface_stats:
                    stats = interface_stats[interface_name]
                    interface_info["stats"] = {
                        "is_up": stats.isup,
                        "duplex": str(stats.duplex),
                        "speed": stats.speed,
                        "mtu": stats.mtu
                    }
                
                network_info["interfaces"][interface_name] = interface_info
            
            # Network I/O counters
            net_io = psutil.net_io_counters()
            network_info["io_counters"] = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "errin": net_io.errin,
                "errout": net_io.errout,
                "dropin": net_io.dropin,
                "dropout": net_io.dropout
            }
            
            # Test connectivity
            network_info["connectivity"] = self._test_network_connectivity()
            
            return network_info
            
        except Exception as e:
            self.logger.error(f"Error getting network info: {e}")
            return {"error": str(e)}
    
    def _test_network_connectivity(self) -> Dict[str, Any]:
        """Test network connectivity to various services."""
        connectivity = {}
        
        test_hosts = [
            ("google.com", 80),
            ("8.8.8.8", 53),
            ("1.1.1.1", 53)
        ]
        
        for host, port in test_hosts:
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex((host, port))
                sock.close()
                connectivity[f"{host}:{port}"] = result == 0
            except Exception as e:
                connectivity[f"{host}:{port}"] = False
        
        return connectivity
    
    def _get_storage_info(self) -> Dict[str, Any]:
        """Get storage and filesystem information."""
        try:
            storage_info = {}
            
            # Disk usage for all mount points
            disk_partitions = psutil.disk_partitions()
            storage_info["partitions"] = {}
            
            for partition in disk_partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    storage_info["partitions"][partition.mountpoint] = {
                        "device": partition.device,
                        "fstype": partition.fstype,
                        "opts": partition.opts,
                        "total_gb": usage.total / (1024**3),
                        "used_gb": usage.used / (1024**3),
                        "free_gb": usage.free / (1024**3),
                        "percent": (usage.used / usage.total) * 100
                    }
                except PermissionError:
                    # Skip partitions we can't access
                    continue
            
            # Disk I/O counters
            try:
                disk_io = psutil.disk_io_counters()
                if disk_io:
                    storage_info["io_counters"] = {
                        "read_count": disk_io.read_count,
                        "write_count": disk_io.write_count,
                        "read_bytes": disk_io.read_bytes,
                        "write_bytes": disk_io.write_bytes,
                        "read_time": disk_io.read_time,
                        "write_time": disk_io.write_time
                    }
            except Exception:
                storage_info["io_counters"] = None
            
            return storage_info
            
        except Exception as e:
            self.logger.error(f"Error getting storage info: {e}")
            return {"error": str(e)}
    
    def _get_process_info(self) -> Dict[str, Any]:
        """Get current process information."""
        try:
            current_process = psutil.Process()
            
            process_info = {
                "pid": current_process.pid,
                "name": current_process.name(),
                "status": current_process.status(),
                "create_time": datetime.fromtimestamp(current_process.create_time()).isoformat(),
                "cpu_percent": current_process.cpu_percent(),
                "memory_info": {
                    "rss_mb": current_process.memory_info().rss / (1024 * 1024),
                    "vms_mb": current_process.memory_info().vms / (1024 * 1024),
                    "percent": current_process.memory_percent()
                },
                "num_threads": current_process.num_threads(),
                "num_fds": current_process.num_fds() if hasattr(current_process, 'num_fds') else None,
                "connections": len(current_process.connections()),
                "cwd": current_process.cwd()
            }
            
            # Get child processes
            children = current_process.children(recursive=True)
            process_info["children"] = [
                {
                    "pid": child.pid,
                    "name": child.name(),
                    "status": child.status(),
                    "cpu_percent": child.cpu_percent(),
                    "memory_percent": child.memory_percent()
                }
                for child in children
            ]
            
            return process_info
            
        except Exception as e:
            self.logger.error(f"Error getting process info: {e}")
            return {"error": str(e)}
    
    def _get_degradation_status(self) -> Dict[str, Any]:
        """Get system degradation status."""
        degradation_status = {
            "system_degraded": False,
            "camera_degraded": False,
            "network_degraded": False,
            "storage_degraded": False,
            "degradation_start_time": None,
            "degradation_duration_seconds": 0
        }
        
        if self.error_handler:
            degradation_info = self.error_handler.get_degradation_info()
            degradation_status.update(degradation_info)
        
        return degradation_status
    
    def run_manual_health_check(self) -> SystemHealthReport:
        """Run a manual health check and return report."""
        self.logger.info("Running manual health check")
        
        # Update all metrics
        self._update_system_metrics()
        
        # Run all component checks
        self._run_component_checks()
        
        # Generate and return report
        report = self.get_health_report()
        
        self.logger.info(f"Manual health check completed - Status: {report.overall_status.value}")
        return report
        
    def _get_degradation_status(self) -> Dict[str, Any]:
        """Get system degradation status."""
        degradation_status = {
            "system_degraded": False,
            "camera_degraded": False,
            "network_degraded": False,
            "storage_degraded": False,
            "degradation_start_time": None,
            "degradation_duration_seconds": 0
        }
        
        if self.error_handler:
            degradation_info = self.error_handler.get_degradation_info()
            degradation_status.update(degradation_info)
        
        return degradation_status
    
    def run_manual_health_check(self) -> SystemHealthReport:
        """Run a manual health check and return a report."""
        # Update system metrics
        self._update_system_metrics()
        
        # Run component checks
        self._run_component_checks()
        
        # Generate and return health report
        return self.get_health_report()
    
    def _handle_component_failure(self, check: ComponentHealthCheck) -> None:
        """Handle component failure."""
        self.logger.error(f"Component {check.name} has failed health checks "
                         f"{check.consecutive_failures} times")
        
        if self.error_handler:
            # Create a synthetic error for the failed component
            error = RuntimeError(f"Component {check.name} failed health check")
            self.error_handler.handle_error(
                check.name, error, self.error_handler.ErrorSeverity.HIGH
            )
    
    def _check_alerts(self) -> None:
        """Check for alert conditions and log warnings."""
        for metric in self.metrics.values():
            if metric.status == HealthStatus.CRITICAL:
                self.logger.critical(f"CRITICAL: {metric.name} is {metric.value}{metric.unit}")
            elif metric.status == HealthStatus.WARNING:
                self.logger.warning(f"WARNING: {metric.name} is {metric.value}{metric.unit}")
    
    def _test_network_connectivity(self) -> Dict[str, Any]:
        """Test network connectivity to various services."""
        connectivity = {}
        
        test_hosts = [
            ("google.com", 80),
            ("8.8.8.8", 53),
            ("1.1.1.1", 53)
        ]
        
        for host, port in test_hosts:
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex((host, port))
                sock.close()
                connectivity[f"{host}:{port}"] = result == 0
            except Exception as e:
                connectivity[f"{host}:{port}"] = False
        
        return connectivity