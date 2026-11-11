#!/usr/bin/env python3
"""
Interactive Connection & Diagnostic Tool for Vending Machine Box.
Helps discover the box IP, test ADB communication, and launch automation.
"""

import subprocess
import socket
import sys
import os
import time
import json

def check_port(ip, port=5555, timeout=1.0):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        res = s.connect_ex((ip, port))
        s.close()
        return res == 0
    except Exception:
        return False

def get_adb_bin():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        "adb",
        os.path.join(script_dir, "platform-tools", "adb.exe"),
        r"C:\platform-tools\adb.exe",
        os.path.expanduser(r"~\platform-tools\adb.exe"),
    ]
    for c in candidates:
        try:
            res = subprocess.run([c, "version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode == 0:
                return c
        except Exception:
            continue
    return None

def test_adb_connection(ip):
    adb_bin = get_adb_bin()
    if not adb_bin:
        print("\n[!] ADB executable not found on your PC yet.")
        print("Please run this command first in your terminal to download it:")
        print("  powershell -ExecutionPolicy Bypass -File setup_adb.ps1")
        return False

    print(f"\n[ADB] Testing connection to {ip}:5555 using {adb_bin}...")
    res = subprocess.run([adb_bin, "connect", f"{ip}:5555"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print(f"Output: {res.stdout.strip()}")
    
    # Check devices
    dev_res = subprocess.run([adb_bin, "devices"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print(f"Connected devices:\n{dev_res.stdout.strip()}")
    
    if ip in dev_res.stdout:
        print(f"\n[SUCCESS] Successfully connected to Vending Machine at {ip}!")
        return True
    return False

def get_default_ip():
    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            return cfg.get("connection", {}).get("wifi_ip", "192.168.1.100")
        except Exception:
            pass
    return "192.168.1.100"

def main():
    print("=" * 65)
    print("VENDING MACHINE NETWORK / ADB CONNECTION HELPER")
    print("=" * 65)
    
    default_ip = get_default_ip()
    print("\nConnection Options:")
    print(f"  [1] Use configured IP ({default_ip} - Default)")
    print("  [2] Enter custom IP")
    
    choice = input("\nSelect option [Default 1]: ").strip()
    if choice == "2":
        ip = input("Enter target device IP: ").strip()
    else:
        ip = default_ip

    print(f"\n[Check] Checking if {ip} is responding on port 5555 (ADB)...")
    if check_port(ip, 5555):
        print(f"  [OK] Port 5555 is OPEN on {ip}!")
        success = test_adb_connection(ip)
        if success:
            # Query device details
            try:
                adb_bin = get_adb_bin() or "adb"
                res = subprocess.run([adb_bin, "-s", f"{ip}:5555", "shell", "getprop", "ro.product.model"], 
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                model = res.stdout.strip()
                if model:
                    print(f"  [Device Model]: {model}")
            except Exception:
                pass

            # Update config.json with this IP
            try:
                cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                cfg["connection"]["type"] = "wifi"
                cfg["connection"]["wifi_ip"] = ip
                cfg["connection"]["adb_target"] = f"{ip}:5555"
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2)
                print(f"[Config] Saved {ip}:5555 to config.json automatically!")
            except Exception as e:
                print(f"[Config Note] Could not update config.json: {e}")

            print("\n" + "=" * 65)
            print("YOU ARE CONNECTED AND READY!")
            print("Start the automated test by running:")
            print("  python vending_adb_automator.py")
            print("=" * 65)
    else:
        print(f"  [!] Port 5555 is not currently responding on {ip}.")
        test_adb_connection(ip)

if __name__ == "__main__":
    main()
