FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# Install deps + Blender 4.4.3
RUN apt-get update && apt-get install -y \
    wget python3 python3-pip libxkbcommon0 libxkbcommon-x11-0 \
    libepoxy0 zip libxrender1 libxi6 libxfixes3 libxcursor1 \
    libxrandr2 libxinerama1 libgl1 libsm6 libice6 \
    && rm -rf /var/lib/apt/lists/* \
    && wget https://mirror.clarkson.edu/blender/release/Blender4.4/blender-4.4.3-linux-x64.tar.xz \
    && tar -xf blender-4.4.3-linux-x64.tar.xz \
    && mv blender-4.4.3-linux-x64 /opt/blender \
    && ln -s /opt/blender/blender /usr/local/bin/blender \
    && rm blender-4.4.3-linux-x64.tar.xz

RUN pip install runpod boto3 requests

WORKDIR /workspace
COPY handler.py animation_render_script.py ./
CMD ["python3", "/workspace/handler.py"]
