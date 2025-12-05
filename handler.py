import os
import time
import subprocess
import requests
import runpod
import boto3

# This will run on the GPU serverless job
# It will:
# 1) Download the .blend file from a URL
# 2) Run Blender with your animation_render_script.py
# 3) Zip the output frames
# 4) Upload zip to S3
# 5) Return the S3 URL

def handler(job):
    print("🚀 RunPod serverless Blender job started")

    inp = job.get("input", {})

    blend_url = inp.get("blend_url")
    if not blend_url:
        return {"error": "Missing blend_url in input"}

    frame_start = int(inp.get("frame_start", 1))
    frame_end = int(inp.get("frame_end", 250))

    print(f"📄 Blend URL: {blend_url}")
    print(f"🎬 Frames: {frame_start} → {frame_end}")

    # 1) Download .blend file
    blend_path = "/workspace/scene.blend"
    print("⬇️ Downloading .blend file...")
    r = requests.get(blend_url)
    r.raise_for_status()
    with open(blend_path, "wb") as f:
        f.write(r.content)
    print(f"✅ Downloaded to {blend_path}")

    # 2) Make output folder
    output_dir = "/workspace/output"
    os.makedirs(output_dir, exist_ok=True)

    # 3) Run Blender in background mode
    # Blender image already has "blender" on PATH
    cmd = [
        "blender",
        "-b", blend_path,
        "--python", "/workspace/animation_render_script.py",
        "--",
        "--frame_start", str(frame_start),
        "--frame_end", str(frame_end),
    ]

    print("🎥 Running Blender...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print("Blender STDOUT:\n", result.stdout)
    print("Blender STDERR:\n", result.stderr)

    if result.returncode != 0:
        return {"error": "Blender render failed", "stderr": result.stderr}

    print("✅ Blender render finished")

    # 4) Zip the output frames
    zip_path = "/workspace/renders.zip"
    print("📦 Zipping output frames...")
    zip_cmd = ["zip", "-r", zip_path, output_dir]
    zip_res = subprocess.run(zip_cmd, capture_output=True, text=True)
    if zip_res.returncode != 0:
        return {"error": "Failed to zip outputs", "stderr": zip_res.stderr}

    print("✅ Zipped to", zip_path)

    # 5) Upload to S3
    bucket = os.environ.get("AWS_BUCKET_NAME")
    aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    aws_region = os.environ.get("AWS_REGION", "ap-south-1")  # adjust if needed

    if not (bucket and aws_access_key and aws_secret_key):
        return {"error": "Missing AWS env vars in serverless endpoint"}

    s3 = boto3.client(
        "s3",
        region_name=aws_region,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
    )

    key = f"blender_renders/{int(time.time())}_renders.zip"
    print(f"☁️ Uploading to S3: s3://{bucket}/{key}")

    s3.upload_file(zip_path, bucket, key)

    # Simple public-style URL (if bucket allows it or for presigned use)
    s3_url = f"https://{bucket}.s3.{aws_region}.amazonaws.com/{key}"

    print("✅ Uploaded to:", s3_url)

    return {
        "status": "ok",
        "frames": {"start": frame_start, "end": frame_end},
        "s3_url": s3_url,
    }

# Start the RunPod serverless worker
runpod.serverless.start({"handler": handler})
