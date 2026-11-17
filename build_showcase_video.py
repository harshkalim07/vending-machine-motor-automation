import os
import subprocess
import time
import math
from PIL import Image, ImageDraw, ImageFont

v1_path = r"C:\Users\91913\.gemini\antigravity\brain\f8a19ccf-ed4b-4dfa-9954-3e5eadd4bd9d\.user_uploaded\media_1794911679549_82ab0718.mp4"
v2_path = r"C:\Users\91913\.gemini\antigravity\brain\f8a19ccf-ed4b-4dfa-9954-3e5eadd4bd9d\.user_uploaded\media_1794911686655_0117fbf9.mp4"
out_dir = r"C:\Users\91913\.gemini\antigravity\scratch\vending-machine-motor-automation\docs\video"
os.makedirs(out_dir, exist_ok=True)
final_video = os.path.join(out_dir, "vendiman_hil_linkedin_showcase.mp4")

# Parameters
FPS = 30
DURATION = 38.0  # 38 seconds (1140 frames)
TOTAL_FRAMES = int(FPS * DURATION)
W, H = 1920, 1080

# Fonts
font_title = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 26)
font_sub = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 15)
font_card = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 18)
font_big = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 36)
font_mono = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 15)
font_mono_bold = ImageFont.truetype(r"C:\Windows\Fonts\consolab.ttf", 16)
font_small = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 13)
font_badge = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 14)

print(f"Generating {TOTAL_FRAMES} frames for LinkedIn video showcase ({DURATION}s @ {FPS}fps)...")

# We will stream raw video frames from Python into ffmpeg
ffmpeg_cmd = [
    "ffmpeg", "-nostdin", "-y",
    "-f", "rawvideo",
    "-vcodec", "rawvideo",
    "-s", f"{W}x{H}",
    "-pix_fmt", "rgb24",
    "-r", str(FPS),
    "-i", "-",  # Background and telemetry stream from stdin
    "-ss", "0", "-t", str(DURATION), "-i", v1_path,  # Input 1: Terminal PowerShell
    "-ss", "0", "-t", str(DURATION), "-i", v2_path,  # Input 2: Physical Kiosk video + audio
    "-filter_complex",
    # Scale v1 terminal: crop from x=0 to avoid clipping left text, scale to 1240x350
    "[1:v]crop=2200:620:0:570,scale=1240:350[v1_scaled];"
    # Scale v2 physical kiosk to 474x800
    "[2:v]scale=474:800[v2_scaled];"
    # Overlay v1 onto base at x=65, y=605
    "[0:v][v1_scaled]overlay=65:605[tmp1];"
    # Overlay v2 onto base at x=1385, y=150
    "[tmp1][v2_scaled]overlay=1385:150[outv];"
    # Audio: apply 1.5s fade-in and 1.5s fade-out to natural kiosk audio
    f"[2:a]afade=t=in:ss=0:d=1.5,afade=t=out:st={DURATION-1.5}:d=1.5[outa]",
    "-map", "[outv]",
    "-map", "[outa]",
    "-c:v", "libx264",
    "-preset", "fast",
    "-crf", "18",
    "-c:a", "aac",
    "-b:a", "192k",
    final_video
]

log_file = os.path.join(out_dir, "ffmpeg_render.log")
log_f = open(log_file, "w", encoding="utf-8")

proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=log_f)

start_time = time.time()

# Pre-render static base elements for maximum speed
base_img = Image.new("RGB", (W, H), (15, 23, 42))  # slate-900
d_base = ImageDraw.Draw(base_img)

# 1. Top Header Bar
d_base.rectangle([(0, 0), (W, 85)], fill=(9, 14, 26))
d_base.line([(0, 85), (W, 85)], fill=(249, 115, 22), width=3)  # Orange accent

# Title & Subtitle
d_base.text((45, 18), "AUTONOMOUS ANDROID IOT VENDING QA BENCH", fill=(255, 255, 255), font=font_title)
d_base.text((45, 52), "Hardware-in-the-Loop (HIL) Stress Testing & Dynamic Security Solving  •  Vendiman Pvt Ltd", fill=(148, 163, 184), font=font_sub)

# Badges on Header Right
badges = [
    ("CONNECTED: 124.20.12.15:5555", (34, 197, 94), (20, 83, 45)),
    ("MATH SOLVER: < 10ms", (249, 115, 22), (124, 45, 18)),
    ("45 MOTORS (2,025 ROTS)", (59, 130, 246), (30, 58, 138)),
]
bx = W - 40
for b_text, text_col, bg_col in reversed(badges):
    bw = len(b_text) * 8 + 24
    bx -= bw + 15
    d_base.rounded_rectangle([(bx, 24), (bx + bw, 62)], radius=8, fill=bg_col, outline=text_col, width=1)
    d_base.text((bx + 12, 33), b_text, fill=text_col, font=font_badge)

# 2. Left Panel: Outer Container
d_base.rounded_rectangle([(35, 100), (1335, 980)], radius=16, fill=(15, 23, 42), outline=(51, 65, 85), width=2)

# Left Top: Telemetry Card Container
d_base.rounded_rectangle([(50, 115), (1320, 535)], radius=14, fill=(24, 33, 54), outline=(71, 85, 105), width=1)
d_base.text((70, 130), "LIVE TEST TELEMETRY  •  DESKTOP QA BENCH", fill=(249, 115, 22), font=font_card)

# Left Bottom: Controller Terminal Container
d_base.rounded_rectangle([(50, 550), (1320, 965)], radius=14, fill=(10, 15, 28), outline=(71, 85, 105), width=1)
d_base.text((70, 563), "ADB CONTROLLER CONSOLE  •  EVENT DISPATCHER & IN-MEMORY MATH SOLVER", fill=(148, 163, 184), font=font_card)

# 3. Right Panel: Physical Kiosk Container
d_base.rounded_rectangle([(1360, 100), (1885, 980)], radius=16, fill=(24, 33, 54), outline=(249, 115, 22), width=2)
d_base.text((1380, 120), "LIVE KIOSK HARDWARE  •  HIL FEED", fill=(255, 255, 255), font=font_card)

# 4. Bottom Footer Bar
d_base.rectangle([(0, 995), (W, H)], fill=(9, 14, 26))
d_base.line([(0, 995), (W, 995)], fill=(51, 65, 85), width=2)
d_base.text((45, 1015), "QA Time: 4 Hours -> 100% Hands-Free  •  Automated Red Cross Jam Detection  •  Python • Android ADB • Flask SSE  •  Harsh Kalim", fill=(203, 213, 225), font=font_sub)

# Metric Boxes Template in Telemetry Card
metrics = [
    ("TOTAL MOTORS", "45", (148, 163, 184)),
    ("PASSED", "9", (34, 197, 94)),
    ("JAMMED / FAILED", "0", (239, 68, 68)),
    ("PENDING", "36", (249, 115, 22))
]

print("Streaming composite frames...")

for i in range(TOTAL_FRAMES):
    t = i / FPS
    frame = base_img.copy()
    draw = ImageDraw.Draw(frame)

    # State evolution across the 38 seconds
    if t < 7.5:
        # Motor 600 Finishing
        active_motor = "600"
        rot_curr, rot_target = 45, 45
        elapsed_sec = int(250 + t)
        status_text = "COMPLETING 45 ROTATIONS"
        status_col = (34, 197, 94)
        pct = 1.0
    elif t < 12.0:
        # Transition & Selecting Motor 601
        active_motor = "601"
        rot_curr, rot_target = 0, 45
        elapsed_sec = 0
        status_text = "INITIALIZING MOTOR #601"
        status_col = (249, 115, 22)
        pct = 0.0
    elif t < 22.0:
        # Solving Security Challenge
        active_motor = "601"
        rot_curr, rot_target = 0, 45
        elapsed_sec = int(t - 12.0)
        status_text = "SOLVING SECURITY CHALLENGE (< 10ms)"
        status_col = (250, 204, 21)
        pct = 0.0
    else:
        # Motor 601 Spinning
        active_motor = "601"
        elapsed_sec = int(t - 22.0)
        rot_curr = min(45, max(1, int((t - 22.0) / 5.7)))
        rot_target = 45
        status_text = "ACTIVE TEST IN PROGRESS"
        status_col = (34, 197, 94)
        pct = rot_curr / 45.0

    # Draw Telemetry Contents
    # Status Tag
    draw.rounded_rectangle([(970, 124), (1305, 156)], radius=6, fill=(30, 41, 59), outline=status_col, width=1)
    draw.text((985, 131), status_text, fill=status_col, font=font_small)

    # Motor Card Inner Box (x: 75, y: 175, w: 1220, h: 180)
    draw.rounded_rectangle([(75, 175), (1295, 360)], radius=12, fill=(15, 23, 42), outline=(51, 65, 85), width=1)

    # Spinning Rotor Indicator
    # Rotate an icon or circle with angle
    angle = (t * 360) % 360
    cx, cy = 135, 245
    draw.ellipse([(cx-35, cy-35), (cx+35, cy+35)], fill=(30, 41, 59), outline=(249, 115, 22), width=3)
    rad = math.radians(angle)
    ex = cx + int(24 * math.cos(rad))
    ey = cy + int(24 * math.sin(rad))
    draw.line([(cx, cy), (ex, ey)], fill=(255, 255, 255), width=3)
    draw.ellipse([(cx-6, cy-6), (cx+6, cy+6)], fill=(249, 115, 22))

    # Motor Labels
    draw.text((195, 200), "ACTIVE MOTOR UNDER TEST", fill=(148, 163, 184), font=font_sub)
    draw.text((195, 230), f"#{active_motor}", fill=(255, 255, 255), font=font_big)

    # Rotation Counter
    draw.text((1050, 200), "ROTATION PROGRESS", fill=(148, 163, 184), font=font_sub)
    draw.text((1050, 230), f"{rot_curr} / {rot_target}", fill=(249, 115, 22), font=font_big)

    # Progress Bar Track
    bar_x, bar_y, bar_w, bar_h = 95, 295, 1180, 14
    draw.rounded_rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h)], radius=7, fill=(30, 41, 59))
    fill_w = max(14, int(bar_w * pct))
    draw.rounded_rectangle([(bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h)], radius=7, fill=(249, 115, 22))

    # Progress Details
    draw.text((95, 320), f"Elapsed: {elapsed_sec}s ({int(pct*100)}%)", fill=(148, 163, 184), font=font_small)
    draw.text((1070, 320), "Target: ~258s (45 Rotations)", fill=(148, 163, 184), font=font_small)

    # 4 Metric Boxes (y: 385 to 515)
    mb_w = 280
    mb_gap = 25
    start_mx = 75
    for idx, (label, val, val_col) in enumerate(metrics):
        cur_x = start_mx + idx * (mb_w + mb_gap)
        draw.rounded_rectangle([(cur_x, 385), (cur_x + mb_w, 515)], radius=10, fill=(15, 23, 42), outline=(51, 65, 85), width=1)
        draw.text((cur_x + 20, 400), label, fill=(148, 163, 184), font=font_small)
        # Update passed count dynamically after motor 600 completes
        display_val = val
        if label == "PASSED" and t >= 7.5:
            display_val = "10"
        elif label == "PENDING" and t >= 7.5:
            display_val = "35"
        draw.text((cur_x + 20, 440), display_val, fill=val_col, font=font_big)

    # Callout Banners at Key Moments (positioned perfectly between y: 545 and y: 595)
    if 12.0 <= t <= 19.5:
        # Dynamic Math Challenge Banner
        draw.rounded_rectangle([(70, 546), (1300, 596)], radius=8, fill=(124, 45, 18), outline=(249, 115, 22), width=2)
        draw.text((100, 559), "[CHALLENGE SOLVED]  IN-MEMORY ARITHMETIC: '21 + 45 = 66'  (< 10ms - NO OCR LAG)", fill=(255, 255, 255), font=font_mono_bold)

    elif 23.0 <= t <= 32.0:
        # START Button Engagement Banner
        draw.rounded_rectangle([(70, 546), (1300, 596)], radius=8, fill=(20, 83, 45), outline=(34, 197, 94), width=2)
        draw.text((100, 559), "[HARDWARE ENGAGED]  START COMMAND SUBMITTED VIA ADB  -  MOTOR #601 ACTIVE", fill=(255, 255, 255), font=font_mono_bold)

    elif t >= 33.0:
        # Final Outro Banner
        draw.rounded_rectangle([(70, 546), (1300, 596)], radius=8, fill=(30, 58, 138), outline=(59, 130, 246), width=2)
        draw.text((100, 559), "[QA RESULT]  100% HANDS-FREE HIL EXECUTION  •  45 MOTORS  •  ZERO FIELD JAMS", fill=(255, 255, 255), font=font_mono_bold)

    # Write raw bytes to ffmpeg stdin
    proc.stdin.write(frame.tobytes())

    if i % 150 == 0:
        elapsed = time.time() - start_time
        print(f"Rendered frame {i}/{TOTAL_FRAMES} ({(i/TOTAL_FRAMES)*100:.1f}%) in {elapsed:.1f}s")

proc.stdin.close()
proc.wait()
log_f.close()

if proc.returncode != 0:
    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
        print("FFmpeg Error:\n", f.read()[-1000:])
else:
    print(f"✅ Master showcase video generated successfully: {final_video}")
