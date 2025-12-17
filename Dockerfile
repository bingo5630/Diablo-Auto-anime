# Base image
FROM python:3.10-slim-bullseye

# Set working directory
WORKDIR /usr/src/app

# Install system packages
RUN apt-get update && apt-get install -y \
    ffmpeg git wget pv jq python3-dev \
    mediainfo gcc libsm6 libxext6 \
    libfontconfig1 libxrender1 libgl1-mesa-glx \
 && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install "lxml[html_clean]"

# Optional: If using static ffmpeg binaries
# COPY --from=mwader/static-ffmpeg:6.1 /ffmpeg /bin/ffmpeg
# COPY --from=mwader/static-ffmpeg:6.1 /ffprobe /bin/ffprobe

# Copy project files
COPY . .

# Set entry point
CMD ["bash", "run.sh"]
