#!/usr/bin/env python3
"""
Simple camera debug script to test camera functionality locally.
"""

import cv2
import time
import sys
import os

def test_opencv_camera():
    """Test OpenCV camera access."""
    print("=== Testing OpenCV Camera ===")
    
    for device in [0, 1, 2, 3]:
        print(f"\nTrying device {device}...")
        cap = cv2.VideoCapture(device)
        
        if cap.isOpened():
            print(f"✅ Device {device} opened successfully")
            
            # Set some properties
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 160)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 120)
            cap.set(cv2.CAP_PROP_FPS, 0.5)
            
            # Try to read a frame
            ret, frame = cap.read()
            if ret:
                print(f"✅ Frame captured! Shape: {frame.shape}")
                filename = f"debug_device_{device}.jpg"
                cv2.imwrite(filename, frame)
                print(f"✅ Saved {filename}")
                cap.release()
                return True
            else:
                print(f"❌ Could not read frame from device {device}")
                cap.release()
        else:
            print(f"❌ Could not open device {device}")
    
    return False

def test_libcamera():
    """Test libcamera functionality."""
    print("\n=== Testing libcamera ===")
    
    try:
        import subprocess
        result = subprocess.run(['libcamera-vid', '--list-cameras'], 
                              capture_output=True, timeout=10)
        print(f"libcamera-vid exit code: {result.returncode}")
        print(f"stdout: {result.stdout.decode()}")
        print(f"stderr: {result.stderr.decode()}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ libcamera-vid timed out")
        return False
    except FileNotFoundError:
        print("❌ libcamera-vid not found")
        return False
    except Exception as e:
        print(f"❌ libcamera error: {e}")
        return False

def test_camera_module():
    """Test the camera module directly."""
    print("\n=== Testing Camera Module ===")
    
    try:
        from camera import Camera
        import config
        
        print("Creating camera instance...")
        camera = Camera()
        
        print("Starting camera...")
        camera.start()
        
        print("Waiting for frames...")
        for i in range(10):
            frame = camera.get_frame()
            if frame is not None:
                print(f"✅ Frame received! Shape: {frame.shape}")
                cv2.imwrite(f"debug_camera_module_{i}.jpg", frame)
                break
            time.sleep(1)
            print(f"Attempt {i+1}/10: No frame yet...")
        else:
            print("❌ No frames received after 10 attempts")
        
        print("Stopping camera...")
        camera.stop()
        
    except Exception as e:
        print(f"❌ Camera module error: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main debug function."""
    print("Camera Debug Script")
    print("=" * 50)
    
    # Test OpenCV
    opencv_works = test_opencv_camera()
    
    # Test libcamera
    libcamera_works = test_libcamera()
    
    # Test camera module
    test_camera_module()
    
    print("\n" + "=" * 50)
    print("SUMMARY:")
    print(f"OpenCV camera: {'✅ Working' if opencv_works else '❌ Failed'}")
    print(f"libcamera: {'✅ Working' if libcamera_works else '❌ Failed'}")
    
    if opencv_works:
        print("\n🎉 OpenCV camera is working! This should be sufficient for the system.")
    else:
        print("\n⚠️  OpenCV camera failed. This needs to be fixed.")

if __name__ == "__main__":
    main() 