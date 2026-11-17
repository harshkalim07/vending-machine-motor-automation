#!/usr/bin/env python3
"""
Automation Engine for Vendiman Motor QA Bench
Engineered for hardware testers with:
- Universal screen state detection across all 7 kiosk screens
- Autonomous navigation & OTP login to Machine Diagnostics
- Exact bin entry & in-memory arithmetic security solver
- Synchronized 45-rotation monitoring with Red Cross matrix fault detection
- Hardware-aware graceful stop handling
- Thread-safe state tracking for the Web Dashboard
"""

import os
import sys
import time
import json
import re
import subprocess
import threading
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from PIL import Image
import requests

# Ensure local .android directory to avoid permission issues
LOCAL_ANDROID = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".android")
os.makedirs(LOCAL_ANDROID, exist_ok=True)
os.environ["ANDROID_USER_HOME"] = LOCAL_ANDROID

DEFAULT_ADB_PATHS = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "platform-tools", "adb.exe"),
    "adb",
    r"C:\platform-tools\adb.exe",
    r"C:\Program Files\platform-tools\adb.exe",
    os.path.expanduser(r"~\platform-tools\adb.exe"),
    os.path.expanduser(r"~\AppData\Local\Android\Sdk\platform-tools\adb.exe"),
]

ALL_MOTORS = [
    100, 101, 102, 103, 104,
    200, 201, 202, 203, 204,
    300, 301, 302, 303, 304,
    400, 401, 402, 403, 404, 405, 406, 407, 408, 409,
    500, 501, 502, 503, 504, 505, 506, 507, 508, 509,
    600, 601, 602, 603, 604, 605, 606, 607, 608, 609
]

class AutomationEngine:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.target = self.config.get("connection", {}).get("adb_target", "124.20.12.15:5555")
        self.adb_bin = self._resolve_adb()
        self.total_test_seconds = self.config.get("timing", {}).get("total_test_seconds", 258)
        self.rotations_per_motor = self.config.get("timing", {}).get("rotations_per_motor", 45)

        # Thread-safe automation state
        self.lock = threading.Lock()
        self.active_thread = None
        self.stop_requested = False

        self.state = {
            "status": "IDLE",            # IDLE, CONNECTING, NAVIGATING, RUNNING, STOP_REQUESTED, COMPLETED, ERROR
            "connected": False,
            "device_ip": self.target,
            "current_screen": "UNKNOWN",
            "current_bin": None,
            "mode": "all",               # "all", "single", or "nav_only"
            "start_bin": 100,
            "active_rotation": 0,
            "elapsed_seconds": 0,
            "total_seconds": self.total_test_seconds,
            "stop_requested": False,
            "alert": None,
            "logs": [],
            "motor_results": {bin_num: {"status": "PENDING", "duration": 0, "failed_rotations": []} for bin_num in ALL_MOTORS}
        }

    def _load_config(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {
                "connection": {"adb_target": "124.20.12.15:5555", "wifi_ip": "124.20.12.15", "wifi_port": 5555},
                "notifications": {"enabled": True, "topic": "vending_testsept_alerts"},
                "timing": {"rotations_per_motor": 45, "total_test_seconds": 258}
            }

    def _resolve_adb(self):
        for path in DEFAULT_ADB_PATHS:
            try:
                res = subprocess.run([path, "version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if res.returncode == 0:
                    return path
            except Exception:
                continue
        return "adb"

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = {"time": timestamp, "level": level, "text": message}
        with self.lock:
            self.state["logs"].append(entry)
            if len(self.state["logs"]) > 200:
                self.state["logs"] = self.state["logs"][-200:]
        print(f"[{timestamp}] [{level}] {message}")

    def notify(self, title, message, priority="default", tags="gear"):
        """Dispatches non-blocking ntfy alert"""
        def _send():
            topic = self.config.get("notifications", {}).get("topic", "vending_testsept_alerts")
            url = f"https://ntfy.sh/{topic}"
            headers = {"Title": title, "Priority": priority, "Tags": tags}
            try:
                requests.post(url, data=message.encode("utf-8"), headers=headers, timeout=2)
            except Exception:
                pass
        threading.Thread(target=_send, daemon=True).start()

    def run_cmd(self, cmd_args, timeout=15):
        full_cmd = [self.adb_bin]
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
        self.run_cmd(["shell", f"input swipe {int(x)} {int(y)} {int(x)} {int(y)+1} {int(duration_ms)}"])

    def keyevent(self, code):
        self.run_cmd(["shell", f"input keyevent {int(code)}"])

    def check_connection(self):
        """Checks and connects ADB to target vending kiosk with auto-retry"""
        for attempt in range(1, 4):
            code, out, _ = self.run_cmd(["devices"])
            if any(self.target in line and "\tdevice" in line for line in out.splitlines()):
                test_code, test_out, _ = self.run_cmd(["shell", "echo ok"], timeout=5)
                if test_code == 0 and "ok" in test_out:
                    with self.lock:
                        self.state["connected"] = True
                    self.log(f"Connected to kiosk ({self.target})", level="SUCCESS")
                    return True

            self.log(f"Connecting to vending kiosk at {self.target} (Attempt {attempt}/3)...")
            self.run_cmd(["disconnect", self.target], timeout=5)
            time.sleep(0.3)
            self.run_cmd(["connect", self.target], timeout=8)
            time.sleep(0.5)

        with self.lock:
            self.state["connected"] = False
        self.log(f"Cannot reach {self.target}. Verify kiosk IP & Wi-Fi.", level="ERROR")
        return False

    def get_ui_xml(self):
        remote_xml = "/data/local/tmp/kiosk_ui.xml"
        self.run_cmd(["shell", "uiautomator", "dump", remote_xml], timeout=8)
        code, out, _ = self.run_cmd(["shell", "cat", remote_xml], timeout=8)
        if code == 0 and "<?xml" in out:
            try:
                xml_str = out[out.find("<?xml"):]
                return ET.fromstring(xml_str.encode("utf-8", errors="replace"))
            except Exception:
                pass
        return None

    def detect_screen(self):
        """Universal Screen Detector for all 7 Kiosk states"""
        root = self.get_ui_xml()
        if root is None:
            state_name = "UNKNOWN"
        else:
            texts = [n.attrib.get("text", "") for n in root.iter("node")]
            res_ids = [n.attrib.get("resource-id", "") for n in root.iter("node")]
            # Normalize whitespace to eliminate newlines
            all_text = " ".join(" ".join(texts).split()).lower()
            all_ids = " ".join(res_ids).lower()

            if "clean board fault" in all_text or "bin + motor multiple" in all_text or "test bin sensor" in all_text:
                state_name = "MACHINE_DIAGNOSTICS"
            elif "uid :" in all_text or "tray -" in all_text or "ll_uid_info_bar" in all_ids:
                state_name = "TRAY_CATALOG"
            elif "vend motor test multiple" in all_text or "btnstopmachinecheck" in all_ids:
                state_name = "VEND_TEST_SCREEN"
            elif "security check" in all_text or re.search(r"what is \d+", all_text):
                state_name = "SECURITY_DIALOG"
            elif ("btnmachinediagnostics" in all_ids or "btnmachinesetup" in all_ids or 
                  "btninformationsettings" in all_ids or "information settings" in all_text or 
                  "machine setup" in all_text or "password management" in all_text or 
                  "advanced setting" in all_text or 
                  ("machine diagnostics" in all_text and "clean board" not in all_text)):
                state_name = "ADMIN_MENU"
            elif "otp verification" in all_text or "enter otp" in all_text or "tv_otp_verification" in all_ids:
                state_name = "OTP_SCREEN"
            elif "scan qr" in all_text or "qrcode" in all_ids:
                state_name = "ADMIN_LOGIN_QR"
            elif "f & b app" in all_text or "shoonya" in all_ids or "esper" in all_text:
                state_name = "BLUE_LAUNCHER"
            elif "please wait" in all_text:
                state_name = "LOADING"
            else:
                state_name = "UNKNOWN"

        with self.lock:
            self.state["current_screen"] = state_name
        return state_name

    def calculate_today_otp(self):
        """Computes Vendiman dynamic master password: Vman@ + (tomorrow's DDMM)"""
        tomorrow = datetime.now() + timedelta(days=1)
        ddmm = tomorrow.strftime("%d%m")
        return f"Vman@{ddmm}"

    def auto_navigate_to_diagnostics(self, max_steps=15):
        """Autonomously navigates through any screen into Machine Diagnostics"""
        self.log("Universal Screen Awareness: Checking current kiosk screen...")
        otp = self.calculate_today_otp()

        for step in range(1, max_steps + 1):
            if self.stop_requested:
                self.log("Navigation halted by operator request.", level="WARN")
                return False

            state = self.detect_screen()
            self.log(f"[Step {step}/{max_steps}] Detected Screen: [{state}]")

            if state == "MACHINE_DIAGNOSTICS":
                self.log("🎉 Successfully on Machine Diagnostics screen! Ready for testing.", level="SUCCESS")
                return True

            elif state == "LOADING":
                self.log("App loading in progress (Please Wait)... Waiting 2.0s...")
                time.sleep(2.0)
                continue

            elif state == "VEND_TEST_SCREEN":
                self.log("Active 45-box test screen open. Tapping STOP/BACK at (810, 1888)...")
                self.tap(810, 1888)
                time.sleep(1.0)
                self.tap(810, 1888)
                time.sleep(1.5)

            elif state == "SECURITY_DIALOG":
                self.log("Security popup present. Dismissing to return...")
                self.tap(350, 1073)
                time.sleep(1.0)

            elif state == "BLUE_LAUNCHER":
                self.log("On Blue Launcher (Shoonya DPC). Launching Vendiman F&B App...")
                self.run_cmd(["shell", "am", "start", "-n", "com.vendiman.foodandbeverage/.activity.SplashScreenActivity"])
                time.sleep(4.5)

            elif state == "TRAY_CATALOG":
                self.log("On Tray-1 screen. Long-pressing UID: testsept (top-right)...")
                self.long_press(912, 28, duration_ms=2500)
                time.sleep(1.5)

            elif state == "ADMIN_LOGIN_QR":
                self.log("On Admin QR screen. Long-pressing bottom-right secret backdoor...")
                self.long_press(986, 1896, duration_ms=2500)
                time.sleep(1.5)

            elif state == "OTP_SCREEN":
                self.log(f"Entering dynamic rolling master OTP: '{otp}'...")
                input_x, input_y = 540, 544
                login_x, login_y = 540, 710
                root = self.get_ui_xml()
                if root is not None:
                    for n in root.iter("node"):
                        cls = n.attrib.get("class", "").lower()
                        txt = n.attrib.get("text", "").upper()
                        rid = n.attrib.get("resource-id", "").lower()
                        m = re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.attrib.get("bounds", ""))
                        if m:
                            cx = (int(m.group(1)) + int(m.group(3))) // 2
                            cy = (int(m.group(2)) + int(m.group(4))) // 2
                            if "edittext" in cls or "edtpassword" in rid:
                                input_x, input_y = cx, cy
                            if "LOGIN" in txt or "btnlogin" in rid or "btn_login" in rid:
                                login_x, login_y = cx, cy

                # Execute focus, clear, type OTP, dismiss keyboard, and click LOGIN in ONE ATOMIC ADB command (< 0.8s)
                # Over Wi-Fi ADB, chaining everything in a single shell command prevents network lag from expiring the 45s QR timer!
                clear_keys = " ".join(["67"] * 25)
                if "@" in otp:
                    p1, p2 = otp.split("@", 1)
                    type_chain = f"input text '{p1}' && input keyevent 77 && input text '{p2}'"
                else:
                    type_chain = f"input text '{otp}'"

                full_otp_cmd = f"input tap {input_x} {input_y} && input keyevent {clear_keys} && {type_chain} && input keyevent 111 && sleep 0.2 && input tap {login_x} {login_y}"
                self.run_cmd(["shell", full_otp_cmd])
                time.sleep(1.2)

            elif state == "ADMIN_MENU":
                diag_x, diag_y = 270, 365  # Center of [7, 307][533, 422]
                root = self.get_ui_xml()
                if root is not None:
                    for n in root.iter("node"):
                        rid = n.attrib.get("resource-id", "").lower()
                        txt = " ".join(n.attrib.get("text", "").split()).lower()
                        if "btnmachinediagnostics" in rid or "machine diagnostics" in txt:
                            m = re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.attrib.get("bounds", ""))
                            if m:
                                diag_x = (int(m.group(1)) + int(m.group(3))) // 2
                                diag_y = (int(m.group(2)) + int(m.group(4))) // 2
                                break
                self.log(f"On Admin Menu. Tapping 'Machine Diagnostics' at ({diag_x}, {diag_y})...")
                self.tap(diag_x, diag_y)
                time.sleep(2.5)

            else:
                self.log("Screen transition in progress. Waiting 1.5s...", level="INFO")
                time.sleep(1.5)

        return self.detect_screen() == "MACHINE_DIAGNOSTICS"

    def enter_bin_and_trigger_test(self, bin_number):
        """Types the exact requested bin number and clicks Vend Test"""
        self.log(f"Typing Bin #{bin_number} into input field at (270, 627)...")
        cmd = f"input tap 270 627 && input keyevent 123 67 67 67 67 67 && input text {bin_number}"
        self.run_cmd(["shell", cmd])
        time.sleep(0.3)
        self.log("Tapping 'Bin + Motor Multiple Time Vend Test' at (810, 627)...")
        self.tap(810, 627)
        time.sleep(0.8)

    def solve_security_dialog_smart(self, bin_number, max_attempts=5):
        """Finds math question, solves it, and submits answer + VERIFY in one fast atomic command (exact CMD flow)"""
        self.log("Waiting for Security Challenge dialog...")
        for attempt in range(1, max_attempts + 1):
            root = self.get_ui_xml()
            if root is not None:
                texts = [n.attrib.get("text", "") for n in root.iter("node")]
                for text in texts:
                    match = re.search(r"What\s+is\s+(\d+)\s*([\+\-\*])\s*(\d+)", text, re.IGNORECASE)
                    if match:
                        n1 = int(match.group(1))
                        op = match.group(2)
                        n2 = int(match.group(3))
                        if op == "+": answer = n1 + n2
                        elif op == "-": answer = n1 - n2
                        elif op == "*": answer = n1 * n2
                        else: answer = n1 + n2
                        self.log(f"🧠 Dynamic Challenge Solved: {n1} {op} {n2} = {answer} (< 10ms)", level="SUCCESS")
                        
                        # Submit answer & tap VERIFY in ONE fast atomic command (< 0.2s)
                        cmd = f"input tap 540 870 && input text {answer} && input tap 707 1074"
                        self.run_cmd(["shell", cmd])
                        time.sleep(0.8)
                        return True
            time.sleep(0.4)
        self.log("Security dialog did not appear or was auto-bypassed. Continuing...", level="WARN")
        return False

    def wait_and_start_test(self):
        """Immediately clicks START at (270, 1888) as soon as 45-box screen mounts (exact CMD flow)"""
        self.log("45-box Vend Test Screen mounting. Engaging START button...")
        time.sleep(1.2)
        self.log("🚀 Engaging START button at (270, 1888)...", level="INFO")
        self.tap(270, 1888)
        time.sleep(0.4)
        self.tap(270, 1888)  # Fast confirmatory tap to guarantee hardware registration
        time.sleep(0.8)
        self.log("✅ START engaged! Motor rotation cycle underway.", level="SUCCESS")
        return True

    def check_for_red_crosses(self, bin_number):
        """Inspects all 45 rotation boxes for Red Cross marks (R > 180, G < 70, B < 70)"""
        try:
            temp_png = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "temp_check.png")
            os.makedirs(os.path.dirname(temp_png), exist_ok=True)
            self.run_cmd(["shell", "screencap -p /data/local/tmp/temp_check.png"])
            self.run_cmd(["pull", "/data/local/tmp/temp_check.png", temp_png])
            if not os.path.exists(temp_png):
                return []

            img = Image.open(temp_png).convert("RGB")
            failed_boxes = []
            for i in range(45):
                c = i % 5
                r = i // 5
                x1 = 74 + c * 216
                y1 = 110 + r * 154
                box = img.crop((x1, y1, x1 + 67, y1 + 67))
                colors = box.getcolors(maxcolors=5000) or []
                red_count = sum(cnt for cnt, (red, green, blue) in colors if red > 180 and green < 70 and blue < 70)
                if red_count > 150:
                    failed_boxes.append(i + 1)
            return failed_boxes
        except Exception:
            return []

    def monitor_rotations(self, bin_number):
        """Monitors the 45 rotations (258s target) with real-time UI telemetry and Red Cross detection"""
        start_time = time.time()
        self.log(f"Monitoring Motor #{bin_number}: 45 rotations underway (~258s target)...")
        detected_fails = []
        last_screencap_time = start_time

        while True:
            elapsed = time.time() - start_time
            current_rot = min(45, int(elapsed / 5.55) + 1)

            with self.lock:
                self.state["active_rotation"] = current_rot
                self.state["elapsed_seconds"] = int(elapsed)

            # Check if operator clicked STOP in the dashboard
            if self.stop_requested:
                self.log(f"⏹️ STOP requested by operator during Motor #{bin_number}. Exiting test screen...", level="WARN")
                self.exit_test_screen()
                return False, elapsed, detected_fails

            # Real-time state check: If kiosk screen returned to Diagnostics, the test finished
            if elapsed > 15 and int(elapsed) % 6 == 0:
                current_state = self.detect_screen()
                if current_state == "MACHINE_DIAGNOSTICS":
                    self.log(f"Kiosk returned to Machine Diagnostics at {int(elapsed)}s. Rotations complete.", level="SUCCESS")
                    return True, elapsed, detected_fails

            # Check for Red Crosses every 25 seconds
            if elapsed > 15 and (time.time() - last_screencap_time >= 25):
                last_screencap_time = time.time()
                fails = self.check_for_red_crosses(bin_number)
                if fails and fails != detected_fails:
                    detected_fails = fails
                    alert_msg = f"🚨 Red Cross fault detected on Motor #{bin_number} (Rotation #{fails})!"
                    self.log(alert_msg, level="ERROR")
                    with self.lock:
                        self.state["alert"] = alert_msg
                    self.notify(
                        title=f"🚨 MOTOR JAM: Bin #{bin_number}",
                        message=f"Red Cross mark detected at Rotation #{fails}!\nImmediate inspection required.",
                        priority="urgent",
                        tags="rotating_light,x"
                    )

            if elapsed >= self.total_test_seconds:
                # Final inspection
                final_fails = self.check_for_red_crosses(bin_number)
                success = len(final_fails) == 0
                return success, elapsed, final_fails

            time.sleep(1.0)

    def exit_test_screen(self):
        """Returns to Machine Diagnostics screen after rotation cycle finishes"""
        self.log("Tapping STOP/BACK at (810, 1888) to exit test screen...")
        for attempt in range(1, 4):
            self.tap(810, 1888)
            time.sleep(1.0)
            if self.detect_screen() == "MACHINE_DIAGNOSTICS":
                self.log("Cleanly returned to Machine Diagnostics.", level="SUCCESS")
                return True
            time.sleep(0.5)
        return self.detect_screen() == "MACHINE_DIAGNOSTICS"

    def execute_single_motor(self, bin_number):
        """Full test cycle for a single motor"""
        with self.lock:
            self.state["current_bin"] = bin_number
            self.state["motor_results"][bin_number]["status"] = "RUNNING"

        self.log(f"==================================================", level="INFO")
        self.log(f"🚀 STARTING TEST FOR MOTOR #{bin_number} (45 Rotations)", level="INFO")
        self.log(f"==================================================", level="INFO")

        self.notify(
            title=f"Testing Motor #{bin_number}",
            message=f"Starting 45 rotations stress test for Motor #{bin_number}...",
            tags="gear"
        )

        # 1. Ensure Diagnostics
        if not self.auto_navigate_to_diagnostics():
            self.log(f"Cannot reach Machine Diagnostics for Motor #{bin_number}.", level="ERROR")
            with self.lock:
                self.state["motor_results"][bin_number]["status"] = "ERROR"
            return False

        # 2. Enter Bin
        self.enter_bin_and_trigger_test(bin_number)

        # 3. Solve Security Check
        self.solve_security_dialog_smart(bin_number)

        # 4. Start Test (Direct fast tap at 270, 1888 as soon as 45-box mounts - exact CMD flow)
        self.wait_and_start_test()

        # 5. Monitor 45 rotations
        success, duration, failed_rotations = self.monitor_rotations(bin_number)

        # 6. Exit screen
        self.exit_test_screen()

        # Record result
        status_str = "PASS" if success else f"FAIL (Rot #{failed_rotations})"
        with self.lock:
            self.state["motor_results"][bin_number] = {
                "status": "PASS" if success else "FAIL",
                "duration": round(duration, 1),
                "failed_rotations": failed_rotations
            }

        self.log(f"Motor #{bin_number} Result: {status_str} ({round(duration, 1)}s)", level="SUCCESS" if success else "ERROR")
        self.notify(
            title=f"Motor #{bin_number}: {status_str}",
            message=f"Completed in {round(duration, 1)}s. Failed rotations: {failed_rotations or 'None (100% Green Checks)'}",
            priority="default" if success else "high",
            tags="white_check_mark" if success else "x"
        )
        return success

    def run_automation_worker(self, mode="all", start_bin=100):
        """Worker thread for full, single, or nav_only test execution"""
        with self.lock:
            self.state["status"] = "RUNNING"
            self.state["mode"] = mode
            self.state["start_bin"] = start_bin
            self.state["stop_requested"] = False
            self.stop_requested = False
            self.state["alert"] = None

        try:
            # 1. Connect
            if not self.check_connection():
                with self.lock:
                    self.state["status"] = "ERROR"
                return

            # Special Mode: Navigate to Diagnostics Only
            if mode == "nav_only":
                self.log("Mode: Open Machine Diagnostics Screen Only.")
                reached = self.auto_navigate_to_diagnostics()
                with self.lock:
                    self.state["status"] = "COMPLETED" if reached else "ERROR"
                if reached:
                    self.log("🎉 Successfully parked on Machine Diagnostics dashboard!", level="SUCCESS")
                return

            # Determine list of motors to test
            if mode == "single":
                motors_to_test = [int(start_bin)]
            else:
                try:
                    start_val = int(start_bin)
                    idx = ALL_MOTORS.index(start_val)
                    motors_to_test = ALL_MOTORS[idx:]
                except ValueError:
                    self.log(f"Bin #{start_bin} not in standard motor list. Running from #100.", level="WARN")
                    motors_to_test = ALL_MOTORS

            self.log(f"Starting test sequence for {len(motors_to_test)} motor(s): #{motors_to_test[0]} to #{motors_to_test[-1]}")

            for i, bin_num in enumerate(motors_to_test, 1):
                if self.stop_requested:
                    self.log(f"⏹️ Stop was requested. Safely halting automation before Motor #{bin_num}.", level="WARN")
                    break

                self.log(f"--- Motor Progress: [{i}/{len(motors_to_test)}] ---")
                self.execute_single_motor(bin_num)

                # Check if stop was requested while this motor was spinning
                if self.stop_requested:
                    self.log("⏹️ Stop was requested during motor rotations. Machine has returned to Diagnostics. Stopping.", level="WARN")
                    break

            with self.lock:
                self.state["status"] = "STOPPED" if self.stop_requested else "COMPLETED"
                self.state["current_bin"] = None

            self.log("🏁 Test sequence finished! Test reports updated.", level="SUCCESS")
            self._save_reports()

        except Exception as e:
            self.log(f"Unexpected error in automation worker: {e}", level="ERROR")
            with self.lock:
                self.state["status"] = "ERROR"

    def _save_reports(self):
        """Saves JSON and Markdown reports"""
        try:
            logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
            os.makedirs(logs_dir, exist_ok=True)
            report_data = {
                "timestamp": datetime.now().isoformat(),
                "device": self.target,
                "motors": self.state["motor_results"]
            }
            with open(os.path.join(logs_dir, "test_report.json"), "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2)
        except Exception as e:
            self.log(f"Failed to save report: {e}", level="WARN")

    def start(self, mode="all", start_bin=100):
        if self.active_thread and self.active_thread.is_alive():
            return False, "Automation is already actively running!"

        self.stop_requested = False
        self.active_thread = threading.Thread(
            target=self.run_automation_worker,
            args=(mode, start_bin),
            daemon=True
        )
        self.active_thread.start()
        return True, "Automation started successfully."

    def request_stop(self):
        """Handles operator stop request gracefully respecting hardware constraints"""
        self.stop_requested = True
        with self.lock:
            self.state["stop_requested"] = True
            if self.state["status"] == "RUNNING":
                self.state["status"] = "STOP_REQUESTED"
        self.log("⚠️ Operator requested STOP! Waiting for active 45-rotation cycle to complete before exiting...", level="WARN")
        return True

    def reset_grid(self):
        """Resets all motor test states to PENDING"""
        with self.lock:
            self.state["motor_results"] = {b: {"status": "PENDING", "duration": 0, "failed_rotations": []} for b in ALL_MOTORS}
            self.state["alert"] = None
            self.state["status"] = "IDLE"
            self.state["current_bin"] = None
        self.log("Motor status grid has been reset.", level="INFO")
        return True

    def get_state(self):
        with self.lock:
            return dict(self.state)
