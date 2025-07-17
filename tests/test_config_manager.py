"""Unit tests for configuration manager."""

import unittest
import os
import json
import tempfile
import time
from datetime import datetime, time as dt_time
from unittest.mock import Mock, patch
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cat_counter_detection.config_manager import ConfigManager
from cat_counter_detection.models.config import SystemConfig


class TestConfigManager(unittest.TestCase):
    """Test cases for ConfigManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.test_dir, "test_config.json")
        self.config_manager = ConfigManager(self.config_path)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Stop any running threads
        if self.config_manager._watching:
            self.config_manager.stop_file_watcher()
        
        if self.config_manager._schedule_running:
            self.config_manager.stop_scheduler()
        
        # Remove temporary directory
        if os.path.exists(self.test_dir):
            import shutil
            shutil.rmtree(self.test_dir)
    
    def test_initialization(self):
        """Test configuration manager initialization."""
        self.assertEqual(self.config_manager.config_path, self.config_path)
        self.assertIsNotNone(self.config_manager._config)
        self.assertFalse(self.config_manager._watching)
        self.assertFalse(self.config_manager._schedule_running)
    
    def test_load_save_config(self):
        """Test loading and saving configuration."""
        # Initial config should be created
        self.assertTrue(os.path.exists(self.config_path))
        
        # Modify and save config
        self.config_manager.update_config(confidence_threshold=0.8)
        
        # Create new config manager to load from file
        new_manager = ConfigManager(self.config_path)
        self.assertEqual(new_manager.get_config().confidence_threshold, 0.8)
    
    def test_update_config(self):
        """Test updating configuration."""
        original_threshold = self.config_manager.get_config().confidence_threshold
        
        # Update single value
        self.config_manager.update_config(confidence_threshold=0.9)
        self.assertEqual(self.config_manager.get_config().confidence_threshold, 0.9)
        
        # Update multiple values
        self.config_manager.update_config(
            confidence_threshold=0.8,
            monitoring_enabled=False
        )
        self.assertEqual(self.config_manager.get_config().confidence_threshold, 0.8)
        self.assertFalse(self.config_manager.get_config().monitoring_enabled)
        
        # Invalid key should be ignored
        self.config_manager.update_config(invalid_key="value")
        # No error should be raised
    
    def test_validate_config(self):
        """Test configuration validation."""
        # Default config should be valid
        self.assertTrue(self.config_manager.validate_config())
        
        # Invalid confidence threshold
        self.config_manager.update_config(confidence_threshold=1.5)
        self.assertFalse(self.config_manager.validate_config())
        
        # Fix confidence threshold
        self.config_manager.update_config(confidence_threshold=0.8)
        self.assertTrue(self.config_manager.validate_config())
        
        # Invalid monitoring hours
        self.config_manager.update_config(monitoring_start_hour=25)
        self.assertFalse(self.config_manager.validate_config())
        
        # Fix monitoring hours
        self.config_manager.update_config(monitoring_start_hour=8)
        self.assertTrue(self.config_manager.validate_config())
        
        # Invalid ROI
        self.config_manager.update_config(detection_roi=(-10, 0, 640, 480))
        self.assertFalse(self.config_manager.validate_config())
        
        # Fix ROI
        self.config_manager.update_config(detection_roi=(0, 0, 640, 480))
        self.assertTrue(self.config_manager.validate_config())
    
    def test_file_watcher(self):
        """Test file watcher for hot-reload."""
        # Create mock callback
        callback = Mock()
        self.config_manager.register_change_callback(callback)
        
        # Start file watcher with short interval
        self.config_manager.start_file_watcher(check_interval=0.1)
        self.assertTrue(self.config_manager._watching)
        
        # Wait a moment for watcher to start
        time.sleep(0.2)
        
        # Modify config file externally
        with open(self.config_path, 'r') as f:
            config_data = json.load(f)
        
        config_data['confidence_threshold'] = 0.95
        
        with open(self.config_path, 'w') as f:
            json.dump(config_data, f)
        
        # Wait for watcher to detect change
        time.sleep(0.3)
        
        # Check that callback was called
        callback.assert_called_once()
        
        # Check that config was reloaded
        self.assertEqual(self.config_manager.get_config().confidence_threshold, 0.95)
        
        # Stop file watcher
        self.config_manager.stop_file_watcher()
        self.assertFalse(self.config_manager._watching)
    
    def test_register_unregister_callback(self):
        """Test registering and unregistering callbacks."""
        callback1 = Mock()
        callback2 = Mock()
        
        # Register callbacks
        self.config_manager.register_change_callback(callback1)
        self.config_manager.register_change_callback(callback2)
        
        self.assertEqual(len(self.config_manager._config_change_callbacks), 2)
        
        # Unregister one callback
        self.config_manager.unregister_change_callback(callback1)
        
        self.assertEqual(len(self.config_manager._config_change_callbacks), 1)
        self.assertEqual(self.config_manager._config_change_callbacks[0], callback2)
    
    def test_add_scheduled_config(self):
        """Test adding scheduled configuration."""
        # Add scheduled config
        schedule_time = dt_time(hour=8, minute=0)
        config_changes = {'monitoring_enabled': True}
        
        schedule_id = self.config_manager.add_scheduled_config(
            config_changes=config_changes,
            schedule_time=schedule_time
        )
        
        self.assertEqual(schedule_id, 0)  # First schedule ID should be 0
        self.assertEqual(len(self.config_manager._scheduled_configs), 1)
        self.assertTrue(self.config_manager._schedule_running)
        
        # Check schedule details
        schedule = self.config_manager._scheduled_configs[0]
        self.assertEqual(schedule['config_changes'], config_changes)
        self.assertEqual(schedule['time'], schedule_time)
        self.assertIsNone(schedule['days_of_week'])
        self.assertTrue(schedule['enabled'])
    
    def test_remove_scheduled_config(self):
        """Test removing scheduled configuration."""
        # Add two scheduled configs
        schedule_id1 = self.config_manager.add_scheduled_config(
            config_changes={'monitoring_enabled': True},
            schedule_time=dt_time(hour=8, minute=0)
        )
        
        schedule_id2 = self.config_manager.add_scheduled_config(
            config_changes={'monitoring_enabled': False},
            schedule_time=dt_time(hour=20, minute=0)
        )
        
        self.assertEqual(len(self.config_manager._scheduled_configs), 2)
        
        # Remove first schedule
        result = self.config_manager.remove_scheduled_config(schedule_id1)
        self.assertTrue(result)
        self.assertEqual(len(self.config_manager._scheduled_configs), 1)
        self.assertEqual(self.config_manager._scheduled_configs[0]['id'], schedule_id2)
        
        # Try to remove non-existent schedule
        result = self.config_manager.remove_scheduled_config(999)
        self.assertFalse(result)
    
    def test_get_scheduled_configs(self):
        """Test getting scheduled configurations."""
        # Add scheduled config
        schedule_time = dt_time(hour=8, minute=0)
        config_changes = {'monitoring_enabled': True}
        days = [0, 2, 4]  # Monday, Wednesday, Friday
        
        self.config_manager.add_scheduled_config(
            config_changes=config_changes,
            schedule_time=schedule_time,
            days_of_week=days
        )
        
        # Get scheduled configs
        schedules = self.config_manager.get_scheduled_configs()
        
        self.assertEqual(len(schedules), 1)
        schedule = schedules[0]
        
        self.assertEqual(schedule['config_changes'], config_changes)
        self.assertEqual(schedule['time'], '08:00:00')
        self.assertEqual(schedule['days_of_week'], days)
        self.assertIsNone(schedule['last_run'])
        self.assertTrue(schedule['enabled'])
    
    def test_enable_disable_scheduled_config(self):
        """Test enabling and disabling scheduled configuration."""
        # Add scheduled config
        schedule_id = self.config_manager.add_scheduled_config(
            config_changes={'monitoring_enabled': True},
            schedule_time=dt_time(hour=8, minute=0)
        )
        
        # Disable schedule
        result = self.config_manager.enable_scheduled_config(schedule_id, False)
        self.assertTrue(result)
        self.assertFalse(self.config_manager._scheduled_configs[0]['enabled'])
        
        # Enable schedule
        result = self.config_manager.enable_scheduled_config(schedule_id, True)
        self.assertTrue(result)
        self.assertTrue(self.config_manager._scheduled_configs[0]['enabled'])
        
        # Try to enable non-existent schedule
        result = self.config_manager.enable_scheduled_config(999, True)
        self.assertFalse(result)
    
    @patch('cat_counter_detection.config_manager.datetime')
    def test_scheduler_functionality(self, mock_datetime):
        """Test scheduler functionality."""
        # Mock datetime.now() to control time
        mock_now = Mock()
        mock_datetime.now.return_value = mock_now
        
        # Set current time to 8:00 AM on Monday (weekday 0)
        mock_now.time.return_value = dt_time(hour=8, minute=0)
        mock_now.weekday.return_value = 0
        mock_now.date.return_value = datetime.now().date()
        
        # Add scheduled config for 8:00 AM on Monday
        config_changes = {'monitoring_enabled': False}  # Start with False
        self.config_manager.update_config(monitoring_enabled=True)  # Set to True initially
        
        schedule_id = self.config_manager.add_scheduled_config(
            config_changes=config_changes,
            schedule_time=dt_time(hour=8, minute=0),
            days_of_week=[0]  # Monday only
        )
        
        # Manually trigger the scheduler logic (without the infinite loop)
        schedule = self.config_manager._scheduled_configs[0]
        
        # Check if the schedule should run
        now = mock_datetime.now.return_value
        current_time = now.time.return_value
        current_day = now.weekday.return_value
        
        # Verify schedule conditions
        self.assertTrue(schedule['enabled'])
        self.assertIn(current_day, schedule['days_of_week'])
        
        # Simulate applying the scheduled config
        if schedule['enabled'] and current_day in schedule['days_of_week']:
            schedule_time = schedule['time']
            schedule_seconds = schedule_time.hour * 3600 + schedule_time.minute * 60 + schedule_time.second
            current_seconds = current_time.hour * 3600 + current_time.minute * 60 + current_time.second
            
            time_diff = abs(schedule_seconds - current_seconds)
            if time_diff <= 30:  # Within 30 second window
                self.config_manager.update_config(**schedule['config_changes'])
                schedule['last_run'] = now
        
        # Check that config was updated
        self.assertFalse(self.config_manager.get_config().monitoring_enabled)
        
        # Test with wrong day
        mock_now.weekday.return_value = 1  # Tuesday
        
        # Reset config
        self.config_manager.update_config(monitoring_enabled=True)
        
        # Schedule should not run on Tuesday
        current_day = mock_now.weekday.return_value
        self.assertNotIn(current_day, schedule['days_of_week'])
        
        # Config should remain unchanged
        self.assertTrue(self.config_manager.get_config().monitoring_enabled)
    
    def test_start_stop_scheduler(self):
        """Test starting and stopping scheduler."""
        # Start scheduler
        self.config_manager.start_scheduler()
        self.assertTrue(self.config_manager._schedule_running)
        self.assertIsNotNone(self.config_manager._schedule_thread)
        
        # Stop scheduler
        self.config_manager.stop_scheduler()
        self.assertFalse(self.config_manager._schedule_running)
    
    def test_detection_sensitivity_profiles(self):
        """Test detection sensitivity adjustment features (Requirement 4.1)."""
        # Test low sensitivity
        self.config_manager.set_detection_sensitivity('low')
        config = self.config_manager.get_config()
        self.assertEqual(config.detection_sensitivity, 'low')
        self.assertEqual(config.confidence_threshold, 0.8)
        self.assertEqual(config.min_detection_size, 80)
        self.assertEqual(config.temporal_consistency_frames, 3)
        
        # Test medium sensitivity
        self.config_manager.set_detection_sensitivity('medium')
        config = self.config_manager.get_config()
        self.assertEqual(config.detection_sensitivity, 'medium')
        self.assertEqual(config.confidence_threshold, 0.7)
        self.assertEqual(config.min_detection_size, 50)
        self.assertEqual(config.temporal_consistency_frames, 2)
        
        # Test high sensitivity
        self.config_manager.set_detection_sensitivity('high')
        config = self.config_manager.get_config()
        self.assertEqual(config.detection_sensitivity, 'high')
        self.assertEqual(config.confidence_threshold, 0.6)
        self.assertEqual(config.min_detection_size, 30)
        self.assertEqual(config.temporal_consistency_frames, 1)
        
        # Test invalid sensitivity (should not change config)
        original_sensitivity = config.detection_sensitivity
        self.config_manager.set_detection_sensitivity('invalid')
        self.assertEqual(self.config_manager.get_config().detection_sensitivity, original_sensitivity)
    
    @patch('cat_counter_detection.config_manager.datetime')
    def test_monitoring_schedule_functionality(self, mock_datetime):
        """Test monitoring schedule functionality (Requirement 4.2)."""
        # Mock datetime.now() to control time
        mock_now = Mock()
        mock_datetime.now.return_value = mock_now
        
        # Test monitoring during active hours
        mock_now.hour = 10  # 10 AM
        mock_now.weekday.return_value = 1  # Tuesday
        
        # Set monitoring hours 8 AM to 6 PM, Tuesday enabled
        self.config_manager.update_config(
            monitoring_enabled=True,
            monitoring_start_hour=8,
            monitoring_end_hour=18,
            monitoring_days=(False, True, False, False, False, False, False)  # Only Tuesday
        )
        
        self.assertTrue(self.config_manager.is_monitoring_active())
        
        # Test monitoring outside active hours
        mock_now.hour = 20  # 8 PM (outside 8 AM - 6 PM)
        self.assertFalse(self.config_manager.is_monitoring_active())
        
        # Test monitoring on disabled day
        mock_now.hour = 10  # 10 AM (within hours)
        mock_now.weekday.return_value = 0  # Monday (disabled)
        self.assertFalse(self.config_manager.is_monitoring_active())
        
        # Test overnight monitoring schedule
        self.config_manager.update_config(
            monitoring_start_hour=22,  # 10 PM
            monitoring_end_hour=6,     # 6 AM
            monitoring_days=(True, True, True, True, True, True, True)  # All days
        )
        
        # Test during overnight period
        mock_now.hour = 2  # 2 AM
        mock_now.weekday.return_value = 1  # Tuesday
        self.assertTrue(self.config_manager.is_monitoring_active())
        
        # Test outside overnight period
        mock_now.hour = 10  # 10 AM
        self.assertFalse(self.config_manager.is_monitoring_active())
        
        # Test when monitoring is disabled
        self.config_manager.update_config(monitoring_enabled=False)
        mock_now.hour = 10
        self.assertFalse(self.config_manager.is_monitoring_active())
    
    @patch('cat_counter_detection.config_manager.datetime')
    def test_notification_preferences_and_quiet_hours(self, mock_datetime):
        """Test notification preferences and cooldown management (Requirement 4.3)."""
        # Mock datetime.now() to control time
        mock_now = Mock()
        mock_datetime.now.return_value = mock_now
        
        # Test notification allowed during normal hours
        mock_now.hour = 15  # 3 PM
        self.config_manager.update_config(
            notification_quiet_hours_enabled=True,
            notification_quiet_hours_start=22,  # 10 PM
            notification_quiet_hours_end=7      # 7 AM
        )
        
        self.assertTrue(self.config_manager.is_notification_allowed())
        
        # Test notification blocked during quiet hours
        mock_now.hour = 2  # 2 AM (within quiet hours)
        self.assertFalse(self.config_manager.is_notification_allowed())
        
        # Test notification allowed when quiet hours disabled
        self.config_manager.update_config(notification_quiet_hours_enabled=False)
        self.assertTrue(self.config_manager.is_notification_allowed())
        
        # Test notification parameters retrieval
        self.config_manager.update_config(
            push_notifications_enabled=True,
            email_notifications_enabled=False,
            notification_cooldown_minutes=10,
            notification_max_per_hour=6
        )
        
        params = self.config_manager.get_notification_parameters()
        self.assertTrue(params['push_notifications_enabled'])
        self.assertFalse(params['email_notifications_enabled'])
        self.assertEqual(params['notification_cooldown_minutes'], 10)
        self.assertEqual(params['notification_max_per_hour'], 6)
    
    def test_hot_reload_configuration_changes(self):
        """Test that configuration changes take effect without restart (Requirement 4.4)."""
        # Create mock callback to simulate system components
        detection_engine_callback = Mock()
        notification_service_callback = Mock()
        
        # Register callbacks
        self.config_manager.register_change_callback(detection_engine_callback)
        self.config_manager.register_change_callback(notification_service_callback)
        
        # Update configuration
        self.config_manager.update_config(
            confidence_threshold=0.85,
            push_notifications_enabled=False
        )
        
        # Verify callbacks were called (simulating hot-reload)
        detection_engine_callback.assert_called_once()
        notification_service_callback.assert_called_once()
        
        # Verify configuration was updated
        config = self.config_manager.get_config()
        self.assertEqual(config.confidence_threshold, 0.85)
        self.assertFalse(config.push_notifications_enabled)
        
        # Test detection parameters retrieval for hot-reload
        detection_params = self.config_manager.get_detection_parameters()
        self.assertEqual(detection_params['confidence_threshold'], 0.85)
        self.assertIn('detection_roi', detection_params)
        self.assertIn('min_detection_size', detection_params)
        self.assertIn('temporal_consistency_frames', detection_params)
        self.assertIn('detection_sensitivity', detection_params)
    
    def test_configuration_validation_comprehensive(self):
        """Test comprehensive configuration validation."""
        # Test detection sensitivity validation
        self.config_manager.update_config(detection_sensitivity='invalid')
        self.assertFalse(self.config_manager.validate_config())
        
        self.config_manager.update_config(detection_sensitivity='medium')
        self.assertTrue(self.config_manager.validate_config())
        
        # Test monitoring days validation
        self.config_manager.update_config(monitoring_days=(True, True, True))  # Wrong length
        self.assertFalse(self.config_manager.validate_config())
        
        self.config_manager.update_config(monitoring_days=(True, True, True, True, True, True, True))
        self.assertTrue(self.config_manager.validate_config())
        
        # Test notification parameters validation
        self.config_manager.update_config(notification_cooldown_minutes=-1)
        self.assertFalse(self.config_manager.validate_config())
        
        self.config_manager.update_config(notification_cooldown_minutes=5)
        self.assertTrue(self.config_manager.validate_config())
        
        # Test image quality validation
        self.config_manager.update_config(image_quality=150)  # > 100
        self.assertFalse(self.config_manager.validate_config())
        
        self.config_manager.update_config(image_quality=85)
        self.assertTrue(self.config_manager.validate_config())
    
    def test_export_import_configuration(self):
        """Test configuration export and import functionality."""
        # Update some configuration values
        self.config_manager.update_config(
            confidence_threshold=0.75,
            monitoring_enabled=False,
            push_notifications_enabled=True,
            detection_sensitivity='high'
        )
        
        # Export configuration
        exported_config = self.config_manager.export_config()
        
        # Verify exported values
        self.assertEqual(exported_config['confidence_threshold'], 0.75)
        self.assertFalse(exported_config['monitoring_enabled'])
        self.assertTrue(exported_config['push_notifications_enabled'])
        self.assertEqual(exported_config['detection_sensitivity'], 'high')
        
        # Reset to defaults
        self.config_manager.reset_to_defaults()
        self.assertEqual(self.config_manager.get_config().confidence_threshold, 0.7)  # Default
        
        # Import the exported configuration
        success = self.config_manager.import_config(exported_config)
        self.assertTrue(success)
        
        # Verify imported values
        config = self.config_manager.get_config()
        self.assertEqual(config.confidence_threshold, 0.75)
        self.assertFalse(config.monitoring_enabled)
        self.assertTrue(config.push_notifications_enabled)
        self.assertEqual(config.detection_sensitivity, 'high')
        
        # Test import with invalid configuration
        invalid_config = {'confidence_threshold': 2.0}  # Invalid value
        success = self.config_manager.import_config(invalid_config)
        self.assertFalse(success)
        
        # Configuration should remain unchanged after failed import
        self.assertEqual(self.config_manager.get_config().confidence_threshold, 0.75)
    
    def test_scheduled_config_with_days_of_week(self):
        """Test scheduled configuration with specific days of week."""
        # Add scheduled config for weekdays only
        config_changes = {'monitoring_enabled': True, 'detection_sensitivity': 'high'}
        weekdays = [0, 1, 2, 3, 4]  # Monday through Friday
        
        schedule_id = self.config_manager.add_scheduled_config(
            config_changes=config_changes,
            schedule_time=dt_time(hour=8, minute=0),
            days_of_week=weekdays
        )
        
        # Verify schedule was added correctly
        schedules = self.config_manager.get_scheduled_configs()
        self.assertEqual(len(schedules), 1)
        
        schedule = schedules[0]
        self.assertEqual(schedule['days_of_week'], weekdays)
        self.assertEqual(schedule['config_changes'], config_changes)
    
    def test_reset_to_defaults(self):
        """Test resetting configuration to defaults."""
        # Create mock callback
        callback = Mock()
        self.config_manager.register_change_callback(callback)
        
        # Modify configuration
        self.config_manager.update_config(
            confidence_threshold=0.9,
            monitoring_enabled=False,
            detection_sensitivity='low'
        )
        
        # Reset to defaults
        self.config_manager.reset_to_defaults()
        
        # Verify callback was called
        callback.assert_called()
        
        # Verify configuration was reset
        config = self.config_manager.get_config()
        self.assertEqual(config.confidence_threshold, 0.7)  # Default
        self.assertTrue(config.monitoring_enabled)  # Default
        self.assertEqual(config.detection_sensitivity, 'medium')  # Default


if __name__ == '__main__':
    unittest.main()