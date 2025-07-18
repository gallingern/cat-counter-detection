#!/usr/bin/env python3
"""Script to fix the frame_capture.py file."""

import os

# Path to the frame_capture.py file
file_path = "cat_counter_detection/services/frame_capture.py"

# Read the file content
with open(file_path, "r") as f:
    content = f.read()

# Replace all occurrences of the problematic decorator
content = content.replace(
    "@retry_on_error(max_attempts=3, delay=1.0, exceptions=(Exception,))",
    "@retry_on_error(max_retries=3, delay_seconds=1.0, component_name=\"frame_capture\")"
)

# Write the updated content back to the file
with open(file_path, "w") as f:
    f.write(content)

print(f"Fixed {file_path}")