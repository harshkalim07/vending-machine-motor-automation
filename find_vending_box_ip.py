#!/usr/bin/env python3
"""
Vending Machine IP Finder.
Scans the local network subnet to find the vending machine Android box listening on ADB port 5555 or pingable.
"""

import socket
import concurrent.futures
import sys
import os

def check_ip(ip, port=5555, timeout=0.8):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        if result == 0:
            return ip, True
    except Exception:
        pass
    return ip, False

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Dummy connect to find outbound interface
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def scan_subnet(subnet_base=None, port=5555, max_workers=60):
    if not subnet_base:
        local_ip = get_local_ip()
        print(f"[Finder] Your PC Local IP: {local_ip}")
        parts = local_ip.split(".")
        if len(parts) == 4 and parts[0] != "127":
            subnet_base = f"{parts[0]}.{parts[1]}.{parts[2]}"
        else:
            subnet_base = "192.168.1"

    print(f"[Finder] Scanning subnet {subnet_base}.1 to {subnet_base}.254 on port {port} (ADB)...")
    ips_to_scan = [f"{subnet_base}.{i}" for i in range(1, 255)]
    found = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(check_ip, ip, port): ip for ip in ips_to_scan}
        for future in concurrent.futures.as_completed(futures):
            ip, is_open = future.result()
            if is_open:
                found.append(ip)
                print(f"  --> FOUND Android ADB Device at: {ip}:{port}")

    if found:
        print("\n[SUCCESS] Found device(s):")
        for f in found:
            print(f"  👉 {f}")
            print(f"     Run: adb connect {f}:5555")
    else:
        print("\n[Info] No devices found on port 5555 in this subnet.")
        print("Tip: If the vending machine is on a different subnet (e.g. 192.168.1.x or 192.168.0.x), specify it:")
        print("     python find_vending_box_ip.py 192.168.1")

    return found

if __name__ == "__main__":
    target_subnet = sys.argv[1] if len(sys.argv) > 1 else None
    scan_subnet(target_subnet)
