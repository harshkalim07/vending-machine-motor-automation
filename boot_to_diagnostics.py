#!/usr/bin/env python3
"""
Vending Machine Auto-Boot to Diagnostics Screen
Navigates fully autonomously from Blue Launcher or Tray 1 into Machine Diagnostics:
1. Launches F&B App if on Blue Launcher (Shoonya DPC).
2. Long-presses UID: testsept (top right) to open Admin Login.
3. Immediately long-presses bottom-right 'Show Password' before the 49s QR timer expires.
4. Generates dynamic rolling OTP (e.g., today 13/11 -> Vman@1411), types it, and clicks LOGIN.
5. Clicks 'Machine Diagnostics' on the admin menu grid to land on the motor test screen!
"""

import os
import sys
import time
import subprocess
import re
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

ADB_BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "platform-tools", "adb.exe")
if not os.path.exists(ADB_BIN):
    ADB_BIN = "adb"

DEFAULT_TARGET = "124.20.12.15:5555"

class AutoBootDiagnostics:
    def __init__(self, target_device=DEFAULT_TARGET):
        self.target = target_device
        self.adb = ADB_BIN

    def run_cmd(self, cmd_args, timeout=15):
        full_cmd = [self.adb]
        if self.target:
            full_cmd.extend(["-s", self.target])
        full_cmd.extend(cmd_args)
        try:
            res = subprocess.run(full_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
            return res.returncode, res.stdout, res.stderr
        except Exception as e:
            return -1, "", str(e)

    def tap(self, x, y):
        self.run_cmd(["shell", f"input tap {int(x)} {int(y)}"])

    def long_press(self, x, y, duration_ms=2500):
        # In ADB, swipe in-place with a 1-pixel micro displacement triggers reliable long-press
        self.run_cmd(["shell", f"input swipe {int(x)} {int(y)} {int(x)} {int(y)+1} {int(duration_ms)}"])

    def type_text(self, text):
        self.run_cmd(["shell", f"input text '{text}'"])

    def get_current_ui_xml(self):
        remote_xml = "/data/local/tmp/state_check.xml"
        self.run_cmd(["shell", "uiautomator", "dump", remote_xml], timeout=10)
        code, out, _ = self.run_cmd(["shell", "cat", remote_xml], timeout=10)
        if code == 0 and "<?xml" in out:
            try:
                # Extract clean xml substring
                xml_str = out[out.find("<?xml"):]
                return ET.fromstring(xml_str.encode("utf-8", errors="replace"))
            except Exception:
                pass
        return None

    def detect_screen_state(self, root):
        if root is None:
            return "UNKNOWN"
        
        texts = [n.attrib.get("text", "") for n in root.iter("node")]
        res_ids = [n.attrib.get("resource-id", "") for n in root.iter("node")]
        all_text = " ".join(texts).lower()
        all_ids = " ".join(res_ids).lower()

        # 1. Target screen: Machine Diagnostics (Motor testing dashboard)
        if "clean board fault" in all_text or "bin + motor multiple" in all_text or "test bin sensor" in all_text:
            return "MACHINE_DIAGNOSTICS"

        # 2. Admin Menu Screen (Grid of 7 orange buttons)
        if ("information settings" in all_text or 
            "machine setup" in all_text or 
            "password management" in all_text or 
            "advanced setting" in all_text or
            ("machine diagnostics" in all_text and "clean board" not in all_text)):
            return "ADMIN_MENU"

        # 3. OTP Verification screen
        if "otp verification" in all_text or "enter otp" in all_text or "tv_otp_verification" in all_ids:
            return "OTP_SCREEN"

        # 4. Admin Login QR Code screen (with timer)
        if "scan qr" in all_text or "qrcode" in all_ids:
            return "ADMIN_LOGIN_QR"

        # 5. Tray / Catalog Screen (TRAY - 1 / UID: testsept)
        if "uid :" in all_text or "tray -" in all_text or "ll_uid_info_bar" in all_ids:
            return "TRAY_CATALOG"

        # 6. Blue Launcher (Shoonya DPC / Android desktop)
        if "f & b app" in all_text or "shoonya" in all_ids or "esper" in all_text:
            return "BLUE_LAUNCHER"

        return "UNKNOWN"

    def calculate_today_otp(self):
        """
        Calculates Vendiman daily admin OTP:
        Logic: 'Vman@' + (Tomorrow's Day %d) + (Tomorrow's Month %m)
        Example: Today 13/11/2026 -> Vman@1411
        """
        tomorrow = datetime.now() + timedelta(days=1)
        ddmm = tomorrow.strftime("%d%m")
        otp = f"Vman@{ddmm}"
        return otp

    def navigate_to_diagnostics(self, max_steps=12):
        print("=" * 65)
        print("🚀 STARTING AUTO-NAVIGATION TO MACHINE DIAGNOSTICS")
        print(f"Target Device: {self.target}")
        otp = self.calculate_today_otp()
        print(f"Dynamic Master OTP for today: {otp}")
        print("=" * 65)

        for step in range(1, max_steps + 1):
            print(f"\n[Step {step}/{max_steps}] Probing current kiosk screen state...")
            root = self.get_current_ui_xml()
            state = self.detect_screen_state(root)
            print(f"  👉 Detected Screen State: [{state}]")

            if state == "MACHINE_DIAGNOSTICS":
                print("\n🎉 SUCCESS: Already on Machine Diagnostics screen! Ready for testing.")
                return True

            elif state == "BLUE_LAUNCHER":
                print("  [Action] Launching F & B App from launcher...")
                self.run_cmd(["shell", "am", "start", "-n", "com.vendiman.foodandbeverage/.activity.SplashScreenActivity"])
                time.sleep(3.5)

            elif state == "TRAY_CATALOG":
                print("  [Action] Performing long-press on 'UID : testsept' (top-right)...")
                # ll_uid_info_bar bounds are roughly [816,1][1009,55] -> center (912, 28)
                uid_x, uid_y = 912, 28
                if root is not None:
                    for n in root.iter("node"):
                        if "ll_uid_info_bar" in n.attrib.get("resource-id", "") or "uid" in n.attrib.get("text", "").lower():
                            m = re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.attrib.get("bounds", ""))
                            if m:
                                uid_x = (int(m.group(1)) + int(m.group(3))) // 2
                                uid_y = (int(m.group(2)) + int(m.group(4))) // 2
                                break
                print(f"  Targeting UID at ({uid_x}, {uid_y}) for 2.5s...")
                self.long_press(uid_x, uid_y, duration_ms=2500)
                time.sleep(1.2)

            elif state == "ADMIN_LOGIN_QR":
                print("  [Action] On QR Code Screen. Long-pressing bottom-right secret 'Show Password'...")
                # ll_ShowPasswordLayout bounds are [892,1873][1080,1920] -> center (986, 1896)
                pwd_x, pwd_y = 986, 1896
                if root is not None:
                    for n in root.iter("node"):
                        if "ShowPassword" in n.attrib.get("resource-id", "") or "show password" in n.attrib.get("text", "").lower():
                            m = re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.attrib.get("bounds", ""))
                            if m:
                                pwd_x = (int(m.group(1)) + int(m.group(3))) // 2
                                pwd_y = (int(m.group(2)) + int(m.group(4))) // 2
                                break
                print(f"  Targeting Show Password at ({pwd_x}, {pwd_y}) for 2.5s...")
                self.long_press(pwd_x, pwd_y, duration_ms=2500)
                time.sleep(1.2)

            elif state == "OTP_SCREEN":
                print(f"  [Action] Entering OTP: '{otp}'...")
                # Find OTP input field and LOGIN button
                input_x, input_y = 540, 620
                login_x, login_y = 540, 709
                if root is not None:
                    for n in root.iter("node"):
                        cls = n.attrib.get("class", "")
                        txt = n.attrib.get("text", "").upper()
                        rid = n.attrib.get("resource-id", "").lower()
                        m = re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.attrib.get("bounds", ""))
                        if m:
                            cx = (int(m.group(1)) + int(m.group(3))) // 2
                            cy = (int(m.group(2)) + int(m.group(4))) // 2
                            if "edittext" in cls.lower() or "enter otp" in txt.lower():
                                input_x, input_y = cx, cy
                            if "LOGIN" in txt or "btn_login" in rid or "btnlogin" in rid or "btnsubmit" in rid:
                                login_x, login_y = cx, cy

                # Tap input field
                self.tap(input_x, input_y)
                time.sleep(0.3)
                # Clear existing text
                clear_keys = " ".join(["67"] * 20)
                self.run_cmd(["shell", f"input keyevent {clear_keys}"])
                time.sleep(0.2)

                # Type OTP safely (Handle '@' with Android KEYCODE_AT 77)
                if "@" in otp:
                    p1, p2 = otp.split("@", 1)
                    type_cmd = f"input text '{p1}' && input keyevent 77 && input text '{p2}'"
                else:
                    type_cmd = f"input text '{otp}'"
                self.run_cmd(["shell", type_cmd])
                time.sleep(0.4)

                # Hide soft keyboard if visible (KEYCODE_ESCAPE 111)
                self.run_cmd(["shell", "input keyevent 111"])
                time.sleep(0.3)

                # Tap LOGIN
                print(f"  [Action] Tapping LOGIN at ({login_x}, {login_y})...")
                self.tap(login_x, login_y)
                time.sleep(1.8)
                # Proactively click Machine Diagnostics in case Admin Menu already mounted
                print("  [Action] Transitioning: Tapping 'Machine Diagnostics' button at (280, 410)...")
                self.tap(280, 410)
                time.sleep(1.0)

            elif state == "ADMIN_MENU":
                print("  [Action] On Admin Menu grid. Tapping 'Machine Diagnostics' (Row 2, Left)...")
                diag_x, diag_y = 280, 410
                if root is not None:
                    for n in root.iter("node"):
                        if "machine diagnostics" in n.attrib.get("text", "").lower():
                            m = re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.attrib.get("bounds", ""))
                            if m:
                                diag_x = (int(m.group(1)) + int(m.group(3))) // 2
                                diag_y = (int(m.group(2)) + int(m.group(4))) // 2
                                break
                print(f"  Tapping Machine Diagnostics at ({diag_x}, {diag_y})...")
                self.tap(diag_x, diag_y)
                time.sleep(0.5)
                self.tap(diag_x, diag_y)  # Double tap to ensure click registered
                time.sleep(1.5)

            else:
                print("  [State Pending] Screen transition in progress. Re-probing...")
                time.sleep(1.2)

        print("❌ Reached maximum step attempts. Please check kiosk screen.")
        return False

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TARGET
    booter = AutoBootDiagnostics(target_device=target)
    success = booter.navigate_to_diagnostics()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
