import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1920, 1080
canvas = Image.new("RGB", (W, H), (9, 14, 26))
draw = ImageDraw.Draw(canvas)

# Fonts
font_huge = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 52)
font_big = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 34)
font_mid = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 22)
font_pill = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 16)
font_sub = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 18)
font_mono = ImageFont.truetype(r"C:\Windows\Fonts\consolab.ttf", 20)

# Paths
art_dir = r"C:\Users\91913\.gemini\antigravity\scratch\vending-machine-motor-automation\docs\screenshots"
v2_crop_path = r"C:\Users\91913\.gemini\antigravity\brain\f8a19ccf-ed4b-4dfa-9954-3e5eadd4bd9d\v2_frame15.png"
v2_complete_path = r"C:\Users\91913\.gemini\antigravity\brain\f8a19ccf-ed4b-4dfa-9954-3e5eadd4bd9d\v2_frame5.png"
dash_path = os.path.join(art_dir, "dashboard_dark.png")
telemetry_path = os.path.join(art_dir, "telemetry_active_dark.png")

# --- 1. Top Section ---
# Ambient top glow
for r in range(120, 0, -10):
    alpha = int((120 - r) * 0.4)
    # subtle orange glow at top center
    draw.rectangle([(0, 0), (W, 140)], fill=(15 + alpha//4, 23 + alpha//6, 42))

# Top pill badge
badge_w, badge_h = 440, 34
bx = (W - badge_w) // 2
draw.rounded_rectangle([(bx, 20), (bx + badge_w, 54)], radius=17, fill=(30, 41, 59), outline=(249, 115, 22), width=2)
draw.text((bx + 26, 26), "ENTERPRISE IOT  •  HARDWARE-IN-THE-LOOP", fill=(249, 115, 22), font=font_pill)

# Main Title (Bold, High Contrast)
title_text = "AUTONOMOUS VENDING MACHINE MOTOR QA"
title_w = int(draw.textlength(title_text, font=font_huge))
draw.text(((W - title_w) // 2, 62), title_text, fill=(255, 255, 255), font=font_huge)

# The "Before vs After" Impact Banner
comp_text_before = "MANUAL QA: 4 HOURS"
comp_text_after = "AUTONOMOUS: 100% HANDS-FREE"

banner_w = 920
banner_h = 44
ban_x = (W - banner_w) // 2
ban_y = 132
draw.rounded_rectangle([(ban_x, ban_y), (ban_x + banner_w, ban_y + banner_h)], radius=22, fill=(15, 23, 42), outline=(51, 65, 85), width=2)

# Red left pill
draw.rounded_rectangle([(ban_x + 6, ban_y + 4), (ban_x + 390, ban_y + banner_h - 4)], radius=18, fill=(127, 29, 29))
draw.text((ban_x + 40, ban_y + 10), "BEFORE:  4-HOUR MANUAL QA", fill=(254, 202, 202), font=font_pill)

# Arrow
draw.text((ban_x + 412, ban_y + 10), "==>", fill=(249, 115, 22), font=font_mono)

# Green right pill
draw.rounded_rectangle([(ban_x + 460, ban_y + 4), (ban_x + banner_w - 6, ban_y + banner_h - 4)], radius=18, fill=(20, 83, 45))
draw.text((ban_x + 485, ban_y + 10), "AFTER:  100% HANDS-FREE WI-FI ADB", fill=(187, 247, 208), font=font_pill)


# --- 2. Center Split Images ---
# Left Card: Desktop Web QA Bench (x: 50 to 1080 -> width 1030)
left_card_x, left_card_y, left_card_w, left_card_h = 60, 195, 1030, 755
draw.rounded_rectangle([(left_card_x, left_card_y), (left_card_x + left_card_w, left_card_y + left_card_h)], radius=18, fill=(15, 23, 42), outline=(51, 65, 85), width=2)

# Left Header
draw.rounded_rectangle([(left_card_x, left_card_y), (left_card_x + left_card_w, left_card_y + 55)], radius=18, fill=(30, 41, 59))
draw.rectangle([(left_card_x, left_card_y + 35), (left_card_x + left_card_w, left_card_y + 55)], fill=(30, 41, 59))
draw.text((left_card_x + 25, left_card_y + 14), "VENDIMAN QA BENCH  •  DESKTOP WEB CONTROLLER", fill=(249, 115, 22), font=font_mid)

# Paste cropped dashboard into Left Card
im_dash = Image.open(dash_path)
dash_crop = im_dash.crop((50, 100, 1550, 950))
dash_crop = dash_crop.resize((990, 600), Image.Resampling.LANCZOS)
canvas.paste(dash_crop, (left_card_x + 20, left_card_y + 65))

# Floating highlight pill on Left Card
pill_text = "Real-Time SSE Telemetry  •  45-Motor Matrix  •  1-Click Automated Execution"
draw.rounded_rectangle([(left_card_x + 30, left_card_y + 685), (left_card_x + left_card_w - 30, left_card_y + 735)], radius=12, fill=(24, 33, 54), outline=(249, 115, 22), width=1)
draw.text((left_card_x + 160, left_card_y + 697), pill_text, fill=(255, 255, 255), font=font_pill)


# Right Card: Physical Kiosk Hardware (x: 1120 to 1860 -> width 740)
right_card_x, right_card_y, right_card_w, right_card_h = 1120, 195, 740, 755
draw.rounded_rectangle([(right_card_x, right_card_y), (right_card_x + right_card_w, right_card_y + right_card_h)], radius=18, fill=(15, 23, 42), outline=(249, 115, 22), width=3)

# Right Header
draw.rounded_rectangle([(right_card_x, right_card_y), (right_card_x + right_card_w, right_card_y + 55)], radius=18, fill=(124, 45, 18))
draw.rectangle([(right_card_x, right_card_y + 35), (right_card_x + right_card_w, right_card_y + 55)], fill=(124, 45, 18))
draw.text((right_card_x + 25, right_card_y + 14), "PHYSICAL VENDING MACHINE  •  LIVE HARDWARE FEED", fill=(255, 255, 255), font=font_mid)

# Paste Physical Screen Crop into Right Card
im_kiosk = Image.open(v2_crop_path)
kiosk_w, kiosk_h = im_kiosk.size
kiosk_crop = im_kiosk.crop((0, 80, kiosk_w, kiosk_h - 120))
kiosk_crop = kiosk_crop.resize((700, 600), Image.Resampling.LANCZOS)
canvas.paste(kiosk_crop, (right_card_x + 20, right_card_y + 65))

# Floating highlight badge over kiosk image
badge_challenge_y = right_card_y + 685
draw.rounded_rectangle([(right_card_x + 30, badge_challenge_y), (right_card_x + right_card_w - 30, badge_challenge_y + 50)], radius=12, fill=(20, 83, 45), outline=(34, 197, 94), width=2)
draw.text((right_card_x + 95, badge_challenge_y + 13), "IN-MEMORY MATH SOLVER: '21 + 45 = 66' (< 10ms)", fill=(255, 255, 255), font=font_pill)


# --- 3. Bottom Feature Bar ---
footer_y = 970
draw.rectangle([(0, footer_y), (W, H)], fill=(9, 14, 26))
draw.line([(0, footer_y), (W, footer_y)], fill=(51, 65, 85), width=2)

features = [
    ("Wi-Fi ADB Wireless", (34, 197, 94)),
    ("< 10ms In-Memory Solver", (249, 115, 22)),
    ("2,025 Continuous Rotations", (59, 130, 246)),
    ("Red Cross Jam Detection", (239, 68, 68)),
    ("Auto Markdown/JSON Reports", (168, 85, 247))
]

fx = 60
for feat, fcol in features:
    fw = len(feat) * 9 + 25
    draw.rounded_rectangle([(fx, footer_y + 20), (fx + fw, footer_y + 62)], radius=10, fill=(24, 33, 54), outline=fcol, width=1)
    draw.text((fx + 12, footer_y + 28), feat, fill=fcol, font=font_pill)
    fx += fw + 18

# Author watermark on bottom right
draw.text((W - 360, footer_y + 30), "HARSH KALIM • VENDIMAN PVT LTD", fill=(148, 163, 184), font=font_pill)

# Save thumbnail
out_png = os.path.join(r"C:\Users\91913\.gemini\antigravity\scratch\vending-machine-motor-automation\docs\screenshots", "linkedin_video_thumbnail.png")
canvas.save(out_png, quality=95)

# Also save into brain artifact folder
art_png = r"C:\Users\91913\.gemini\antigravity\brain\f8a19ccf-ed4b-4dfa-9954-3e5eadd4bd9d\linkedin_video_thumbnail.png"
canvas.save(art_png, quality=95)

print("Master Thumbnail generated successfully:", out_png)
