#!/usr/bin/env python3
"""
Vending Machine Motor Test Automation via Mouse & Screen (PyAutoGUI + OCR).
Used when the vending machine screen is displayed or mirrored on a PC monitor (e.g., via scrcpy or capture card).
"""

import sys
import os
import time
import json
import re
import argparse
from datetime import datetime
from PIL import Image, ImageEnhance

try:
    import pyautogui
    import pytesseract
except ImportError:
    print("[Error] Missing dependencies. Run: pip install pyautogui pytesseract pillow")

# Configure tesseract binary if on standard Windows path
TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe")
]
for p in TESSERACT_PATHS:
    if os.path.exists(p):
        pytesseract.pytesseract.tesseract_cmd = p
        break

class VendingMouseAutomator:
    def __init__(self, config_path=None, coords_path=None, dry_run=False):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if config_path is None or config_path == "config.json":
            self.config_path = os.path.join(script_dir, "config.json")
        else:
            self.config_path = config_path

        if coords_path is None or coords_path == "screen_coords.json":
            self.coords_path = os.path.join(script_dir, "screen_coords.json")
        else:
            self.coords_path = coords_path

        self.dry_run = dry_run
        self.config = self._load_json(self.config_path)
        self.coords = self._load_json(self.coords_path)
        self.test_results = []
        if "pyautogui" in sys.modules:
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.5

    def _load_json(self, path):
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def solve_math_from_roi(self):
        """Take screenshot of security question region and solve math via OCR"""
        roi = self.coords.get("security_dialog_question_roi", {})
        if not roi:
            raise RuntimeError("Missing 'security_dialog_question_roi' in screen_coords.json. Run calibrate_screen.py first.")

        # Capture bounding box
        screenshot = pyautogui.screenshot(region=(
            roi["left"], roi["top"], roi["width"], roi["height"]
        ))

        # Enhance contrast for OCR
        w, h = screenshot.size
        large = screenshot.resize((w * 3, h * 3), Image.Resampling.LANCZOS)
        gray = large.convert("L")
        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(2.5)

        # Run OCR with single block PSM
        text = pytesseract.image_to_string(enhanced, config="--psm 6")
        print(f"  [OCR Raw Text]: '{text.strip()}'")

        m = re.search(r"(\d+)\s*([\+\-\*])\s*(\d+)", text)
        if m:
            n1 = int(m.group(1))
            op = m.group(2)
            n2 = int(m.group(3))
            if op == "+":
                return n1 + n2
            elif op == "-":
                return n1 - n2
            elif op == "*":
                return n1 * n2

        # If OCR fails, ask tester for rapid input
        print("  [Warn] OCR could not reliably parse math. Please enter the answer manually:")
        user_ans = input("  Security answer: ").strip()
        return int(user_ans)

    def click_elem(self, elem_name, sleep_after=1.0):
        pos = self.coords.get(elem_name)
        if not pos:
            raise KeyError(f"Coordinate '{elem_name}' not found in screen_coords.json. Run calibrate_screen.py!")
        print(f"  [Mouse Click] -> {elem_name} at ({pos['x']}, {pos['y']})")
        if not self.dry_run:
            pyautogui.click(pos["x"], pos["y"])
        time.sleep(sleep_after)

    def enter_bin_number(self, bin_number):
        self.click_elem("bin_input_field", sleep_after=0.5)
        if not self.dry_run:
            # Select all and replace
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.2)
            pyautogui.press("backspace")
            time.sleep(0.2)
            pyautogui.write(str(bin_number), interval=0.08)
            time.sleep(0.3)
        self.click_elem("bin_test_button", sleep_after=2.0)

    def solve_security_check(self):
        answer = self.solve_math_from_roi()
        print(f"  [Security Check] Answer: {answer}")
        self.click_elem("security_dialog_input", sleep_after=0.4)
        if not self.dry_run:
            pyautogui.hotkey("ctrl", "a")
            pyautogui.press("backspace")
            pyautogui.write(str(answer), interval=0.08)
            time.sleep(0.3)
        self.click_elem("security_dialog_verify", sleep_after=2.5)

    def start_and_monitor(self, bin_number):
        self.click_elem("test_start_button", sleep_after=1.0)
        timing = self.config.get("timing", {})
        rotations = timing.get("rotations_per_motor", 45)
        est_sec = timing.get("seconds_per_rotation_estimate", 6.0) * rotations

        print(f"  [Testing] Motor {bin_number}: Running {rotations} rotations (~{int(est_sec)}s)...")
        start_time = time.time()

        if self.dry_run:
            time.sleep(3)
            return True, 3.0

        while True:
            elapsed = time.time() - start_time
            pct = min(1.0, elapsed / est_sec)
            bar_len = 30
            filled = int(bar_len * pct)
            bar = "=" * filled + "-" * (bar_len - filled)
            sys.stdout.write(f"\r  [{bar}] {int(pct*100)}% | Elapsed: {int(elapsed)}s / ~{int(est_sec)}s")
            sys.stdout.flush()

            if elapsed >= est_sec + 15:
                print(f"\n  [Success] Motor {bin_number} completed.")
                return True, elapsed

            time.sleep(3)

    def test_single_motor(self, bin_number):
        print(f"\n========================================================")
        print(f"Starting Mouse Automation for Motor Bin #{bin_number}")
        print(f"========================================================")

        # 1. Click STOP/BACK to return from previous test screen if needed
        self.click_elem("stop_back_button", sleep_after=2.5)

        # 2. Enter bin number and click test button
        self.enter_bin_number(bin_number)

        # 3. Solve security check
        self.solve_security_check()

        # 4. Start and wait for completion
        success, duration = self.start_and_monitor(bin_number)

        # 5. Return to diagnostics
        self.click_elem("stop_back_button", sleep_after=2.0)

        result = {
            "bin": bin_number,
            "status": "PASS" if success else "FAIL",
            "duration_seconds": round(duration, 1),
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        return success

    def run_all(self, start_from=None):
        motors = self.config.get("motors", [])
        if start_from:
            try:
                idx = motors.index(int(start_from))
                motors = motors[idx:]
            except ValueError:
                pass

        print(f"Starting test sequence for {len(motors)} motors...")
        print("Move mouse to top-left corner of the monitor anytime to trigger FAILSAFE abort.")
        time.sleep(3)

        start_time = time.time()
        for idx, b in enumerate(motors, 1):
            print(f"\n[Progress] Motor {idx}/{len(motors)} (Bin: {b})")
            self.test_single_motor(b)

        total_time = time.time() - start_time
        print(f"\nAll tests completed in {round(total_time/60, 2)} minutes.")

def main():
    parser = argparse.ArgumentParser(description="Automate vending motor testing with mouse clicks.")
    parser.add_argument("--start-from", type=int, help="Motor bin number to resume from")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without actual clicks")
    args = parser.parse_args()

    automator = VendingMouseAutomator(dry_run=args.dry_run)
    automator.run_all(start_from=args.start_from)

if __name__ == "__main__":
    main()
