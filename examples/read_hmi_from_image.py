#!/usr/bin/env python3
"""
Example: Read values from an HMI screen image.

This example demonstrates how to extract data from a captured HMI screen
using defined regions of interest (ROI).

Usage:
    python examples/read_hmi_from_image.py
"""

import json
from pathlib import Path

from vision_connector import HMIReader


def main():
    # Determine paths relative to this script
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Sample image and config paths
    image_path = project_root / "sample_images" / "hmi_screen.png"
    config_path = project_root / "config" / "sample_config.json"

    print("Vision Connector - HMI Screen Reader Example")
    print("=" * 50)
    print()

    # Method 1: Using config file
    print("Method 1: Reading with config file")
    print("-" * 40)

    reader = HMIReader(config=config_path)
    result = reader.read_image(image_path)

    print("Extracted values:")
    print(json.dumps(result, indent=2))
    print()

    # Method 2: Using inline region definitions
    print("Method 2: Reading with inline regions")
    print("-" * 40)

    reader = HMIReader()
    result = reader.read_image(
        image_path,
        regions={
            "temperature": {"x": 40, "y": 130, "w": 95, "h": 40, "type": "number"},
            "pressure": {"x": 40, "y": 230, "w": 80, "h": 40, "type": "number"},
            "status": {"x": 340, "y": 145, "w": 140, "h": 40, "type": "text"},
        },
    )

    print("Extracted values:")
    print(json.dumps(result, indent=2))
    print()

    # Method 3: Reading with confidence scores
    print("Method 3: Reading with confidence metadata")
    print("-" * 40)

    result_with_meta = reader.read_image_with_metadata(
        image_path,
        regions={
            "temperature": {"x": 40, "y": 130, "w": 95, "h": 40, "type": "number"},
            "status": {"x": 340, "y": 145, "w": 140, "h": 40, "type": "text"},
        },
    )

    print("Extracted values with metadata:")
    print(json.dumps(result_with_meta, indent=2))


if __name__ == "__main__":
    main()
