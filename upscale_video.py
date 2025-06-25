#!/usr/bin/env python3
"""Simple video upscaling utility using realsr-ncnn-vulkan or waifu2x-ncnn-vulkan."""

import argparse
import os
import shutil
import subprocess
import time
from typing import Optional

try:
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency
    Image = None

try:
    import torch
except Exception:  # pragma: no cover - optional dependency
    torch = None


try:
    from diffusers import (
        StableDiffusionUpscalePipeline,
        StableDiffusionLatentUpscalePipeline,
        LDMSuperResolutionPipeline,
    )
except Exception as e:  # pragma: no cover - optional dependency
    StableDiffusionUpscalePipeline = None
    StableDiffusionLatentUpscalePipeline = None
    LDMSuperResolutionPipeline = None


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

REALSRCNN_EXECUTABLE = "realsr-ncnn-vulkan"
WAIFU2X_EXECUTABLE = "waifu2x-ncnn-vulkan"
REALESRGAN_EXECUTABLE = "realesrgan-ncnn-vulkan"
SWINIR_EXECUTABLE = "swinir-ncnn-vulkan"
SDX4_MODEL_ID = "stabilityai/stable-diffusion-x4-upscaler"
LDSR_MODEL_ID = "CompVis/ldm-super-resolution-4x-openimages"

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
    if model in {"sdx4", "ldsr"}:
        if Image is None or torch is None:
            raise RuntimeError("Diffusion upscaling requires Pillow and torch")

        if model == "sdx4":
            if StableDiffusionUpscalePipeline is None:
                raise RuntimeError("Diffusion upscaling requires the diffusers package")
            if scale != 4:
                raise ValueError("SDx4 upscaler only supports 4x scale")
        else:
            if LDMSuperResolutionPipeline is None:
                raise RuntimeError("Diffusion upscaling requires the diffusers package")
            if scale != 4:
                raise ValueError("LDSR upscaler only supports 4x scale")


        device = f"cuda:{gpu}" if (gpu is not None and gpu >= 0 and torch.cuda.is_available()) else "cpu"
        dtype = torch.float16 if "cuda" in device else torch.float32
        if model == "sdx4":
            pipe = StableDiffusionUpscalePipeline.from_pretrained(SDX4_MODEL_ID, torch_dtype=dtype)
        else:
            pipe = LDMSuperResolutionPipeline.from_pretrained(LDSR_MODEL_ID, torch_dtype=dtype)
        pipe.to(device)
        os.makedirs(output_folder, exist_ok=True)
        for fname in sorted(os.listdir(input_folder)):
            if not fname.lower().endswith(".png"):
                continue
            img = Image.open(os.path.join(input_folder, fname)).convert("RGB")
            if model == "sdx4":
                result = pipe(prompt="", image=img, num_inference_steps=75).images[0]
            else:
                result = pipe(img, num_inference_steps=50, eta=1).images[0]
            result.save(os.path.join(output_folder, fname))
        print("✅ Diffusion upscaling complete.")
        return
    exe_map = {
        "realsr": REALSRCNN_EXECUTABLE,
        "waifu2x": WAIFU2X_EXECUTABLE,
        "realesrgan": REALESRGAN_EXECUTABLE,
        "swinir": SWINIR_EXECUTABLE,
    }
    exe = exe_map.get(model)

    def locate_executable(name: str) -> Optional[str]:
        """Return path to executable if found locally or on PATH."""
        # Check PATH first
        path = shutil.which(name)
        if path:
            return path

        # Check for <name>.exe in script directory
        local = os.path.join(SCRIPT_DIR, name)
        if os.name == "nt":
            local_exe = local + ".exe"
            if os.path.isfile(local_exe):
                return local_exe
        if os.path.isfile(local):
            return local

        # Check for executable inside folder with same name
        folder_exe = os.path.join(SCRIPT_DIR, name, name)
        if os.name == "nt":
            folder_exe += ".exe"
        if os.path.isfile(folder_exe):
            return folder_exe

        return None

    exe_path = locate_executable(exe)
    if not exe_path:
        raise FileNotFoundError(
            f"❌ Model binary '{exe}' was not found. Ensure it is installed and on your PATH."
        )

    cmd = [exe_path, "-i", input_folder, "-o", output_folder, "-s", str(scale), "-f", "png"]
    if gpu is not None:
        cmd.extend(["-g", str(gpu)])
    print(f"🚀 Upscaling frames with {model} (scale={scale})...")
    subprocess.run(cmd, check=True)
    print("✅ Upscaling complete.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upscale a video using ncnn or diffusion models"
    )
    parser.add_argument("input_video", help="Path to the input video")
    parser.add_argument("output_video", help="Path for the upscaled video")
    parser.add_argument(
        "--model",
        choices=["realsr", "waifu2x", "realesrgan", "swinir", "sdx4", "ldsr"],
        default="realsr",
        help="Upscaling model",
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=2,
        help="Scale factor for ncnn models (diffusion-based models have fixed scale)",
    )
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
