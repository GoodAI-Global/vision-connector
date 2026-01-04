#!/usr/bin/env python3
"""
Example: Continuous monitoring with data output.

This example demonstrates how to set up continuous monitoring
of industrial equipment with various output options.

Usage:
    python examples/continuous_monitor.py
"""

import json
import time
from datetime import datetime
from pathlib import Path

from vision_connector import HMIReader
from vision_connector.capture import ImageCapture
from vision_connector.outputs import CSVWriter


def main():
    # Determine paths relative to this script
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Paths
    image_path = project_root / "sample_images" / "hmi_screen.png"
    output_path = project_root / "output" / "readings.csv"
    config_path = project_root / "config" / "sample_config.json"

    print("Vision Connector - Continuous Monitor Example")
    print("=" * 50)
    print()

    # Initialize components
    reader = HMIReader(config=config_path)
    csv_writer = CSVWriter(output_path)

    print(f"Image source: {image_path}")
    print(f"Output file: {output_path}")
    print()

    # Simulate continuous monitoring (in real use, this would read from camera)
    print("Simulating continuous monitoring (3 readings)...")
    print("-" * 40)

    for i in range(3):
        # Read current values
        timestamp = datetime.now()
        result = reader.read_image(image_path)

        # Log to CSV
        csv_writer.append(result, timestamp=timestamp)

        # Display
        print(f"\nReading {i + 1} at {timestamp.strftime('%H:%M:%S')}:")
        print(json.dumps(result, indent=2))

        # Wait between readings (in real use, this might be configurable)
        if i < 2:
            time.sleep(1)

    print()
    print("-" * 40)
    print(f"Data logged to: {output_path}")
    print(f"Total rows: {csv_writer.get_row_count()}")

    # Show the logged data
    print()
    print("Logged data:")
    for row in csv_writer.read_all():
        print(f"  {row}")


if __name__ == "__main__":
    main()
