"""Configuration management system with scheduling and hot-reload."""

import json
import os
import threading
import time
from datetime import datetime, time as dt_time
from typing import Optional, Dict, Any, Callable, List
from .models.config import SystemConfig
from .config.defaults import DEFAULT_CONFIG, DEFAULT_PATHS


class ConfigManager:
    """Manages system configuration with file persistence, scheduling, and hot-reload."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or DEFAULT_PATHS["config_file"]
        self._config: Optional[SystemConfig] = None
        
        # Hot-reload functionality
        self._file_watcher_thread = None
        self._watching = False
        self._last_modified = None
        self._config_change_callbacks: List[Callable[[SystemConfig], None]] = []
        
        # Scheduling functionality
        self._schedule_thread = None
        self._schedule_running = False
        self._scheduled_configs: List[Dict[str, Any]] = []
        
        # Load initial configuration
        self.load_config()
        
        # Get initial file modification time
        if os.path.exists(self.config_path):
            self._last_modified = os.path.getmtime(self.config_path)
    
    def load_config(self) -> SystemConfig:
        """Load configuration from file or create default."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config_dict = json.load(f)
                self._config = SystemConfig(**config_dict)
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Error loading config: {e}. Using defaults.")
                self._config = SystemConfig()
        else:
            self._config = SystemConfig()
            self.save_config()
        
        return self._config
    
    def save_config(self) -> None:
        """Save current configuration to file."""
        if self._config is None:
            return
        
        config_dict = {
            'confidence_threshold': self._config.confidence_threshold,
            'detection_roi': self._config.detection_roi,
            'detection_sensitivity': self._config.detection_sensitivity,
            'min_detection_size': self._config.min_detection_size,
            'temporal_consistency_frames': self._config.temporal_consistency_frames,
            'monitoring_enabled': self._config.monitoring_enabled,
            'monitoring_start_hour': self._config.monitoring_start_hour,
            'monitoring_end_hour': self._config.monitoring_end_hour,
            'monitoring_days': list(self._config.monitoring_days),
            'push_notifications_enabled': self._config.push_notifications_enabled,
            'email_notifications_enabled': self._config.email_notifications_enabled,
            'notification_cooldown_minutes': self._config.notification_cooldown_minutes,
            'notification_max_per_hour': self._config.notification_max_per_hour,
            'notification_quiet_hours_start': self._config.notification_quiet_hours_start,
            'notification_quiet_hours_end': self._config.notification_quiet_hours_end,
            'notification_quiet_hours_enabled': self._config.notification_quiet_hours_enabled,
            'max_storage_days': self._config.max_storage_days,
            'image_quality': self._config.image_quality,
            'auto_cleanup_enabled': self._config.auto_cleanup_enabled,
            'target_fps': self._config.target_fps,
            'max_cpu_usage': self._config.max_cpu_usage,
            'adaptive_performance': self._config.adaptive_performance
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    def get_config(self) -> SystemConfig:
        """Get current configuration."""
        if self._config is None:
            return self.load_config()
        return self._config
    
    def update_config(self, **kwargs) -> None:
        """Update configuration with new values."""
        if self._config is None:
            self.load_config()
        
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
        
        self.save_config()
        
        # Notify callbacks of config change
        for callback in self._config_change_callbacks:
            try:
                callback(self._config)
            except Exception as e:
                print(f"Error in config change callback: {e}")
    
    def validate_config(self) -> bool:
        """Validate current configuration."""
        if self._config is None:
            return False
        
        # Validate confidence threshold
        if not 0.0 <= self._config.confidence_threshold <= 1.0:
            return False
        
        # Validate detection sensitivity
        if self._config.detection_sensitivity not in ['low', 'medium', 'high']:
            return False
        
        # Validate detection parameters
        if (self._config.min_detection_size < 10 or
            self._config.temporal_consistency_frames < 1):
            return False
        
        # Validate monitoring hours
        if not (0 <= self._config.monitoring_start_hour <= 23 and 
                0 <= self._config.monitoring_end_hour <= 23):
            return False
        
        # Validate monitoring days (should be 7 boolean values)
        if (len(self._config.monitoring_days) != 7 or
            not all(isinstance(day, bool) for day in self._config.monitoring_days)):
            return False
        
        # Validate ROI
        roi = self._config.detection_roi
        if not (roi[0] >= 0 and roi[1] >= 0 and roi[2] > 0 and roi[3] > 0):
            return False
        
        # Validate notification settings
        if (self._config.notification_cooldown_minutes < 0 or
            self._config.notification_max_per_hour < 1 or
            not (0 <= self._config.notification_quiet_hours_start <= 23) or
            not (0 <= self._config.notification_quiet_hours_end <= 23)):
            return False
        
        # Validate storage settings
        if (self._config.max_storage_days < 1 or
            not 1 <= self._config.image_quality <= 100):
            return False
        
        # Validate performance settings
        if (self._config.target_fps <= 0 or
            self._config.max_cpu_usage <= 0):
            return False
        
        return True
    
    # Hot-reload functionality
    
    def start_file_watcher(self, check_interval: float = 5.0) -> None:
        """Start watching config file for changes."""
        if self._watching:
            return
        
        self._watching = True
        self._file_watcher_thread = threading.Thread(
            target=self._file_watcher_loop,
            args=(check_interval,),
            daemon=True
        )
        self._file_watcher_thread.start()
        print(f"Started watching config file: {self.config_path}")
    
    def stop_file_watcher(self) -> None:
        """Stop watching config file."""
        self._watching = False
        if self._file_watcher_thread and self._file_watcher_thread.is_alive():
            self._file_watcher_thread.join(timeout=1.0)
        print("Stopped watching config file")
    
    def _file_watcher_loop(self, check_interval: float) -> None:
        """Background thread to watch for config file changes."""
        while self._watching:
            try:
                if os.path.exists(self.config_path):
                    current_mtime = os.path.getmtime(self.config_path)
                    
                    if self._last_modified and current_mtime > self._last_modified:
                        print(f"Config file changed, reloading: {self.config_path}")
                        old_config = self._config
                        self.load_config()
                        self._last_modified = current_mtime
                        
                        # Notify callbacks of config change
                        for callback in self._config_change_callbacks:
                            try:
                                callback(self._config)
                            except Exception as e:
                                print(f"Error in config change callback: {e}")
                    
                    self._last_modified = current_mtime
            except Exception as e:
                print(f"Error watching config file: {e}")
            
            time.sleep(check_interval)
    
    def register_change_callback(self, callback: Callable[[SystemConfig], None]) -> None:
        """Register a callback to be called when config changes."""
        if callback not in self._config_change_callbacks:
            self._config_change_callbacks.append(callback)
    
    def unregister_change_callback(self, callback: Callable[[SystemConfig], None]) -> None:
        """Unregister a config change callback."""
        if callback in self._config_change_callbacks:
            self._config_change_callbacks.remove(callback)
    
    # Scheduling functionality
    
    def add_scheduled_config(self, 
                           config_changes: Dict[str, Any], 
                           schedule_time: dt_time,
                           days_of_week: Optional[List[int]] = None) -> int:
        """
        Schedule configuration changes to occur at specific times.
        
        Args:
            config_changes: Dictionary of config changes to apply
            schedule_time: Time of day to apply changes (24-hour format)
            days_of_week: Optional list of days (0=Monday, 6=Sunday), None for every day
            
        Returns:
            Schedule ID for later reference
        """
        schedule_id = len(self._scheduled_configs)
        
        schedule = {
            'id': schedule_id,
            'config_changes': config_changes,
            'time': schedule_time,
            'days_of_week': days_of_week,
            'last_run': None,
            'enabled': True
        }
        
        self._scheduled_configs.append(schedule)
        
        # Start scheduler if not already running
        if not self._schedule_running:
            self.start_scheduler()
        
        return schedule_id
    
    def remove_scheduled_config(self, schedule_id: int) -> bool:
        """Remove a scheduled configuration by ID."""
        for i, schedule in enumerate(self._scheduled_configs):
            if schedule['id'] == schedule_id:
                self._scheduled_configs.pop(i)
                return True
        return False
    
    def start_scheduler(self, check_interval: float = 60.0) -> None:
        """Start the scheduler to apply scheduled configurations."""
        if self._schedule_running:
            return
        
        self._schedule_running = True
        self._schedule_thread = threading.Thread(
            target=self._scheduler_loop,
            args=(check_interval,),
            daemon=True
        )
        self._schedule_thread.start()
        print("Started configuration scheduler")
    
    def stop_scheduler(self) -> None:
        """Stop the configuration scheduler."""
        self._schedule_running = False
        if self._schedule_thread and self._schedule_thread.is_alive():
            self._schedule_thread.join(timeout=1.0)
        print("Stopped configuration scheduler")
    
    def _scheduler_loop(self, check_interval: float) -> None:
        """Background thread to apply scheduled configurations."""
        while self._schedule_running:
            try:
                now = datetime.now()
                current_time = now.time()
                current_day = now.weekday()  # 0=Monday, 6=Sunday
                
                for schedule in self._scheduled_configs:
                    if not schedule['enabled']:
                        continue
                    
                    # Check if day matches (if specified)
                    if schedule['days_of_week'] and current_day not in schedule['days_of_week']:
                        continue
                    
                    # Check if time matches (within check_interval window)
                    schedule_time = schedule['time']
                    schedule_seconds = schedule_time.hour * 3600 + schedule_time.minute * 60 + schedule_time.second
                    current_seconds = current_time.hour * 3600 + current_time.minute * 60 + current_time.second
                    
                    # Check if we're within the window and haven't run today
                    time_diff = abs(schedule_seconds - current_seconds)
                    if time_diff <= check_interval / 2:
                        # Check if we've already run this schedule today
                        last_run = schedule['last_run']
                        if not last_run or last_run.date() < now.date():
                            print(f"Applying scheduled config changes: {schedule['config_changes']}")
                            self.update_config(**schedule['config_changes'])
                            schedule['last_run'] = now
            
            except Exception as e:
                print(f"Error in scheduler loop: {e}")
            
            # Use a shorter sleep and check if we should stop more frequently
            for _ in range(int(check_interval)):
                if not self._schedule_running:
                    break
                time.sleep(1.0)
    
    def get_scheduled_configs(self) -> List[Dict[str, Any]]:
        """Get all scheduled configurations."""
        return [
            {
                'id': s['id'],
                'config_changes': s['config_changes'],
                'time': s['time'].strftime('%H:%M:%S'),
                'days_of_week': s['days_of_week'],
                'last_run': s['last_run'].isoformat() if s['last_run'] else None,
                'enabled': s['enabled']
            }
            for s in self._scheduled_configs
        ]
    
    def enable_scheduled_config(self, schedule_id: int, enabled: bool = True) -> bool:
        """Enable or disable a scheduled configuration."""
        for schedule in self._scheduled_configs:
            if schedule['id'] == schedule_id:
                schedule['enabled'] = enabled
                return True
        return False
    
    # Detection sensitivity management
    
    def set_detection_sensitivity(self, sensitivity: str) -> None:
        """
        Set detection sensitivity with predefined profiles.
        
        Args:
            sensitivity: 'low', 'medium', or 'high'
        """
        sensitivity_profiles = {
            'low': {
                'confidence_threshold': 0.8,
                'min_detection_size': 80,
                'temporal_consistency_frames': 3
            },
            'medium': {
                'confidence_threshold': 0.7,
                'min_detection_size': 50,
                'temporal_consistency_frames': 2
            },
            'high': {
                'confidence_threshold': 0.6,
                'min_detection_size': 30,
                'temporal_consistency_frames': 1
            }
        }
        
        if sensitivity in sensitivity_profiles:
            profile = sensitivity_profiles[sensitivity]
            profile['detection_sensitivity'] = sensitivity
            self.update_config(**profile)
    
    def is_monitoring_active(self) -> bool:
        """Check if monitoring should be active based on current time and schedule."""
        if not self._config or not self._config.monitoring_enabled:
            return False
        
        now = datetime.now()
        current_hour = now.hour
        current_day = now.weekday()  # 0=Monday, 6=Sunday
        
        # Check if current day is enabled
        if not self._config.monitoring_days[current_day]:
            return False
        
        # Check if current time is within monitoring hours
        start_hour = self._config.monitoring_start_hour
        end_hour = self._config.monitoring_end_hour
        
        if start_hour <= end_hour:
            # Normal case: start_hour=8, end_hour=20 (8 AM to 8 PM)
            return start_hour <= current_hour <= end_hour
        else:
            # Overnight case: start_hour=20, end_hour=8 (8 PM to 8 AM)
            return current_hour >= start_hour or current_hour <= end_hour
    
    def is_notification_allowed(self) -> bool:
        """Check if notifications should be sent based on quiet hours and rate limiting."""
        if not self._config:
            return True
        
        # Check quiet hours
        if self._config.notification_quiet_hours_enabled:
            now = datetime.now()
            current_hour = now.hour
            start_hour = self._config.notification_quiet_hours_start
            end_hour = self._config.notification_quiet_hours_end
            
            if start_hour <= end_hour:
                # Normal case: start_hour=22, end_hour=7 (10 PM to 7 AM)
                if start_hour <= current_hour <= end_hour:
                    return False
            else:
                # Overnight case: start_hour=22, end_hour=7 (10 PM to 7 AM)
                if current_hour >= start_hour or current_hour <= end_hour:
                    return False
        
        return True
    
    def get_detection_parameters(self) -> Dict[str, Any]:
        """Get current detection parameters for the detection engine."""
        if not self._config:
            return {}
        
        return {
            'confidence_threshold': self._config.confidence_threshold,
            'detection_roi': self._config.detection_roi,
            'min_detection_size': self._config.min_detection_size,
            'temporal_consistency_frames': self._config.temporal_consistency_frames,
            'detection_sensitivity': self._config.detection_sensitivity
        }
    
    def get_notification_parameters(self) -> Dict[str, Any]:
        """Get current notification parameters for the notification service."""
        if not self._config:
            return {}
        
        return {
            'push_notifications_enabled': self._config.push_notifications_enabled,
            'email_notifications_enabled': self._config.email_notifications_enabled,
            'notification_cooldown_minutes': self._config.notification_cooldown_minutes,
            'notification_max_per_hour': self._config.notification_max_per_hour,
            'notification_quiet_hours_enabled': self._config.notification_quiet_hours_enabled,
            'notification_quiet_hours_start': self._config.notification_quiet_hours_start,
            'notification_quiet_hours_end': self._config.notification_quiet_hours_end
        }
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to default values."""
        self._config = SystemConfig()
        self.save_config()
        
        # Notify callbacks of config change
        for callback in self._config_change_callbacks:
            try:
                callback(self._config)
            except Exception as e:
                print(f"Error in config change callback: {e}")
    
    def export_config(self) -> Dict[str, Any]:
        """Export current configuration as a dictionary."""
        if not self._config:
            return {}
        
        return {
            'confidence_threshold': self._config.confidence_threshold,
            'detection_roi': self._config.detection_roi,
            'detection_sensitivity': self._config.detection_sensitivity,
            'min_detection_size': self._config.min_detection_size,
            'temporal_consistency_frames': self._config.temporal_consistency_frames,
            'monitoring_enabled': self._config.monitoring_enabled,
            'monitoring_start_hour': self._config.monitoring_start_hour,
            'monitoring_end_hour': self._config.monitoring_end_hour,
            'monitoring_days': list(self._config.monitoring_days),
            'push_notifications_enabled': self._config.push_notifications_enabled,
            'email_notifications_enabled': self._config.email_notifications_enabled,
            'notification_cooldown_minutes': self._config.notification_cooldown_minutes,
            'notification_max_per_hour': self._config.notification_max_per_hour,
            'notification_quiet_hours_start': self._config.notification_quiet_hours_start,
            'notification_quiet_hours_end': self._config.notification_quiet_hours_end,
            'notification_quiet_hours_enabled': self._config.notification_quiet_hours_enabled,
            'max_storage_days': self._config.max_storage_days,
            'image_quality': self._config.image_quality,
            'auto_cleanup_enabled': self._config.auto_cleanup_enabled,
            'target_fps': self._config.target_fps,
            'max_cpu_usage': self._config.max_cpu_usage,
            'adaptive_performance': self._config.adaptive_performance
        }
    
    def import_config(self, config_dict: Dict[str, Any]) -> bool:
        """
        Import configuration from a dictionary.
        
        Args:
            config_dict: Dictionary containing configuration values
            
        Returns:
            True if import was successful, False otherwise
        """
        try:
            # Create temporary config to validate
            temp_config = SystemConfig(**config_dict)
            
            # Temporarily set config for validation
            old_config = self._config
            self._config = temp_config
            
            if self.validate_config():
                # Save the new config
                self.save_config()
                
                # Notify callbacks of config change
                for callback in self._config_change_callbacks:
                    try:
                        callback(self._config)
                    except Exception as e:
                        print(f"Error in config change callback: {e}")
                
                return True
            else:
                # Restore old config if validation failed
                self._config = old_config
                return False
                
        except (TypeError, ValueError) as e:
            print(f"Error importing config: {e}")
            return False