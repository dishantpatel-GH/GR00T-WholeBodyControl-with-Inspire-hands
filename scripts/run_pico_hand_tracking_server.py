#!/usr/bin/env python3
"""Standalone script to run the Pico hand tracking server.

This script should be run in a separate terminal to stream hand tracking data
from a different Pico controller. The main teleop loop will connect to this server
to receive hand tracking data while using another Pico for arm/lower body control.

Usage:
    python scripts/run_pico_hand_tracking_server.py --port 5557
"""

import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from gr00t_wbc.control.teleop.device.pico.pico_hand_tracking_server import main

if __name__ == "__main__":
    main()
