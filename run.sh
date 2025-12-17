#!/bin/bash

# Check if ffmpeg is already installed
if ! command -v ffmpeg &> /dev/null; then
    echo "ffmpeg is not installed. Installing ffmpeg..."
    sudo apt update && sudo apt install -y ffmpeg
else
    echo "ffmpeg is already installed. Skipping installation."
fi

# Install Python dependencies from requirements.txt
pip3 install --no-cache-dir -r requirements.txt
pip install lxml_html_clean

# Run the Python bot
python3 update.py && python3 -m bot
