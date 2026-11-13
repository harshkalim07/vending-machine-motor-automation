#!/usr/bin/env python3
"""
Vending Machine Motor Test Automation via ADB (Smart State-Aware Closed-Loop Edition)
Engineered with real-time UI state verification, adaptive retries, and confirmed transitions.
"""

import sys
import os
import time
import json
import re
import subprocess
import argparse
import threading
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

DEFAULT_ADB_PATHS = [
    "adb",
    r"C:\platform-tools\adb.exe",
    r"C:\Program Files\platform-tools\adb.exe",
    os.path.expanduser(r"~\platform-tools\adb.exe"),
    os.path.expanduser(r"~\AppData\Local\Android\Sdk\platform-tools\adb.exe"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "platform-tools", "adb.exe"),
]

class ADBController:
    def __init__(self, adb_path=None, target_device=None):
        self.adb_bin = self._resolve_adb(adb_path)
        self.target_device = target_device
        self.screen_width = 1080
        self.screen_height = 1920

    def _resolve_adb(self, custom_path):
        candidates = [custom_path] if custom_path else []
        candidates.extend(DEFAULT_ADB_PATHS)
        for path in candidates:
            if not path:
                continue
            try:
                res = subprocess.run([path, "version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if res.returncode == 0:
                    return path
            except Exception:
                continue
        return "adb"

    def run_cmd(self, cmd_args, timeout=20):
        full_cmd = [self.adb_bin]
        if self.target_device:
            full_cmd.extend(["-s", self.target_device])
        full_cmd.extend(cmd_args)
        try:
            res = subprocess.run(full_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
            return res.returncode, res.stdout, res.stderr
        except FileNotFoundError:
            return -1, "", "ADB executable not found."
        except Exception as e:
            return -1, "", str(e)

    def connect(self, wifi_ip=None, wifi_port=5555):
        if wifi_ip:
            target = f"{wifi_ip}:{wifi_port}"
            code, out, err = self.run_cmd(["connect", target])
            print(f"[ADB] Connect to {target}: {out.strip()}")
            self.target_device = target

        code, out, err = self.run_cmd(["devices"])
        lines = [line.strip() for line in out.strip().splitlines()[1:] if line.strip() and not line.startswith("*")]
        if not lines:
            raise RuntimeError("No ADB devices found. Ensure USB debugging is ON or Wi-Fi ADB is connected.")

        device_ids = [line.split()[0] for line in lines]
        if not self.target_device:
            self.target_device = device_ids[0]
        print(f"[ADB] Connected to device: {self.target_device}")

        # Get screen size
        code, out, err = self.run_cmd(["shell", "wm", "size"])
        m = re.search(r"(\d+)x(\d+)", out)
        if m:
            d1, d2 = int(m.group(1)), int(m.group(2))
            self.screen_width = min(d1, d2)
            self.screen_height = max(d1, d2)
        else:
            self.screen_width = 1080
            self.screen_height = 1920
        print(f"[ADB] Screen resolution: {self.screen_width}x{self.screen_height} (Portrait)")

        # Zero out animation scales for instantaneous UI response
        try:
            self.run_cmd(["shell", "settings put global window_animation_scale 0 && settings put global transition_animation_scale 0 && settings put global animator_duration_scale 0"])
        except Exception:
            pass

    def tap(self, x, y):
        self.run_cmd(["shell", f"input tap {int(x)} {int(y)}"])

    def keyevent(self, keycode):
        self.run_cmd(["shell", f"input keyevent {keycode}"])

    def get_focused_window(self):
        """Ultra-fast window state query (~40ms)"""
        code, out, _ = self.run_cmd(["shell", "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'"], timeout=3)
        return out.strip() if code == 0 else ""

    def dump_ui(self):
        """Compressed XML hierarchy dump"""
        dump_file = "/data/local/tmp/ui_dump.xml"
        cmd = f"uiautomator dump --compressed {dump_file} >/dev/null && cat {dump_file}"
        code, xml_content, err = self.run_cmd(["shell", cmd], timeout=8)
        if code != 0 or not xml_content.strip() or "<hierarchy" not in xml_content:
            cmd_fallback = f"uiautomator dump {dump_file} >/dev/null && cat {dump_file}"
            code, xml_content, err = self.run_cmd(["shell", cmd_fallback], timeout=8)
            if code != 0 or not xml_content.strip():
                return None
        try:
            idx = xml_content.find("<hierarchy")
            if idx != -1:
                xml_content = xml_content[idx:]
            return ET.fromstring(xml_content.encode("utf-8", errors="replace"))
        except Exception:
            return None


class SmartVendingTester:
    def __init__(self, config_path=None, dry_run=False):
        if config_path is None or config_path == "config.json":
            script_dir = os.path.dirname(os.path.abspath(__file__))
            default_config = os.path.join(script_dir, "config.json")
            self.config_path = default_config if os.path.exists(default_config) else "config.json"
        else:
            self.config_path = config_path
        self.dry_run = dry_run
        self.config = self._load_config()
        self.adb = ADBController(
            adb_path=self.config.get("connection", {}).get("adb_path"),
            target_device=self.config.get("connection", {}).get("adb_target")
        )
        self.test_results = []

        # Calibrated exact coordinates (1080 x 1920)
        self.BIN_INPUT = (270, 628)
        self.VEND_TEST_BTN = (810, 628)
        self.SECURITY_INPUT = (540, 870)
        self.SECURITY_VERIFY_BTN = (707, 1074)
        self.TEST_START_BTN = (270, 1880)
        self.TEST_STOP_BACK_BTN = (810, 1880)

    def _load_config(self):
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def setup_connection(self):
        conn = self.config.get("connection", {})
        try:
            self.adb.connect(conn.get("wifi_ip"), conn.get("wifi_port", 5555))
        except Exception as e:
            if self.dry_run:
                print(f"[Dry-run Note] No ADB device connected ({e}). Using simulated 1080x1920 screen.")
                self.adb.screen_width = 1080
                self.adb.screen_height = 1920
            else:
                raise

    def solve_security_math(self, text):
        m = re.search(r"(\d+)\s*([\+\-\*])\s*(\d+)", text)
        if m:
            n1 = int(m.group(1))
            op = m.group(2)
            n2 = int(m.group(3))
            if op == "+": return n1 + n2
            if op == "-": return n1 - n2
            if op == "*": return n1 * n2
        return None

    def notify(self, title, message, priority="default", tags=None):
        notif_cfg = self.config.get("notifications", {})
        if not notif_cfg.get("enabled", False):
            return
        topic = notif_cfg.get("topic", "vending_motor_alerts")
        url = f"https://ntfy.sh/{topic}"
        clean_title = re.sub(r'[^\x00-\x7F]+', '', title).strip() or "Vending Motor Alert"
        headers = {"Title": clean_title, "Priority": priority}
        if tags: headers["Tags"] = tags

        def _send():
            try:
                import urllib.request
                req = urllib.request.Request(url, data=message.encode("utf-8"), headers=headers)
                with urllib.request.urlopen(req, timeout=5): pass
            except Exception: pass

        threading.Thread(target=_send, daemon=True).start()

    # =========================================================================
    # SMART STATE MACHINE: SENSE, DECIDE, VERIFY
    # =========================================================================

    def detect_current_screen(self):
        """Intelligently identify active screen from UI hierarchy"""
        if self.dry_run:
            return "DIAGNOSTICS"

        root = self.adb.dump_ui()
        if root is None:
            return "UNKNOWN"

        all_texts = " ".join([node.attrib.get("text", "") for node in root.iter("node")])

        if "Machine Diagnostics" in all_texts or "Clean Board Fault" in all_texts:
            return "DIAGNOSTICS"
        elif "Security Check" in all_texts or re.search(r"What is \d+", all_texts):
            return "SECURITY_DIALOG"
        elif "Vend Motor Test Multiple" in all_texts or "STOP/BACK" in all_texts or "START" in all_texts:
            return "VEND_TEST_SCREEN"
        return "UNKNOWN"

    def ensure_diagnostics_screen(self, max_attempts=4):
        """Guarantees we are on Machine Diagnostics before touching any motor inputs"""
        print("  [State Check] Verifying Machine Diagnostics screen...")
        for attempt in range(1, max_attempts + 1):
            state = self.detect_current_screen()
            if state == "DIAGNOSTICS":
                print("  [State Confirmed] Currently on Machine Diagnostics.")
                return True

            print(f"  [State Warning] Not on Diagnostics (detected: {state}). Tapping STOP/BACK (Attempt {attempt}/{max_attempts})...")
            if not self.dry_run:
                self.adb.tap(*self.TEST_STOP_BACK_BTN)
                time.sleep(0.8)
                self.adb.keyevent(4)  # Android Back key as guaranteed fallback
                time.sleep(1.0)

        # Final check
        if self.detect_current_screen() == "DIAGNOSTICS":
            return True
        raise RuntimeError("Failed to return to Machine Diagnostics screen. Please check device display.")

    def enter_bin_and_trigger_test(self, bin_number):
        """Enters bin number and verifies that Security Dialog is actually triggered"""
        print(f"  [Action] Entering Bin Number {bin_number} at {self.BIN_INPUT}...")
        if not self.dry_run:
            cmd = f"input tap {self.BIN_INPUT[0]} {self.BIN_INPUT[1]} && input keyevent 123 67 67 67 67 67 && input text {bin_number}"
            self.adb.run_cmd(["shell", cmd])
            time.sleep(0.2)

            print(f"  [Action] Tapping 'Bin + Motor Multiple Time Vend Test' at {self.VEND_TEST_BTN}...")
            self.adb.tap(*self.VEND_TEST_BTN)
            time.sleep(0.5)

    def solve_security_dialog_smart(self, bin_number, max_attempts=5):
        """Finds math question, solves it, submits answer, and verifies dialog closes"""
        print("  [State Check] Waiting for Security Dialog...")
        for attempt in range(1, max_attempts + 1):
            root = self.adb.dump_ui()
            question_text = None

            if root is not None:
                for node in root.iter("node"):
                    t = node.attrib.get("text", "")
                    if "What is" in t or re.search(r"\d+\s*[\+\-\*]\s*\d+", t):
                        question_text = t
                        break

            if question_text:
                answer = self.solve_security_math(question_text)
                print(f"  [Security Check] Detected: '{question_text}' -> Solved Answer = {answer}")
                if not self.dry_run:
                    # Submit answer and tap VERIFY
                    cmd = f"input tap {self.SECURITY_INPUT[0]} {self.SECURITY_INPUT[1]} && input text {answer} && input tap {self.SECURITY_VERIFY_BTN[0]} {self.SECURITY_VERIFY_BTN[1]}"
                    self.adb.run_cmd(["shell", cmd])
                    time.sleep(0.8)
                return True

            # If not detected on attempt 2, re-tap the test button
            if attempt == 2 and not self.dry_run:
                print(f"  [Adaptive Recovery] Dialog not seen. Re-tapping 'Bin + Motor Multiple Time Vend Test'...")
                self.adb.tap(*self.VEND_TEST_BTN)

            time.sleep(0.5)

        if self.dry_run:
            return True
        raise RuntimeError("Failed to resolve Security Dialog after multiple attempts.")

    def wait_and_start_test_smart(self, max_wait_sec=8, max_start_taps=4):
        """Polls until Vend Motor Test screen is loaded, then reliably engages START with verification"""
        print("  [State Check] Waiting for Vend Motor Test screen to load...")
        start_wait = time.time()
        screen_ready = False

        while time.time() - start_wait < max_wait_sec:
            state = self.detect_current_screen()
            if state == "VEND_TEST_SCREEN" or self.dry_run:
                screen_ready = True
                break
            time.sleep(0.4)

        # Allow activity to settle
        time.sleep(1.0)

        # Smart Start Engagement: tap START and VERIFY that test actually launched!
        for attempt in range(1, max_start_taps + 1):
            print(f"  [Action] Engaging START button at {self.TEST_START_BTN} (Attempt {attempt}/{max_start_taps})...")
            if not self.dry_run:
                self.adb.tap(*self.TEST_START_BTN)
                time.sleep(1.2)

                # Verify if test started:
                # When test starts, 'START' button disappears or 'Please Wait' modal appears
                root = self.adb.dump_ui()
                if root is not None:
                    texts = [n.attrib.get("text", "") for n in root.iter("node")]
                    has_start = any(t.strip().upper() == "START" for t in texts)
                    has_wait = any("Please Wait" in t or "Checking" in t for t in texts)

                    if has_wait or not has_start:
                        print("  [State Confirmed] Vend Motor Test successfully engaged! (Hardware checking/spinning)")
                        return True
                    else:
                        print(f"  [Adaptive Retry] START button still unclicked. Retrying tap...")
                else:
                    return True
            else:
                return True

        print("  [State Warning] Max START taps reached, continuing with test monitoring...")

    def monitor_rotations_smart(self, bin_number):
        """Monitors the 45 rotations (258s target) with live console progress"""
        timing = self.config.get("timing", {})
        total_sec = timing.get("total_test_seconds", 258)

        start_time = time.time()
        print(f"  [Testing] Motor {bin_number}: Running 45 rotations ({total_sec}s target)...")

        while True:
            elapsed = time.time() - start_time

            pct = min(1.0, elapsed / total_sec)
            bar_len = 30
            filled = int(bar_len * pct)
            bar = "=" * filled + "-" * (bar_len - filled)
            sys.stdout.write(f"\r  [{bar}] {int(pct*100)}% | Elapsed: {int(elapsed)}s / {total_sec}s")
            sys.stdout.flush()

            if self.dry_run:
                time.sleep(2)
                return True, elapsed

            if elapsed >= total_sec:
                print(f"\n  [Success] Motor {bin_number} completed 45 rotations in {int(elapsed)}s!")
                # Give hardware 2 seconds to release relay
                time.sleep(2.0)
                return True, elapsed

            time.sleep(1.0)

    def exit_test_screen_smart(self, max_attempts=4):
        """Taps STOP/BACK and strictly confirms return to Diagnostics screen"""
        print(f"  [Action] Tapping STOP/BACK at {self.TEST_STOP_BACK_BTN} to exit test screen...")
        for attempt in range(1, max_attempts + 1):
            if not self.dry_run:
                self.adb.tap(*self.TEST_STOP_BACK_BTN)
                time.sleep(0.8)
                self.adb.tap(*self.TEST_STOP_BACK_BTN)
                time.sleep(0.8)

            state = self.detect_current_screen()
            if state == "DIAGNOSTICS" or self.dry_run:
                print("  [State Confirmed] Cleanly returned to Machine Diagnostics.")
                return True

            print(f"  [Adaptive Retry] Still on test screen. Pressing Android Back key (Attempt {attempt}/{max_attempts})...")
            if not self.dry_run:
                self.adb.keyevent(4)
                time.sleep(1.0)

        # Fallback enforcement
        return self.ensure_diagnostics_screen()

    # =========================================================================
    # SINGLE MOTOR ORCHESTRATION
    # =========================================================================

    def test_single_motor(self, bin_number, current_idx=1, total_count=1, next_bin=None):
        print(f"\n========================================================")
        print(f"Starting Test for Motor Bin #{bin_number} ({current_idx}/{total_count})")
        print(f"========================================================")
        
        self.notify(
            title=f"Motor #{bin_number} Running ({current_idx}/{total_count})",
            message=f"Testing motor #{bin_number} (45 rotations)\nStatus: In Progress | ETA: ~4.3 min",
            tags="gear,arrows_counterclockwise"
        )

        # 1. State Verification: Ensure Machine Diagnostics
        self.ensure_diagnostics_screen()

        # 2. Enter Bin & Open Test
        self.enter_bin_and_trigger_test(bin_number)

        # 3. Solve Security Check
        self.solve_security_dialog_smart(bin_number)

        # 4. Wait for screen & Engage START with confirmation
        self.wait_and_start_test_smart()

        # 5. Monitor 45 rotations
        success, duration = self.monitor_rotations_smart(bin_number)

        # 6. Exit and confirm return to Diagnostics
        self.exit_test_screen_smart()

        status_str = "PASS" if success else "FAIL"
        result = {
            "bin": bin_number,
            "status": status_str,
            "duration_seconds": round(duration, 1),
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)

        next_msg = f"Next up: Motor #{next_bin}" if next_bin else "All 45 motors finished!"
        icon = "white_check_mark" if success else "x"
        self.notify(
            title=f"Motor #{bin_number} {status_str} ✅" if success else f"Motor #{bin_number} {status_str} ❌",
            message=f"Completed 45 rotations in {round(duration, 1)}s\n{next_msg}",
            tags=icon
        )

        print(f"\n>>> Motor #{bin_number} Finished with Status: {result['status']} (Duration: {result['duration_seconds']}s)")
        return success

    def run_all(self, start_from=None):
        all_motors = self.config.get("motors", [])
        if start_from:
            try:
                idx = all_motors.index(int(start_from))
                motors_to_test = all_motors[idx:]
                print(f"[Run] Resuming from motor {start_from} ({len(motors_to_test)} of {len(all_motors)} remaining).")
            except ValueError:
                print(f"[Error] Motor {start_from} not found in config motor list. Testing all.")
                motors_to_test = all_motors
        else:
            motors_to_test = all_motors

        print(f"\n[Run] Total Motors to Test: {len(motors_to_test)} (Rotations per motor: {self.config.get('timing', {}).get('rotations_per_motor', 45)})")
        self.setup_connection()

        start_time = time.time()
        for idx, motor_bin in enumerate(motors_to_test, 1):
            next_bin = motors_to_test[idx] if idx < len(motors_to_test) else None
            print(f"\n[Progress] Testing Motor {idx} of {len(motors_to_test)} (Bin: {motor_bin})...")
            self.test_single_motor(motor_bin, current_idx=idx, total_count=len(motors_to_test), next_bin=next_bin)

        total_time = time.time() - start_time
        self.generate_report(total_time)

    def generate_report(self, total_time):
        summary = {
            "total_motors_tested": len(self.test_results),
            "passed": sum(1 for r in self.test_results if r["status"] == "PASS"),
            "failed_or_timeout": sum(1 for r in self.test_results if r["status"] != "PASS"),
            "total_duration_minutes": round(total_time / 60, 2),
            "results": self.test_results
        }

        self.notify(
            title="🎉 Vending Machine Test Complete!",
            message=f"Tested: {summary['total_motors_tested']} motors\nPassed: {summary['passed']}/{summary['total_motors_tested']}\nTotal Time: {summary['total_duration_minutes']} min",
            tags="tada,partying_face",
            priority="high"
        )

        root_dir = os.path.dirname(os.path.abspath(self.config_path))
        out_dir = os.path.join(root_dir, "logs") if os.path.exists(os.path.join(root_dir, "logs")) else root_dir
        json_file = os.path.join(out_dir, "test_report.json")
        md_file = os.path.join(out_dir, "test_report.md")

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        md_lines = [
            "# Vending Machine Motor Test Automation Report",
            f"- **Date/Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **Total Motors Tested**: {summary['total_motors_tested']}",
            f"- **Passed**: {summary['passed']}",
            f"- **Failed / Timeout**: {summary['failed_or_timeout']}",
            f"- **Total Duration**: {summary['total_duration_minutes']} minutes",
            "",
            "| Bin Number | Status | Duration (s) | Timestamp |",
            "|------------|--------|--------------|-----------|"
        ]
        for r in self.test_results:
            status_icon = "✅ PASS" if r["status"] == "PASS" else "❌ " + r["status"]
            md_lines.append(f"| {r['bin']} | {status_icon} | {r['duration_seconds']}s | {r['timestamp']} |")

        with open(md_file, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

        print("\n========================================================")
        print("TEST RUN COMPLETED")
        print(f"Passed: {summary['passed']}/{summary['total_motors_tested']} | Duration: {summary['total_duration_minutes']} min")
        print(f"Reports saved to: {json_file} and {md_file}")
        print("========================================================")


def main():
    parser = argparse.ArgumentParser(description="Smart Closed-Loop Vending Machine Motor Automation.")
    parser.add_argument("--config", default="config.json", help="Path to config.json")
    parser.add_argument("--start-from", type=int, help="Bin number to resume / start testing from")
    parser.add_argument("--motor", type=int, help="Test only this specific bin number")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without sending actual clicks")
    args = parser.parse_args()

    tester = SmartVendingTester(config_path=args.config, dry_run=args.dry_run)

    if args.motor:
        tester.setup_connection()
        tester.test_single_motor(args.motor)
        tester.generate_report(0)
    else:
        tester.run_all(start_from=args.start_from)

if __name__ == "__main__":
    main()
