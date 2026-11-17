import os
import subprocess
import time
import json
import urllib.request
import websocket
import base64
from PIL import Image

out_dir = r"C:\Users\91913\.gemini\antigravity\scratch\vending-machine-motor-automation\docs\screenshots"
os.makedirs(out_dir, exist_ok=True)

edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
temp_dir = r"C:\Users\91913\AppData\Local\Temp\cdp_capture_suite"

proc = subprocess.Popen([
    edge_path,
    "--headless=new",
    "--no-sandbox",
    f"--user-data-dir={temp_dir}",
    "--remote-debugging-port=9222",
    "--window-size=1600,1050",
    "http://127.0.0.1:5000"
])

try:
    time.sleep(3)
    resp = urllib.request.urlopen("http://127.0.0.1:9222/json").read()
    targets = json.loads(resp)
    ws_url = None
    for t in targets:
        if t.get("type") == "page":
            ws_url = t.get("webSocketDebuggerUrl")
            break
    print("WS Connected:", ws_url)
    ws = websocket.create_connection(ws_url)

    def eval_js(code):
        ws.send(json.dumps({"id": 10, "method": "Runtime.evaluate", "params": {"expression": code}}))
        return ws.recv()

    def snap(filename):
        ws.send(json.dumps({"id": 20, "method": "Page.captureScreenshot", "params": {"format": "png"}}))
        res = json.loads(ws.recv())
        data = base64.b64decode(res["result"]["data"])
        filepath = os.path.join(out_dir, filename)
        with open(filepath, "wb") as f:
            f.write(data)
        print(f"Captured: {filename} ({len(data)} bytes)")
        return filepath

    time.sleep(2)

    # 1. Dark Mode Dashboard
    eval_js("applyTheme('dark');")
    time.sleep(1)
    dark_path = snap("dashboard_dark.png")

    # 2. Light Mode Dashboard
    eval_js("applyTheme('light');")
    time.sleep(1)
    light_path = snap("dashboard_light.png")

    # 3. Motor Matrix Grid (scrolled view in Dark Mode with dark tiles styled)
    eval_js("applyTheme('dark');")
    eval_js("""
        document.querySelectorAll('.motor-tile').forEach(t => {
            if (!t.className.includes('bg-emerald') && !t.className.includes('bg-amber')) {
                t.style.backgroundColor = '#1e293b';
                t.style.borderColor = '#334155';
            }
        });
        window.scrollTo(0, 480);
    """)
    time.sleep(1)
    grid_path = snap("motor_matrix_grid.png")

    # 4. Activity Stream Terminal (scrolled to bottom)
    eval_js("window.scrollTo(0, 1100);")
    time.sleep(1)
    terminal_path = snap("live_terminal_stream.png")

    # Reset scroll
    eval_js("window.scrollTo(0, 0);")
    time.sleep(0.5)

    # 4. Generate high-res crops from Dark Mode
    im_dark = Image.open(dark_path)
    telemetry_crop = im_dark.crop((695, 175, 1420, 545))
    telemetry_crop.save(os.path.join(out_dir, "telemetry_active_dark.png"))
    print("Saved telemetry_active_dark.png")

    exec_crop = im_dark.crop((180, 175, 680, 730))
    exec_crop.save(os.path.join(out_dir, "execution_controls_dark.png"))
    print("Saved execution_controls_dark.png")

    # 5. Generate high-res crops from Light Mode
    im_light = Image.open(light_path)
    telemetry_crop_light = im_light.crop((695, 175, 1420, 545))
    telemetry_crop_light.save(os.path.join(out_dir, "telemetry_active_light.png"))
    print("Saved telemetry_active_light.png")

    ws.close()
    print("All captures completed successfully!")
finally:
    proc.terminate()
