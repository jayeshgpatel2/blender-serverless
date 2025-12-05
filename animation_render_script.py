import bpy
import os
import sys
import time

print("\n" + "="*60)
print("BLENDER ANIMATION RENDERING (GPU - RTX 4090)")
print("="*60 + "\n")

# Parse command line arguments for frame range
frame_start = None
frame_end = None

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
for i, arg in enumerate(args):
    if arg == "--frame_start" and i + 1 < len(args):
        frame_start = int(args[i + 1])
    elif arg == "--frame_end" and i + 1 < len(args):
        frame_end = int(args[i + 1])

# Get blend file info
blend_name = bpy.path.basename(bpy.data.filepath)
blend_base = os.path.splitext(blend_name)[0]

print(f"📄 File: {blend_name}")

# Configure render settings
scene = bpy.context.scene
render = scene.render

# Create folder: /workspace/output/<blend_file_name>/
blend_base_safe = blend_base.replace(" ", "_").replace(".", "_")
output_dir = f"/workspace/output/{blend_base_safe}"
os.makedirs(output_dir, exist_ok=True)

# Blender will generate: <blendname>_0001.png etc.
render.filepath = os.path.join(output_dir, f"{blend_base_safe}_")
print(f"📁 Output: {output_dir}/")

# Configure render engine for GPU
print("\n🔧 Configuring render settings...")

# Use Cycles for better quality
scene.render.engine = 'CYCLES'
scene.cycles.device = 'GPU'

# Configure GPU devices
prefs = bpy.context.preferences
cycles_prefs = prefs.addons['cycles'].preferences

# Enable all available GPUs
cycles_prefs.compute_device_type = 'CUDA'
cycles_prefs.get_devices()

print(f"🖥️  Available GPUs:")
for device in cycles_prefs.devices:
    device.use = True
    print(f"  ✓ {device.name}")

# Optimize render settings for animation
scene.cycles.samples = 128  # Adjust based on quality needs
scene.cycles.use_denoising = True
scene.cycles.denoiser = 'OPENIMAGEDENOISE'

# Tile size optimization for GPU
scene.cycles.tile_size = 256

print(f"📊 Samples: {scene.cycles.samples}")
print(f"🎨 Resolution: {render.resolution_x}x{render.resolution_y}")

# Set frame range
if frame_start is not None and frame_end is not None:
    scene.frame_start = frame_start
    scene.frame_end = frame_end
    print(f"🎬 Custom frame range: {frame_start} to {frame_end}")
else:
    frame_start = scene.frame_start
    frame_end = scene.frame_end
    print(f"🎬 Blend file frame range: {frame_start} to {frame_end}")

total_frames = frame_end - frame_start + 1
print(f"📊 Total frames: {total_frames}\n")

# Set output format
render.image_settings.file_format = 'PNG'
render.image_settings.color_mode = 'RGBA'
render.image_settings.compression = 15

print("="*60)
print("🎬 STARTING ANIMATION RENDER")
print("="*60 + "\n")

start_time = time.time()

try:
    # Render animation
    print(f"🎥 Rendering frames {frame_start} to {frame_end}...")
    bpy.ops.render.render(animation=True, write_still=True)
    
    render_time = time.time() - start_time
    avg_time_per_frame = render_time / total_frames
    
    print(f"\n✅ Animation rendered successfully!")
    print(f"⏱️  Total time: {render_time/60:.2f} minutes")
    print(f"⏱️  Avg per frame: {avg_time_per_frame:.2f} seconds")
    
except Exception as e:
    print(f"\n❌ Render failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("✅ RENDERING COMPLETE!")
print("="*60 + "\n")

# List output files
print("📦 Rendered frames:")
output_files = sorted([f for f in os.listdir(output_dir) if f.startswith(blend_base)])
print(f"  Found {len(output_files)} frames")

if output_files:
    total_size = sum(os.path.getsize(os.path.join(output_dir, f)) for f in output_files)
    print(f"  Total size: {total_size / (1024*1024):.2f} MB")
    print(f"  First: {output_files[0]}")
    print(f"  Last: {output_files[-1]}")
else:
    print("  ⚠️ No output files found!")

print("\n" + "="*60)
