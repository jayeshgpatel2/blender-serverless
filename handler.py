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

    # IMPORTANT: Get frame range from input, these will OVERRIDE .blend file settings
    frame_start = inp.get("frame_start")  # Can be None
    frame_end = inp.get("frame_end")      # Can be None

    print(f"📄 Blend URL: {blend_url}")
    
    if frame_start is not None and frame_end is not None:
        print(f"🎬 Custom frame range: {frame_start} → {frame_end}")
    else:
        print(f"🎬 Using .blend file's frame range")

    # 1) Download .blend file
    blend_path = "/workspace/scene.blend"
    print("⬇️  Downloading .blend file...")
    r = requests.get(blend_url)
    r.raise_for_status()
    with open(blend_path, "wb") as f:
        f.write(r.content)
    print(f"✅ Downloaded to {blend_path}")

    # 2) Make output folder
    output_dir = "/workspace/output"
    os.makedirs(output_dir, exist_ok=True)

    # 3) Run Blender in background mode
    cmd = [
        "blender",
        "-b", blend_path,
        "--python", "/workspace/animation_render_script.py",
    ]
    
    # CRITICAL: Only add frame arguments if they were provided
    # This ensures we OVERRIDE the .blend file's frame range
    if frame_start is not None and frame_end is not None:
        cmd.extend([
            "--",
            "--frame_start", str(frame_start),
            "--frame_end", str(frame_end),
        ])
        print(f"✅ Passing frame range to Blender: {frame_start} to {frame_end}")
    else:
        # No frame range specified - Blender will use .blend file's range
        print(f"✅ No frame override - using .blend file's settings")

    print("🎥 Running Blender...")
    print(f"Command: {' '.join(cmd)}")
    
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
    aws_region = os.environ.get("AWS_REGION", "ap-south-1")

    if not (bucket and aws_access_key and aws_secret_key):
        return {"error": "Missing AWS env vars in serverless endpoint"}

    s3 = boto3.client(
        "s3",
        region_name=aws_region,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
    )

    key = f"blender_renders/{int(time.time())}_renders.zip"
    print(f"☁️  Uploading to S3: s3://{bucket}/{key}")

    s3.upload_file(zip_path, bucket, key)

    # Generate presigned URL (works even if bucket is private)
    s3_url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket, 'Key': key},
        ExpiresIn=7200  # 2 hours
    )

    print("✅ Uploaded to:", s3_url)

    return {
        "status": "ok",
        "frames": {
            "start": frame_start if frame_start else "auto", 
            "end": frame_end if frame_end else "auto"
        },
        "s3_url": s3_url,
    }

# Start the RunPod serverless worker
runpod.serverless.start({"handler": handler})
