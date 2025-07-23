#!/usr/bin/env python3
"""
DMA Heap Diagnostic Script
"""

import os
import subprocess
import sys

def check_dma_heap_devices():
    """Check DMA heap devices."""
    print("=== Checking DMA Heap Devices ===")
    
    dma_devices = []
    for i in range(10):
        device = f"/dev/dma_heap{i}"
        if os.path.exists(device):
            dma_devices.append(device)
    
    if dma_devices:
        print(f"✅ Found {len(dma_devices)} DMA heap devices:")
        for device in dma_devices:
            stat = os.stat(device)
            print(f"  {device}: mode={oct(stat.st_mode)[-3:]}, owner={stat.st_uid}, group={stat.st_gid}")
    else:
        print("❌ No DMA heap devices found")
    
    return len(dma_devices) > 0

def check_dma_heap_module():
    """Check DMA heap kernel module."""
    print("\n=== Checking DMA Heap Module ===")
    
    try:
        result = subprocess.run(['lsmod'], capture_output=True, text=True)
        if 'dma_heap' in result.stdout:
            print("✅ DMA heap module is loaded")
            return True
        else:
            print("❌ DMA heap module not loaded")
            return False
    except Exception as e:
        print(f"❌ Error checking modules: {e}")
        return False

def check_device_tree():
    """Check device tree for DMA heap."""
    print("\n=== Checking Device Tree ===")
    
    try:
        result = subprocess.run(['vcgencmd', 'get_config', 'str'], capture_output=True, text=True)
        if 'dma_heap' in result.stdout:
            print("✅ DMA heap overlay in config")
            return True
        else:
            print("❌ DMA heap overlay not in config")
            return False
    except Exception as e:
        print(f"❌ Error checking config: {e}")
        return False

def check_user_permissions():
    """Check user permissions."""
    print("\n=== Checking User Permissions ===")
    
    try:
        result = subprocess.run(['groups'], capture_output=True, text=True)
        groups = result.stdout.strip().split()
        
        if 'video' in groups:
            print("✅ User is in video group")
        else:
            print("❌ User not in video group")
        
        if 'gpio' in groups:
            print("✅ User is in gpio group")
        else:
            print("❌ User not in gpio group")
        
        return 'video' in groups
    except Exception as e:
        print(f"❌ Error checking groups: {e}")
        return False

def test_dma_heap_access():
    """Test DMA heap access."""
    print("\n=== Testing DMA Heap Access ===")
    
    for i in range(5):
        device = f"/dev/dma_heap{i}"
        if os.path.exists(device):
            try:
                with open(device, 'rb') as f:
                    print(f"✅ Can open {device}")
                return True
            except PermissionError:
                print(f"❌ Permission denied for {device}")
            except Exception as e:
                print(f"❌ Error accessing {device}: {e}")
    
    print("❌ Cannot access any DMA heap devices")
    return False

def check_kernel_messages():
    """Check kernel messages for DMA heap issues."""
    print("\n=== Checking Kernel Messages ===")
    
    try:
        result = subprocess.run(['dmesg'], capture_output=True, text=True)
        dma_messages = [line for line in result.stdout.split('\n') if 'dma' in line.lower()]
        
        if dma_messages:
            print("DMA-related kernel messages:")
            for msg in dma_messages[-5:]:  # Last 5 messages
                print(f"  {msg}")
        else:
            print("No DMA-related kernel messages found")
        
        return len(dma_messages) > 0
    except Exception as e:
        print(f"❌ Error checking kernel messages: {e}")
        return False

def main():
    """Main diagnostic function."""
    print("DMA Heap Diagnostic")
    print("=" * 50)
    
    devices_exist = check_dma_heap_devices()
    module_loaded = check_dma_heap_module()
    in_config = check_device_tree()
    user_perms = check_user_permissions()
    can_access = test_dma_heap_access()
    kernel_msgs = check_kernel_messages()
    
    print("\n" + "=" * 50)
    print("SUMMARY:")
    print(f"DMA heap devices: {'✅ Present' if devices_exist else '❌ Missing'}")
    print(f"DMA heap module: {'✅ Loaded' if module_loaded else '❌ Not loaded'}")
    print(f"In config: {'✅ Yes' if in_config else '❌ No'}")
    print(f"User permissions: {'✅ OK' if user_perms else '❌ Issues'}")
    print(f"Can access: {'✅ Yes' if can_access else '❌ No'}")
    
    print("\nRECOMMENDATIONS:")
    if not devices_exist:
        print("- DMA heap devices missing - check kernel support")
    elif not can_access:
        print("- Permission issues - fix udev rules")
    elif not module_loaded:
        print("- Module not loaded - try: sudo modprobe dma_heap")
    else:
        print("- DMA heap appears to be working")

if __name__ == "__main__":
    main() 