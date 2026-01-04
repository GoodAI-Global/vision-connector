#!/usr/bin/env python3
"""
Generate sample images for vision-connector testing.

Creates synthetic HMI screen, analog gauge, and digital display images
that can be used for testing the vision capture library.
"""

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def get_font(size: int = 24):
    """Get a font, falling back to default if specific fonts not available."""
    # Try common monospace fonts
    font_names = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/UbuntuMono-B.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "C:\\Windows\\Fonts\\consola.ttf",
    ]

    for font_path in font_names:
        try:
            return ImageFont.truetype(font_path, size)
        except (OSError, IOError):
            continue

    # Fall back to default
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def create_hmi_screen(output_path: Path) -> dict:
    """
    Create a sample HMI screen image.

    Returns region coordinates for the values.
    """
    width, height = 640, 480
    img = Image.new("RGB", (width, height), color=(40, 44, 52))
    draw = ImageDraw.Draw(img)

    # Colors
    bg_dark = (30, 34, 42)
    text_white = (255, 255, 255)
    text_green = (0, 255, 100)
    text_yellow = (255, 200, 0)
    accent_blue = (70, 130, 180)

    # Title bar
    draw.rectangle([0, 0, width, 50], fill=accent_blue)
    title_font = get_font(28)
    draw.text((20, 10), "PLANT MONITOR - LINE 1", fill=text_white, font=title_font)

    # Status indicator
    draw.text((width - 120, 15), "RUNNING", fill=text_green, font=get_font(20))

    # Main panel background
    draw.rectangle([20, 70, width - 20, height - 20], fill=bg_dark, outline=(80, 80, 80))

    # Define regions and values
    regions = {}
    label_font = get_font(18)
    value_font = get_font(32)

    # Temperature
    label_y = 100
    value_y = 130
    draw.text((40, label_y), "TEMPERATURE", fill=(150, 150, 150), font=label_font)
    temp_x, temp_y = 40, value_y
    draw.text((temp_x, temp_y), "185.5", fill=text_green, font=value_font)
    draw.text((140, value_y + 5), "°C", fill=(150, 150, 150), font=get_font(20))
    regions["temperature"] = {"x": temp_x, "y": temp_y, "w": 95, "h": 40, "type": "number"}

    # Pressure
    label_y = 200
    value_y = 230
    draw.text((40, label_y), "PRESSURE", fill=(150, 150, 150), font=label_font)
    pres_x, pres_y = 40, value_y
    draw.text((pres_x, pres_y), "42.3", fill=text_green, font=value_font)
    draw.text((120, value_y + 5), "PSI", fill=(150, 150, 150), font=get_font(20))
    regions["pressure"] = {"x": pres_x, "y": pres_y, "w": 80, "h": 40, "type": "number"}

    # Flow Rate
    label_y = 300
    value_y = 330
    draw.text((40, label_y), "FLOW RATE", fill=(150, 150, 150), font=label_font)
    flow_x, flow_y = 40, value_y
    draw.text((flow_x, flow_y), "127.8", fill=text_yellow, font=value_font)
    draw.text((145, value_y + 5), "L/min", fill=(150, 150, 150), font=get_font(20))
    regions["flow_rate"] = {"x": flow_x, "y": flow_y, "w": 105, "h": 40, "type": "number"}

    # Status panel on right side
    draw.rectangle([320, 100, 600, 200], fill=(50, 54, 62), outline=(80, 80, 80))
    draw.text((340, 110), "SYSTEM STATUS", fill=(150, 150, 150), font=label_font)
    status_x, status_y = 340, 145
    draw.text((status_x, status_y), "RUNNING", fill=text_green, font=value_font)
    regions["status"] = {"x": status_x, "y": status_y, "w": 140, "h": 40, "type": "text"}

    # Alarm panel
    draw.rectangle([320, 220, 600, 320], fill=(50, 54, 62), outline=(80, 80, 80))
    draw.text((340, 230), "ACTIVE ALARMS", fill=(150, 150, 150), font=label_font)
    alarm_x, alarm_y = 340, 270
    draw.text((alarm_x, alarm_y), "NONE", fill=text_green, font=value_font)
    regions["alarms"] = {"x": alarm_x, "y": alarm_y, "w": 90, "h": 40, "type": "text"}

    # Production counter
    draw.rectangle([320, 340, 600, 440], fill=(50, 54, 62), outline=(80, 80, 80))
    draw.text((340, 350), "UNITS PRODUCED", fill=(150, 150, 150), font=label_font)
    count_x, count_y = 340, 385
    draw.text((count_x, count_y), "1247", fill=text_white, font=value_font)
    regions["units_produced"] = {"x": count_x, "y": count_y, "w": 85, "h": 40, "type": "number"}

    # Save image
    img.save(output_path)

    return regions


def create_analog_gauge(output_path: Path) -> dict:
    """
    Create a sample analog gauge image.

    Returns gauge parameters.
    """
    size = 400
    img = Image.new("RGB", (size, size), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)

    center = size // 2
    radius = 160

    # Draw gauge background (circle)
    draw.ellipse(
        [center - radius, center - radius, center + radius, center + radius],
        fill=(255, 255, 255),
        outline=(100, 100, 100),
        width=3,
    )

    # Draw tick marks and labels
    min_angle = 225  # 7 o'clock position (0 value)
    max_angle = -45  # 5 o'clock position (100 value)
    angle_range = min_angle - max_angle  # 270 degrees

    font = get_font(16)

    for i in range(11):
        # Calculate angle for this tick
        ratio = i / 10
        angle_deg = min_angle - ratio * angle_range
        angle_rad = math.radians(angle_deg)

        # Tick positions
        inner_r = radius - 20
        outer_r = radius - 5

        x1 = center + inner_r * math.cos(angle_rad)
        y1 = center - inner_r * math.sin(angle_rad)
        x2 = center + outer_r * math.cos(angle_rad)
        y2 = center - outer_r * math.sin(angle_rad)

        # Draw tick
        draw.line([(x1, y1), (x2, y2)], fill=(50, 50, 50), width=2)

        # Draw label
        label = str(i * 10)
        label_r = radius - 40

        lx = center + label_r * math.cos(angle_rad)
        ly = center - label_r * math.sin(angle_rad)

        # Approximate text centering
        draw.text((lx - 10, ly - 8), label, fill=(50, 50, 50), font=font)

    # Draw needle pointing to ~67.5
    needle_value = 67.5
    needle_ratio = needle_value / 100
    needle_angle_deg = min_angle - needle_ratio * angle_range
    needle_angle_rad = math.radians(needle_angle_deg)

    needle_length = radius - 30
    needle_x = center + needle_length * math.cos(needle_angle_rad)
    needle_y = center - needle_length * math.sin(needle_angle_rad)

    # Draw needle (thick line)
    draw.line([(center, center), (needle_x, needle_y)], fill=(200, 0, 0), width=4)

    # Draw center cap
    draw.ellipse(
        [center - 10, center - 10, center + 10, center + 10],
        fill=(100, 100, 100),
    )

    # Draw unit label
    unit_font = get_font(20)
    draw.text((center - 20, center + 50), "PSI", fill=(50, 50, 50), font=unit_font)

    # Save image
    img.save(output_path)

    return {
        "min_value": 0,
        "max_value": 100,
        "expected_value": 67.5,
        "unit": "PSI",
    }


def create_digital_display(output_path: Path) -> dict:
    """
    Create a sample 7-segment style digital display image.

    Returns display parameters.
    """
    width, height = 300, 100
    img = Image.new("RGB", (width, height), color=(20, 20, 20))
    draw = ImageDraw.Draw(img)

    # Draw display background
    draw.rectangle([10, 10, width - 10, height - 10], fill=(5, 5, 5), outline=(60, 60, 60))

    # Draw the number in red (simulating LED display)
    display_font = get_font(60)
    text = "1234.5"

    # Red LED color
    led_red = (255, 50, 50)

    # Calculate text position to center it
    draw.text((30, 15), text, fill=led_red, font=display_font)

    # Save image
    img.save(output_path)

    return {
        "expected_value": 1234.5,
        "region": {"x": 20, "y": 10, "w": 260, "h": 80},
    }


def main():
    """Generate all sample images."""
    # Ensure output directory exists
    output_dir = Path(__file__).parent.parent / "sample_images"
    output_dir.mkdir(exist_ok=True)

    print("Generating sample images...")

    # Generate HMI screen
    hmi_path = output_dir / "hmi_screen.png"
    hmi_regions = create_hmi_screen(hmi_path)
    print(f"Created: {hmi_path}")
    print(f"  Regions: {list(hmi_regions.keys())}")

    # Generate analog gauge
    gauge_path = output_dir / "analog_gauge.png"
    gauge_params = create_analog_gauge(gauge_path)
    print(f"Created: {gauge_path}")
    print(f"  Expected value: {gauge_params['expected_value']} {gauge_params['unit']}")

    # Generate digital display
    display_path = output_dir / "digital_display.png"
    display_params = create_digital_display(display_path)
    print(f"Created: {display_path}")
    print(f"  Expected value: {display_params['expected_value']}")

    print("\nSample images generated successfully!")

    # Return region info for config file
    return hmi_regions


if __name__ == "__main__":
    main()
