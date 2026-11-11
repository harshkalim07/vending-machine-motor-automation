#!/usr/bin/env python3
"""
Interactive Screen Calibration Tool for Vending Machine Mouse Automation.
Hover your mouse over the requested UI element on your screen and press Enter to capture coordinates.
"""

import sys
import time
import json
import os

try:
    import pyautogui
except ImportError:
    print("[Error] pyautogui is required for screen calibration. Run: pip install pyautogui")
    sys.exit(1)

ELEMENTS_TO_CALIBRATE = [
    ("stop_back_button", "The red 'STOP/BACK' button at the bottom of the screen"),
    ("bin_input_field", "The text input box for Bin number (next to 'Bin + Motor Multiple Time Vend Test')"),
    ("bin_test_button", "The red 'Bin + Motor Multiple Time Vend Test' button"),
    ("security_dialog_input", "The text input field inside the 'Security Check' dialog popup"),
    ("security_dialog_verify", "The orange/red 'VERIFY' button in the 'Security Check' dialog"),
    ("security_dialog_question_roi", "Top-left and Bottom-right of math question (e.g. 'What is 25+ 38?')"),
    ("test_start_button", "The red 'START' button at the bottom left of the motor test screen"),
]

def calibrate():
    print("=" * 65)
    print("VENDING MACHINE MOUSE AUTOMATION - CALIBRATION WIZARD")
    print("=" * 65)
    print("Open the vending machine screen (or scrcpy window) on your monitor.")
    print("For each element, move your mouse over it and press ENTER in this terminal.\n")

    coords = {}

    for key, description in ELEMENTS_TO_CALIBRATE:
        if key == "security_dialog_question_roi":
            print(f"\nTarget: {description}")
            input("  1. Move mouse to TOP-LEFT corner of the question text and press ENTER...")
            p1 = pyautogui.position()
            print(f"     Recorded Top-Left: ({p1.x}, {p1.y})")
            input("  2. Move mouse to BOTTOM-RIGHT corner of the question text and press ENTER...")
            p2 = pyautogui.position()
            print(f"     Recorded Bottom-Right: ({p2.x}, {p2.y})")
            coords[key] = {
                "left": min(p1.x, p2.x),
                "top": min(p1.y, p2.y),
                "width": abs(p2.x - p1.x),
                "height": abs(p2.y - p1.y)
            }
        else:
            print(f"\nTarget: {description}")
            input("  Move mouse over the element and press ENTER...")
            pos = pyautogui.position()
            coords[key] = {"x": pos.x, "y": pos.y}
            print(f"  --> Saved: {key} = ({pos.x}, {pos.y})")

    out_file = "screen_coords.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(coords, f, indent=2)

    print("\n" + "=" * 65)
    print(f"Calibration complete! Coordinates saved to '{out_file}'.")
    print("You can now run: python vending_mouse_automator.py")
    print("=" * 65)

if __name__ == "__main__":
    calibrate()
