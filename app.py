#!/usr/bin/env python3
"""
Vendiman Motor QA Bench - Web Dashboard Application
Professional White + Orange Theme Edition
Engineered for hardware QA testers to run 45-motor stress tests with:
- Zero CLI / terminal setup
- Universal screen awareness (auto-navigates from Launcher/Tray-1/QR/OTP/Menu into Diagnostics)
- Exact bin typing
- 1-Click Open Diagnostics Only mode
- Live 45-motor visual telemetry matrix
- Web audio synthesizer alert on Red Cross jams
- Graceful hardware-aware stop controls
"""

import os
import sys
import json
import time
import threading
import webbrowser
from flask import Flask, render_template, request, jsonify, send_file
from automation_engine import AutomationEngine, ALL_MOTORS

app = Flask(__name__)
engine = AutomationEngine()

def open_browser():
    # Poll until server is actively responding before launching browser
    import urllib.request
    for _ in range(20):
        time.sleep(0.5)
        try:
            with urllib.request.urlopen("http://127.0.0.1:5000", timeout=1) as resp:
                if resp.status == 200:
                    break
        except Exception:
            continue
    try:
        webbrowser.open("http://127.0.0.1:5000")
    except Exception:
        pass

@app.route("/")
def index():
    return render_template("index.html", motors=ALL_MOTORS, target=engine.target)

@app.route("/api/status", methods=["GET"])
def get_status():
    return jsonify(engine.get_state())

@app.route("/api/connect", methods=["POST"])
def connect_device():
    success = engine.check_connection()
    return jsonify({"connected": success, "target": engine.target})

@app.route("/api/detect-screen", methods=["POST"])
def detect_screen():
    screen = engine.detect_screen()
    return jsonify({"screen": screen})

@app.route("/api/start", methods=["POST"])
def start_test():
    data = request.get_json() or {}
    mode = data.get("mode", "all")
    start_bin = data.get("start_bin", 100)
    try:
        start_bin = int(start_bin)
    except ValueError:
        start_bin = 100

    success, msg = engine.start(mode=mode, start_bin=start_bin)
    return jsonify({"success": success, "message": msg})

@app.route("/api/stop", methods=["POST"])
def stop_test():
    engine.request_stop()
    return jsonify({
        "success": True, 
        "message": "Stop requested. The active 45-rotation cycle will complete before halting."
    })

@app.route("/api/reset", methods=["POST"])
def reset_grid():
    engine.reset_grid()
    return jsonify({"success": True})

@app.route("/api/report", methods=["GET"])
def get_report():
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "test_report.json")
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify({"status": "No report generated yet."})

if __name__ == "__main__":
    print("=" * 65)
    print("  🚀 VENDIMAN MOTOR QA BENCH DASHBOARD (PROFESSIONAL EDITION)")
    print("  🌐 Server running locally on: http://127.0.0.1:5000")
    print("  📱 Opening dashboard in your default web browser...")
    print("=" * 65)
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
