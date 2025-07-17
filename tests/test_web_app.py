"""Unit tests for web application."""

import unittest
import json
import tempfile
import shutil
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock Flask if not available
try:
    from flask import Flask
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

if FLASK_AVAILABLE:
    from cat_counter_detection.web.app import CatCounterWebApp, create_app
    from cat_counter_detection.detection_pipeline import DetectionPipeline
    from cat_counter_detection.config_manager import ConfigManager


@unittest.skipIf(not FLASK_AVAILABLE, "Flask not available")
class TestCatCounterWebApp(unittest.TestCase):
    """Test cases for CatCounterWebApp."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        
        # Create test configuration
        config_path = os.path.join(self.test_dir, "test_config.json")
        config_manager = ConfigManager(config_path)
        
        # Create mock pipeline
        self.mock_pipeline = Mock(spec=DetectionPipeline)
        self.mock_pipeline.config_manager = config_manager
        self.mock_pipeline.config = config_manager.get_config()
        
        # Initialize web app
        self.web_app = CatCounterWebApp(self.mock_pipeline)
        self.client = self.web_app.app.test_client()
        self.web_app.app.config['TESTING'] = True
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_web_app_initialization(self):
        """Test web application initialization."""
        self.assertIsNotNone(self.web_app.app)
        self.assertIsNotNone(self.web_app.pipeline)
        self.assertEqual(self.web_app.pipeline, self.mock_pipeline)
    
    def test_index_route(self):
        """Test main index route."""
        with patch('cat_counter_detection.web.app.render_template') as mock_render:
            mock_render.return_value = "Index Page"
            response = self.client.get('/')
            self.assertEqual(response.status_code, 200)
            mock_render.assert_called_once_with('index.html')
    
    def test_live_feed_route(self):
        """Test live feed route."""
        with patch('cat_counter_detection.web.app.render_template') as mock_render:
            mock_render.return_value = "Live Feed Page"
            response = self.client.get('/live')
            self.assertEqual(response.status_code, 200)
            mock_render.assert_called_once_with('live.html')
    
    def test_history_route(self):
        """Test history route."""
        with patch('cat_counter_detection.web.app.render_template') as mock_render:
            mock_render.return_value = "History Page"
            response = self.client.get('/history')
            self.assertEqual(response.status_code, 200)
            mock_render.assert_called_once_with('history.html')
    
    def test_config_route(self):
        """Test configuration route."""
        with patch('cat_counter_detection.web.app.render_template') as mock_render:
            mock_render.return_value = "Config Page"
            response = self.client.get('/config')
            self.assertEqual(response.status_code, 200)
            mock_render.assert_called_once_with('config.html')
    
    def test_api_status(self):
        """Test API status endpoint."""
        # Mock pipeline status
        mock_status = {
            'running': True,
            'detection_count': 5,
            'error_count': 0
        }
        self.mock_pipeline.get_status.return_value = mock_status
        
        response = self.client.get('/api/status')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['data'], mock_status)
    
    def test_api_status_error(self):
        """Test API status endpoint with error."""
        self.mock_pipeline.get_status.side_effect = Exception("Test error")
        
        response = self.client.get('/api/status')
        self.assertEqual(response.status_code, 500)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('error', data)
    
    def test_api_start_pipeline(self):
        """Test API start pipeline endpoint."""
        self.mock_pipeline.start.return_value = True
        
        response = self.client.post('/api/start')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.mock_pipeline.start.assert_called_once()
    
    def test_api_stop_pipeline(self):
        """Test API stop pipeline endpoint."""
        response = self.client.post('/api/stop')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.mock_pipeline.stop.assert_called_once()
    
    def test_api_get_config(self):
        """Test API get configuration endpoint."""
        response = self.client.get('/api/config')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        
        # Check that configuration fields are present
        config_data = data['data']
        self.assertIn('confidence_threshold', config_data)
        self.assertIn('detection_roi', config_data)
        self.assertIn('monitoring_enabled', config_data)
    
    def test_api_update_config(self):
        """Test API update configuration endpoint."""
        update_data = {
            'confidence_threshold': 0.8,
            'monitoring_enabled': False
        }
        
        response = self.client.post('/api/config',
                                  data=json.dumps(update_data),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.mock_pipeline.update_configuration.assert_called_once_with(**update_data)
    
    def test_api_update_config_no_data(self):
        """Test API update configuration with no data."""
        response = self.client.post('/api/config')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
    
    def test_api_detections(self):
        """Test API detections endpoint."""
        # Mock detection data
        mock_detections = [
            Mock(
                timestamp=Mock(isoformat=Mock(return_value='2023-01-01T12:00:00')),
                cat_count=1,
                confidence_score=0.85,
                image_path='/test/image1.jpg',
                bounding_boxes=[
                    Mock(x=100, y=100, width=50, height=50, confidence=0.8)
                ]
            )
        ]
        self.mock_pipeline.get_recent_detections.return_value = mock_detections
        
        response = self.client.get('/api/detections')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']), 1)
        
        detection_data = data['data'][0]
        self.assertEqual(detection_data['cat_count'], 1)
        self.assertEqual(detection_data['confidence_score'], 0.85)
    
    def test_api_detections_with_params(self):
        """Test API detections endpoint with query parameters."""
        self.mock_pipeline.get_recent_detections.return_value = []
        
        response = self.client.get('/api/detections?limit=20&days=14')
        self.assertEqual(response.status_code, 200)
        
        # Check that the limit parameter was passed
        self.mock_pipeline.get_recent_detections.assert_called_once_with(20)
    
    def test_api_test_detection(self):
        """Test API test detection endpoint."""
        self.mock_pipeline.trigger_test_detection.return_value = True
        
        response = self.client.post('/api/test-detection')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.mock_pipeline.trigger_test_detection.assert_called_once()
    
    def test_api_cleanup(self):
        """Test API cleanup endpoint."""
        response = self.client.post('/api/cleanup')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.mock_pipeline.cleanup_old_data.assert_called_once()
    
    def test_api_storage_stats(self):
        """Test API storage statistics endpoint."""
        # Mock storage stats
        mock_stats = Mock(
            total_space_mb=1000.0,
            used_space_mb=100.0,
            available_space_mb=900.0,
            detection_count=10,
            oldest_detection='2023-01-01',
            newest_detection='2023-01-02'
        )
        self.mock_pipeline.storage_service.get_storage_usage.return_value = mock_stats
        
        response = self.client.get('/api/storage-stats')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['total_space_mb'], 1000.0)
        self.assertEqual(data['data']['detection_count'], 10)
    
    def test_api_test_notifications(self):
        """Test API test notifications endpoint."""
        mock_results = {'push': True, 'email': False}
        self.mock_pipeline.notification_service.send_test_notifications.return_value = mock_results
        
        response = self.client.post('/api/test-notifications')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['data'], mock_results)
    
    def test_create_placeholder_frame(self):
        """Test placeholder frame creation."""
        placeholder = self.web_app._create_placeholder_frame()
        self.assertIsInstance(placeholder, bytes)
        self.assertGreater(len(placeholder), 0)
    
    def test_frame_to_jpeg_with_none(self):
        """Test frame to JPEG conversion with None frame."""
        result = self.web_app._frame_to_jpeg(None)
        self.assertIsInstance(result, bytes)
        # Should return placeholder frame
        self.assertGreater(len(result), 0)
    
    def test_create_app_factory(self):
        """Test app factory function."""
        app = create_app(self.mock_pipeline)
        self.assertIsNotNone(app)
        self.assertEqual(app.config['SECRET_KEY'], 'cat-counter-secret-key-change-in-production')
    
    def test_get_app_method(self):
        """Test get_app method."""
        app = self.web_app.get_app()
        self.assertEqual(app, self.web_app.app)
    
    @patch('cat_counter_detection.web.app.os.path.exists')
    @patch('cat_counter_detection.web.app.send_file')
    def test_api_image_success(self, mock_send_file, mock_exists):
        """Test API image endpoint success."""
        mock_exists.return_value = True
        mock_send_file.return_value = "image_data"
        
        # Mock storage service
        self.mock_pipeline.storage_service.images_dir = "/test/images"
        
        response = self.client.get('/api/image/test.jpg')
        # The actual response depends on send_file mock
        mock_send_file.assert_called_once()
    
    def test_api_image_not_found(self):
        """Test API image endpoint with non-existent file."""
        # Mock storage service
        self.mock_pipeline.storage_service.images_dir = "/test/images"
        
        with patch('cat_counter_detection.web.app.os.path.exists') as mock_exists:
            mock_exists.return_value = False
            
            response = self.client.get('/api/image/nonexistent.jpg')
            self.assertEqual(response.status_code, 404)
            
            data = json.loads(response.data)
            self.assertFalse(data['success'])


@unittest.skipIf(FLASK_AVAILABLE, "Flask is available")
class TestWebAppWithoutFlask(unittest.TestCase):
    """Test web app behavior when Flask is not available."""
    
    def test_import_error_without_flask(self):
        """Test that ImportError is raised when Flask is not available."""
        # This test only runs when Flask is not available
        with self.assertRaises(ImportError):
            from cat_counter_detection.web.app import CatCounterWebApp
            CatCounterWebApp()


if __name__ == '__main__':
    unittest.main()