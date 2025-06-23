#!/usr/bin/env python3
"""Simple video upscaling utility using realsr-ncnn-vulkan or waifu2x-ncnn-vulkan."""

import argparse
import os
import shutil
import subprocess
import time
from typing import Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

REALSRCNN_EXECUTABLE = "realsr-ncnn-vulkan"
WAIFU2X_EXECUTABLE = "waifu2x-ncnn-vulkan"

FRAME_PADDING = 8


def clean_path(path: str) -> str:
    """Return absolute path without surrounding quotes."""
    return os.path.abspath(path.strip().strip('"'))


def clear_directory(folder: str) -> None:
    """Delete a folder and all its contents."""
    if os.path.exists(folder):
        shutil.rmtree(folder)
        print(f"🧹 Fully deleted {folder}")


def extract_frames(video_path: str, output_folder: str) -> None:
    """Extract frames from video using ffmpeg."""
    os.makedirs(output_folder, exist_ok=True)
    pattern = f"frame_%0{FRAME_PADDING}d.png"
    cmd = [
        "ffmpeg", "-thread_queue_size", "1024", "-i", video_path,
        "-vsync", "0", "-pix_fmt", "rgb24", os.path.join(output_folder, pattern)
    ]
    print(f"🚀 Extracting frames to {output_folder}...")
    subprocess.run(cmd, check=True)
    print("✅ Frame extraction complete.")


def rename_frames(folder: str) -> None:
    """Rename frames to a contiguous sequence."""
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith(".png"))
    if not files:
        raise RuntimeError(f"❌ No frames found in {folder} to rename.")
    for i, old in enumerate(files, start=1):
        new_name = f"frame_{i:0{FRAME_PADDING}d}.png"
        os.rename(os.path.join(folder, old), os.path.join(folder, new_name))
    print(f"✅ Renamed frames in {folder}.")


def get_video_fps(video_path: str) -> float:
    """Retrieve average FPS of a video using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=avg_frame_rate",
        "-of", "default=noprint_wrappers=1:nokey=1", video_path,
    ]
    raw = subprocess.check_output(cmd, text=True).strip()
    try:
        num, den = raw.split("/")
        return float(num) / float(den)
    except Exception:
        print("⚠️ Could not parse FPS, defaulting to 30.0")
        return 30.0


def get_unique_filename(path: str) -> str:
    """Return a unique filename if path already exists."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    new_name = f"{base}_{timestamp}{ext}"
    print(f"⚠️ File '{path}' exists. Using '{new_name}' instead.")
    return new_name


def reconstruct_video(
    frames_folder: str,
    input_video: str,
    output_video: str,
    fps: float,
    output_format: str = None,
) -> None:
    """Rebuild video from frames preserving original audio."""
    if output_format is None:
        _, ext = os.path.splitext(output_video)
        output_format = ext.lstrip(".").lower() or "mp4"

    rename_frames(frames_folder)
    pattern = f"frame_%0{FRAME_PADDING}d.png"

    if output_format == "gif":
        palette = os.path.join(frames_folder, "palette.png")
        subprocess.run(["ffmpeg", "-y", "-i", os.path.join(frames_folder, pattern), "-vf", "palettegen", palette], check=True)
        cmd = [
            "ffmpeg", "-y", "-framerate", str(fps),
            "-i", os.path.join(frames_folder, pattern),
            "-i", palette,
            "-lavfi", f"fps={fps}[x];[x][1:v]paletteuse",
            "-loop", "0",
            output_video,
        ]
    else:
        cmd = [
            "ffmpeg", "-framerate", str(fps),
            "-i", os.path.join(frames_folder, pattern),
            "-i", input_video,
            "-map", "0:v:0", "-map", "1:a:0?",
            "-c:v", "libx264", "-crf", "18", "-preset", "slow",
            "-c:a", "aac", "-b:a", "192k", "-shortest",
            output_video,
        ]

    print("🚀 Reconstructing final video...")
    subprocess.run(cmd, check=True)
    print(f"✅ Final video saved as: {output_video}")


def upscale_frames(model: str, scale: int, input_folder: str, output_folder: str, gpu: Optional[int]) -> None:
    """Run the selected upscaling model on extracted frames."""
    exe = REALSRCNN_EXECUTABLE if model == "realsr" else WAIFU2X_EXECUTABLE
    cmd = [exe, "-i", input_folder, "-o", output_folder, "-s", str(scale), "-f", "png"]
    if gpu is not None:
        cmd.extend(["-g", str(gpu)])
    print(f"🚀 Upscaling frames with {model} (scale={scale})...")
    subprocess.run(cmd, check=True)
    print("✅ Upscaling complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Upscale a video using realsr or waifu2x")
    parser.add_argument("input_video", help="Path to the input video")
    parser.add_argument("output_video", help="Path for the upscaled video")
    parser.add_argument("--model", choices=["realsr", "waifu2x"], default="realsr", help="Upscaling model")
    parser.add_argument("--scale", type=int, default=2, help="Scale factor for the model")
    parser.add_argument("--gpu", type=int, help="GPU index for ncnn executable")
    parser.add_argument("--frames_dir", default="upscale_frames", help="Temporary folder for extracted frames")
    parser.add_argument("--upscaled_dir", default="upscaled_frames", help="Folder for upscaled frames")
    parser.add_argument(
        "--output_format",
        choices=["mp4", "gif"],
        help="Output format (defaults to extension of output path)",
    )
    args = parser.parse_args()

    # Clean paths
    args.input_video = clean_path(args.input_video)
    args.output_video = clean_path(args.output_video)
    args.frames_dir = clean_path(args.frames_dir)
    args.upscaled_dir = clean_path(args.upscaled_dir)

    if args.output_format is None:
        _, ext = os.path.splitext(args.output_video)
        args.output_format = ext.lstrip(".").lower() or "mp4"

    try:
        clear_directory(args.frames_dir)
        clear_directory(args.upscaled_dir)
        os.makedirs(args.frames_dir, exist_ok=True)
        os.makedirs(args.upscaled_dir, exist_ok=True)

        extract_frames(args.input_video, args.frames_dir)
        upscale_frames(args.model, args.scale, args.frames_dir, args.upscaled_dir, args.gpu)
        fps = get_video_fps(args.input_video)
        unique_out = get_unique_filename(args.output_video)
        reconstruct_video(
            args.upscaled_dir,
            args.input_video,
            unique_out,
            fps,
            output_format=args.output_format,
        )
        print("✅ Done! Output video:", unique_out)
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")
    finally:
        clear_directory(args.frames_dir)
        clear_directory(args.upscaled_dir)
        print("🧹 Cleanup complete.")


if __name__ == "__main__":
    main()
