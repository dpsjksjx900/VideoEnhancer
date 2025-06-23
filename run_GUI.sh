#!/bin/bash
# Simple script to run the GUI on Unix-like systems
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
python3 GUI.py
