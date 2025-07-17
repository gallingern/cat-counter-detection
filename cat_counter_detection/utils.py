"""Utility functions for the cat detection system."""

import os
import logging
from typing import Tuple, Optional
from datetime import datetime


def ensure_directory_exists(path: str) -> None:
    """Ensure a directory exists, create if it doesn't."""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """Set up logging configuration."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    if log_file:
        ensure_directory_exists(os.path.dirname(log_file))
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format=log_format,
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    else:
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format=log_format
        )


def is_point_in_roi(point: Tuple[int, int], roi: Tuple[int, int, int, int]) -> bool:
    """Check if a point is within a region of interest."""
    x, y = point
    roi_x, roi_y, roi_width, roi_height = roi
    
    return (roi_x <= x <= roi_x + roi_width and 
            roi_y <= y <= roi_y + roi_height)


def calculate_iou(box1: Tuple[int, int, int, int], box2: Tuple[int, int, int, int]) -> float:
    """Calculate Intersection over Union (IoU) of two bounding boxes."""
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2
    
    # Calculate intersection
    x_left = max(x1, x2)
    y_top = max(y1, y2)
    x_right = min(x1 + w1, x2 + w2)
    y_bottom = min(y1 + h1, y2 + h2)
    
    if x_right < x_left or y_bottom < y_top:
        return 0.0
    
    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    
    # Calculate union
    box1_area = w1 * h1
    box2_area = w2 * h2
    union_area = box1_area + box2_area - intersection_area
    
    return intersection_area / union_area if union_area > 0 else 0.0


def format_timestamp(dt: datetime) -> str:
    """Format datetime for consistent display."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def get_file_size_mb(file_path: str) -> float:
    """Get file size in megabytes."""
    if os.path.exists(file_path):
        return os.path.getsize(file_path) / (1024 * 1024)
    return 0.0


def cleanup_old_files(directory: str, max_age_days: int) -> int:
    """Clean up files older than max_age_days and return count of deleted files."""
    if not os.path.exists(directory):
        return 0
    
    current_time = datetime.now()
    deleted_count = 0
    
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            age_days = (current_time - file_time).days
            
            if age_days > max_age_days:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except OSError:
                    pass  # Skip files that can't be deleted
    
    return deleted_count