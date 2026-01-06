#!/usr/bin/env python3
"""
Example: Read values from analog gauges.

This example demonstrates how to extract readings from analog gauges
using needle detection.

Usage:
    python examples/read_gauge.py
"""

import json
from pathlib import Path

from vision_connector import GaugeReader


def main():
    # Determine paths relative to this script
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Sample gauge image path
    gauge_path = project_root / "sample_images" / "analog_gauge.png"

    print("Vision Connector - Gauge Reader Example")
    print("=" * 50)
    print()

    # Create gauge reader
    reader = GaugeReader()

    # Read the gauge
    print(f"Reading gauge from: {gauge_path}")
    print("-" * 40)

    result = reader.read_analog_gauge(
        gauge_path, min_value=0, max_value=100, unit="PSI"
    )

    print("Gauge reading:")
    print(json.dumps(result, indent=2))
    print()

    # Show interpretation
    if result.get("value") is not None:
        print(f"Detected value: {result['value']} {result['unit']}")
        print(f"Needle angle: {result['angle']}°")
        print(f"Confidence: {result['confidence'] * 100:.1f}%")
    else:
        print(f"Could not read gauge: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()
