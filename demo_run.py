#!/usr/bin/env python3
"""
Vision Connector Demo

Demonstrates the core functionality of the vision-connector library
by reading values from a sample HMI screen image.

This demo:
1. Loads a sample HMI screen image
2. Reads configured regions using OCR
3. Prints the extracted values as JSON

Usage:
    python demo_run.py

Requirements:
    - pip install -e .
    - tesseract-ocr installed on system
"""

import json
import sys
from pathlib import Path


def main():
    # Add src to path for development mode
    src_path = Path(__file__).parent / "src"
    if src_path.exists():
        sys.path.insert(0, str(src_path))

    from vision_connector import HMIReader, __version__

    # Paths
    project_root = Path(__file__).parent
    image_path = project_root / "sample_images" / "hmi_screen.png"
    config_path = project_root / "config" / "sample_config.json"

    # Header
    print()
    print("=" * 60)
    print("  VISION CONNECTOR DEMO")
    print(f"  Version: {__version__}")
    print("  Non-invasive industrial data capture using computer vision")
    print("=" * 60)
    print()

    # Verify image exists
    if not image_path.exists():
        print(f"ERROR: Sample image not found: {image_path}")
        print("Run: python scripts/generate_samples.py")
        sys.exit(1)

    # Verify config exists
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        sys.exit(1)

    print(f"Image: {image_path}")
    print(f"Config: {config_path}")
    print()

    # Initialize reader
    print("Initializing HMI Reader...")
    try:
        reader = HMIReader(config=config_path)
        print("OK - Reader initialized")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Read values
    print()
    print("Reading values from HMI screen...")
    print("-" * 40)

    try:
        result = reader.read_image(image_path)
    except Exception as e:
        print(f"ERROR reading image: {e}")
        sys.exit(1)

    # Output as JSON
    print()
    print("EXTRACTED VALUES:")
    print("-" * 40)
    print(json.dumps(result, indent=2))
    print()

    # Summary
    print("-" * 40)
    print(f"Successfully extracted {len(result)} values")
    print()

    # Show with confidence (bonus info)
    print("VALUES WITH CONFIDENCE:")
    print("-" * 40)
    try:
        result_meta = reader.read_image_with_metadata(image_path)
        for field, data in result_meta.items():
            value = data.get("value", "N/A")
            conf = data.get("confidence", 0)
            print(f"  {field}: {value} (confidence: {conf:.1%})")
    except Exception:
        pass

    print()
    print("=" * 60)
    print("  Demo complete!")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
