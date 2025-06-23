import os
import subprocess
import argparse
import time
import math
import shutil

# ---------------------------------------------------------
# Global path setup and configurations
# ---------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RIFE_EXECUTABLE = os.path.join(SCRIPT_DIR, "rife-ncnn-vulkan", "rife-ncnn-vulkan.exe")

# Frame naming configuration
FRAME_PADDING = 8  # Change this value to adjust frame number padding

def clean_path(path):
    """Remove surrounding quotation marks and get absolute path."""
    path = path.strip().strip('"')
    return os.path.abspath(path)

def clear_directory(folder):
    """Delete a directory fully (files + subfolders)."""
    if os.path.exists(folder):
        shutil.rmtree(folder)
        print(f"🧹 Fully deleted {folder}")

def extract_frames(video_path, output_folder):
    """Extract frames from video using ffmpeg (-vsync 0)."""
    os.makedirs(output_folder, exist_ok=True)
    frame_pattern = f"frame_%0{FRAME_PADDING}d.png"
    command = [
        "ffmpeg", "-thread_queue_size", "1024", "-i", video_path, "-vsync", "0",
        os.path.join(output_folder, frame_pattern)
    ]
    print(f"🚀 Extracting frames to {output_folder}...")
    subprocess.run(command, check=True)
    print("✅ Frame extraction complete.")

def is_power_of_2(n):
    """Check if an integer (or float) is a power of 2."""
    try:
        n = float(n)
        return math.log2(n).is_integer()
    except:
        return False

# ---------------------------------------------------------
# 1) Interpolation Helpers
#    - single-pass with -n (RIFE v4.x) or
#    - multi-pass doubling (older RIFE).
# ---------------------------------------------------------

def run_rife_single_pass(
    input_folder, output_folder,
    model, target_frames,
    time_step=None,
    gpu_id=None,
    thread_config=None,
    tta=False,
    temporal_tta=False,
    uhd=False,
    pattern_format=None
):
    """
    RIFE v4.x supports '-n <target_frames>' directly.
    We can do a single pass to get exactly 'target_frames'.
    """
    os.makedirs(output_folder, exist_ok=True)
    command = [
        RIFE_EXECUTABLE,
        "-i", input_folder,
        "-o", output_folder,
        "-m", model,
        "-f", "png",
        "-n", str(target_frames),
    ]
    if time_step is not None:
        command.extend(["-s", str(time_step)])
    if gpu_id is not None:
        command.extend(["-g", str(gpu_id)])
    if thread_config is not None:
        command.extend(["-j", thread_config])
    if tta:
        command.append("-x")
    if temporal_tta:
        command.append("-z")
    if uhd:
        command.append("-u")
    if pattern_format is not None:
        command.extend(["-f", pattern_format])

    print(f"🚀 [RIFE v4.x] Single-pass interpolation to reach exactly {target_frames} frames.")
    subprocess.run(command, check=True)
    print(f"✅ Single-pass interpolation complete. Frames stored in: {output_folder}")

def run_rife_multipass(
    input_folder, 
    output_folder,
    model,
    desired_frames,
    preserve_original_frames=False,  # see spaced_trim_frames logic
    time_step=None,
    gpu_id=None,
    thread_config=None,
    tta=False,
    temporal_tta=False,
    uhd=False,
    pattern_format=None,
    temp_folder=None  # Added parameter to specify temp_folder
):
    """
    For older RIFE that doesn't support '-n':
      1) Repeatedly double frames until >= desired_frames.
      2) Then do spaced trimming if overshoot.
      3) Ensure each pass writes to a fresh folder inside temp_folder.
    """
    if temp_folder is None:
        raise ValueError("temp_folder must be specified for run_rife_multipass.")

    current_count = count_frames_in_folder(input_folder)
    if current_count >= desired_frames:
        # Just copy & trim
        clear_directory(output_folder)
        shutil.copytree(input_folder, output_folder)  # no dirs_exist_ok => fresh copy
        final_count = count_frames_in_folder(output_folder)
        if final_count > desired_frames:
            spaced_trim_frames(output_folder, desired_frames, preserve_original_frames)
        print(f"✅ Copied and trimmed frames to {output_folder}")
        return

    factor = desired_frames / current_count
    passes = math.ceil(math.log2(factor))  # e.g. factor=3.06 => passes=2

    print(f"🚀 [Legacy RIFE] Attempting {passes} pass(es) to exceed {desired_frames} frames.")
    current_source = input_folder

    for i in range(passes):
        pass_folder = os.path.join(temp_folder, f"temp_pass_{i+1}")
        clear_directory(pass_folder)  # ensure it's empty
        os.makedirs(pass_folder, exist_ok=True)

        cmd = [
            RIFE_EXECUTABLE, 
            "-i", current_source,
            "-o", pass_folder,
            "-m", model,
            "-f", "png"
        ]
        if gpu_id is not None:
            cmd.extend(["-g", str(gpu_id)])
        if thread_config is not None:
            cmd.extend(["-j", thread_config])
        if tta:
            cmd.append("-x")
        if temporal_tta:
            cmd.append("-z")
        if uhd:
            cmd.append("-u")
        if pattern_format is not None:
            cmd.extend(["-f", pattern_format])

        print(f"   Pass {i+1}/{passes}: doubling frames.")
        subprocess.run(cmd, check=True)

        # Now pass_folder has the new doubled frames
        new_count = count_frames_in_folder(pass_folder)
        current_source = pass_folder

        if new_count >= desired_frames:
            # Enough frames => stop extra passes
            print(f"✅ Desired frame count {desired_frames} reached.")
            break

    # We now have at least desired_frames in 'current_source'
    clear_directory(output_folder)
    shutil.copytree(current_source, output_folder)  # final copy
    final_count = count_frames_in_folder(output_folder)
    if final_count > desired_frames:
        spaced_trim_frames(output_folder, desired_frames, preserve_original_frames)

    print(f"✅ Multipass interpolation complete. Frames stored in: {output_folder}")

# ---------------------------------------------------------
# 2) Frame removal or spaced trimming
# ---------------------------------------------------------

def count_frames_in_folder(folder):
    return len([f for f in os.listdir(folder) if f.lower().endswith(".png")])

def spaced_trim_frames(folder, target_count, preserve_original=False):
    """
    Distribute frame removals so we don't just cut the tail.
    If preserve_original=True, skip certain "original" frames if possible.
    """
    frames = sorted(f for f in os.listdir(folder) if f.lower().endswith('.png'))
    N = len(frames)
    if N <= target_count:
        return

    remove_count = N - target_count
    print(f"⚠️ Spaced Trimming {remove_count} frames out of {N} to get {target_count} total.")

    original_set = set()
    if preserve_original:
        # Suppose original frames have "orig_" prefix or track them otherwise
        for fr in frames:
            if "orig_" in fr:
                original_set.add(fr)

    # Collect indices that can be removed:
    removable_indices = [i for i, name in enumerate(frames) if name not in original_set]
    if len(removable_indices) < remove_count:
        # We have to remove some originals too
        removable_indices = list(range(N))

    # Spaced removal approach
    step = len(removable_indices) / remove_count
    accum = 0.0
    remove_indices = []
    while len(remove_indices) < remove_count:
        idx = int(accum)
        if idx >= len(removable_indices):
            break
        remove_indices.append(removable_indices[idx])
        accum += step

    remove_indices = sorted(set(remove_indices))  # Remove duplicates
    remove_indices = remove_indices[:remove_count]  # Ensure only 'remove_count' removals

    for i in remove_indices:
        file_to_remove = os.path.join(folder, frames[i])
        if os.path.exists(file_to_remove):
            os.remove(file_to_remove)
            print(f"🗑 Removed frame: {frames[i]}")
    print(f"✅ Spaced trim complete. {len(remove_indices)} frames removed.")

def pick_spaced_indices(all_frames, to_remove, original_set):
    """
    Return a list of indexes (from 'all_frames') that we want to remove,
    distributed as evenly as possible across the entire timeline,
    *avoiding original frames if preserve_original is True*.
    """
    N = len(all_frames)
    # Indices that are not "original"
    removable_indices = [i for i, name in enumerate(all_frames) if name not in original_set]
    if len(removable_indices) < to_remove:
        # We must remove some original frames too, or we won't hit target_count
        # fallback: all frames are removable
        removable_indices = list(range(N))

    # We'll remove 'to_remove' items spaced from 'removable_indices'.
    # e.g. if removable_indices has 50 items, and to_remove=10,
    # remove 1 out of every 5. We'll do it by stepping.

    remove_indices = []
    step = len(removable_indices) / to_remove  # e.g. 50/10=5
    accum = 0.0

    i = 0
    while len(remove_indices) < to_remove and i < len(removable_indices):
        remove_idx = removable_indices[int(accum)]
        remove_indices.append(remove_idx)
        accum += step
        i += 1

    remove_indices.sort()
    return remove_indices

# ---------------------------------------------------------
# 3) Final "filling" and "interpolation" functions
# ---------------------------------------------------------

def fill_back_to_original_count(
    input_folder,
    output_folder,
    model,
    original_count,
    time_step=None,
    gpu_id=None,
    thread_config=None,
    tta=False,
    temporal_tta=False,
    uhd=False,
    pattern_format=None,
    temp_folder=None  # Added parameter
):
    """
    Step 2: After removing duplicates, we might have fewer frames
    than 'original_count'. We restore it so the final duration
    remains the same as the original.

    - If using RIFE v4.x => single pass with '-n original_count'.
    - If older => multi-pass doubling + spaced trimming if overshoot.
    """
    current_count = count_frames_in_folder(input_folder)
    if current_count == original_count:
        print(f"✅ No fill needed. Already have {current_count} frames.")
        # Just copy them over
        shutil.copytree(input_folder, output_folder, dirs_exist_ok=True)
        return
    elif current_count > original_count:
        print(f"⚠️ Found {current_count} frames > original {original_count}; trimming down.")
        shutil.copytree(input_folder, output_folder, dirs_exist_ok=True)
        spaced_trim_frames(output_folder, original_count, preserve_original=False)
        return

    # current_count < original_count => we must add frames
    if model in ["rife-v4", "rife-v4.6"]:
        # single pass with -n
        run_rife_single_pass(
            input_folder, output_folder,
            model=model,
            target_frames=original_count,
            time_step=time_step,
            gpu_id=gpu_id,
            thread_config=thread_config,
            tta=tta,
            temporal_tta=temporal_tta,
            uhd=uhd,
            pattern_format=pattern_format,
        )
    else:
        # older model => multi-pass doubling
        run_rife_multipass(
            input_folder, output_folder,
            model=model,
            desired_frames=original_count,
            preserve_original_frames=False,  # or True if you want to keep them
            time_step=time_step,
            gpu_id=gpu_id,
            thread_config=thread_config,
            tta=tta,
            temporal_tta=temporal_tta,
            uhd=uhd,
            pattern_format=pattern_format,
            temp_folder=temp_folder  # Pass temp_folder
        )

def final_interpolation_to_factor(
    input_folder,
    output_folder,
    model,
    original_count,
    fps_factor,
    time_step=None,
    gpu_id=None,
    thread_config=None,
    tta=False,
    temporal_tta=False,
    uhd=False,
    pattern_format=None,
    temp_folder=None  # Added parameter
):
    """
    Step 3: Interpolate from the 'restored' original_count
    to final_count = original_count * fps_factor.

    If v4.x => single pass with -n final_count
    else => multi-pass doubling until >= final_count, spaced trim.
    """
    final_count = int(original_count * fps_factor)
    if model in ["rife-v4", "rife-v4.6"]:
        run_rife_single_pass(
            input_folder, output_folder,
            model=model,
            target_frames=final_count,
            time_step=time_step,
            gpu_id=gpu_id,
            thread_config=thread_config,
            tta=tta,
            temporal_tta=temporal_tta,
            uhd=uhd,
            pattern_format=pattern_format
        )
    else:
        run_rife_multipass(
            input_folder, output_folder,
            model=model,
            desired_frames=final_count,
            preserve_original_frames=False,  # or True if you want
            time_step=time_step,
            gpu_id=gpu_id,
            thread_config=thread_config,
            tta=tta,
            temporal_tta=temporal_tta,
            uhd=uhd,
            pattern_format=pattern_format,
            temp_folder=temp_folder  # Pass temp_folder
        )

# ---------------------------------------------------------
# 4) Utility: rename frames, unique output name, reconstruct
# ---------------------------------------------------------

def rename_interpolated_frames(output_folder):
    """Rename frames to a strict sequence: frame_00000001.png ..."""
    files = sorted(f for f in os.listdir(output_folder) if f.lower().endswith(".png"))
    if not files:
        raise RuntimeError(f"❌ No frames found in {output_folder} to rename.")

    # Rename in ascending order
    for i, old_file in enumerate(files, start=1):
        old_path = os.path.join(output_folder, old_file)
        new_name = f"frame_{i:0{FRAME_PADDING}d}.png"
        new_path = os.path.join(output_folder, new_name)
        os.rename(old_path, new_path)
    print(f"✅ Renamed frames in {output_folder} to a clean sequence.")

def get_unique_filename(output_video):
    """Generate a unique filename if 'output_video' already exists."""
    if not os.path.exists(output_video):
        return output_video
    base, ext = os.path.splitext(output_video)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    new_filename = f"{base}_{timestamp}{ext}"
    print(f"⚠️ File '{output_video}' exists. Using '{new_filename}' instead.")
    return new_filename

def reconstruct_video(
    frames_folder,
    input_video,
    output_video,
    final_fps,
    output_format=None
):
    """Rebuild the final video using ffmpeg."""
    # Determine output format either from argument or file extension
    if output_format is None:
        _, ext = os.path.splitext(output_video)
        output_format = ext.lstrip(".").lower() or "mp4"

    # Check there is at least one frame
    files = sorted(f for f in os.listdir(frames_folder) if f.lower().endswith(".png"))
    if not files:
        raise RuntimeError("❌ No frames found to reconstruct the video.")

    # Rename them strictly for ffmpeg
    rename_interpolated_frames(frames_folder)

    frame_pattern = f"frame_%0{FRAME_PADDING}d.png"

    if output_format == "gif":
        palette = os.path.join(frames_folder, "palette.png")
        subprocess.run([
            "ffmpeg", "-y", "-i", os.path.join(frames_folder, frame_pattern),
            "-vf", "palettegen", palette
        ], check=True)
        cmd = [
            "ffmpeg", "-y", "-framerate", str(final_fps),
            "-i", os.path.join(frames_folder, frame_pattern),
            "-i", palette,
            "-lavfi", f"fps={final_fps}[x];[x][1:v]paletteuse",
            "-loop", "0",
            output_video
        ]
    else:
        cmd = [
            "ffmpeg",
            "-framerate", str(final_fps),
            "-i", os.path.join(frames_folder, frame_pattern),
            "-i", input_video,
            "-map", "0:v:0", "-map", "1:a:0?",
            "-c:v", "libx264", "-crf", "18", "-preset", "slow",
            "-c:a", "aac", "-b:a", "192k", "-shortest",
            output_video
        ]

    print("🚀 Reconstructing final video with:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print(f"✅ Final video saved as: {output_video}")

# ---------------------------------------------------------
# 5) The main() flow
# ---------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="RIFE interpolation with dedup + fill + final factor.")
    parser.add_argument("input_video", help="Path to the input video")
    parser.add_argument("output_video", help="Path to the output video")
    parser.add_argument("--model", default="rife-v4.6", help="RIFE model name/folder")
    parser.add_argument("--fps_factor", type=float, default=2.0, help="How many times to increase final FPS")
    parser.add_argument("--remove_duplicates", action="store_true", help="Detect & remove duplicate frames first")

    # Additional optional arguments
    parser.add_argument("--input_frames", default="frames_input", help="Folder for extracted frames")
    parser.add_argument("--restored_frames", default="restored_frames", help="Folder after filling to original count")
    parser.add_argument("--final_frames", default="frames_output", help="Folder for final interpolated frames")
    parser.add_argument("--temp_folder", default="temp_interpolation", help="Folder for intermediate steps")
    parser.add_argument("--time_step", type=float, help="RIFE param: time step (v4.x only)")
    parser.add_argument("--gpu_id", type=int, help="GPU device index for rife-ncnn-vulkan")
    parser.add_argument("--thread_config", help="Threads config (e.g. '4:4:4')")
    parser.add_argument("--tta", action="store_true", help="Enable TTA -x")
    parser.add_argument("--temporal_tta", action="store_true", help="Enable temporal TTA -z")
    parser.add_argument("--uhd", action="store_true", help="Enable UHD -u")
    parser.add_argument("--pattern_format", help="Pattern format for rife-ncnn-vulkan")
    parser.add_argument(
        "--output_format",
        choices=["mp4", "gif"],
        help="Output format (defaults to extension of output path)"
    )

    args = parser.parse_args()

    # Clean / absolute paths
    args.input_video = clean_path(args.input_video)
    args.output_video = clean_path(args.output_video)
    args.input_frames = clean_path(args.input_frames)
    args.restored_frames = clean_path(args.restored_frames)
    args.final_frames = clean_path(args.final_frames)
    args.temp_folder = clean_path(args.temp_folder)

    if args.output_format is None:
        _, ext = os.path.splitext(args.output_video)
        args.output_format = ext.lstrip(".").lower() or "mp4"

    # Initialize a list to track all temporary folders that need to be cleaned
    temp_folders = [
        args.input_frames, 
        args.restored_frames, 
        args.final_frames, 
        args.temp_folder
    ]

    try:
        # 1) Clear old folders
        print("🔄 Cleaning previous frames and preparing directories...")
        for folder in temp_folders:
            clear_directory(folder)
            os.makedirs(folder, exist_ok=True)

        # 2) Extract frames
        print("📂 Extracting frames from video...")
        extract_frames(args.input_video, args.input_frames)
        original_total_frames = count_frames_in_folder(args.input_frames)
        print(f"🎥 Original video frames: {original_total_frames}")

        # 3) Remove duplicates if requested
        duplicates_removed = False
        if args.remove_duplicates:
            print("🔍 Detecting duplication rate (via external script `detect_frame_rate.py`)...")
            try:
                duplication_rate = float(
                    subprocess.check_output(["python", "detect_frame_rate.py", args.input_frames], text=True).strip()
                )
                epsilon = 0.01  # Define a small threshold
                if duplication_rate > (1.0 + epsilon):
                    print(f"🛠 Duplicate rate {duplication_rate} > 1.0 + {epsilon}, removing duplicates...")
                    filtered_frames_folder = os.path.join(args.input_frames, "filtered_frames")
                    clear_directory(filtered_frames_folder)
                    subprocess.run([
                        "python", "remove_duplicates.py",
                        "--input_folder", args.input_frames,
                        "--output_folder", filtered_frames_folder,
                        "--rate", str(duplication_rate)
                    ], check=True)
                    # Now 'filtered_frames_folder' has fewer frames
                    args.input_frames = filtered_frames_folder
                    duplicates_removed = True
                    print(f"✅ Duplicate removal complete. Frames saved in: {filtered_frames_folder}")
                else:
                    print(f"✅ No significant duplicates found (duplication_rate={duplication_rate}). Skipping duplicate removal and frame filling.")
            except subprocess.CalledProcessError:
                print("❌ Error running duplication detection. Skipping duplicates removal.")
        else:
            print("🔍 Duplicate removal not requested. Skipping.")

        # 4) Fill back to the original frame count (so duration is unchanged)
        if duplicates_removed:
            original_count = get_video_frame_count(args.input_video)
            print(f"🔄 Restoring frames to original count = {original_count} ...")
            fill_back_to_original_count(
                args.input_frames,
                args.restored_frames,
                model=args.model,
                original_count=original_count,
                time_step=args.time_step,
                gpu_id=args.gpu_id,
                thread_config=args.thread_config,
                tta=args.tta,
                temporal_tta=args.temporal_tta,
                uhd=args.uhd,
                pattern_format=args.pattern_format,
                temp_folder=args.temp_folder  # Pass temp_folder
            )
        else:
            print(f"🔄 No duplicate removal. Setting restored_frames = input_frames.")
            # Copy input_frames to restored_frames
            clear_directory(args.restored_frames)
            shutil.copytree(args.input_frames, args.restored_frames)
            print(f"✅ Frames copied to restored_frames: {args.restored_frames}")

        # 5) Final interpolation to factor => final_frames
        if args.fps_factor != 1.0:
            original_count = get_video_frame_count(args.input_video)
            final_count = int(original_count * args.fps_factor)
            print(f"🚀 Final interpolation to factor {args.fps_factor} => {final_count} frames")
            final_interpolation_to_factor(
                args.restored_frames,
                args.final_frames,
                model=args.model,
                original_count=original_count,
                fps_factor=args.fps_factor,
                time_step=args.time_step,
                gpu_id=args.gpu_id,
                thread_config=args.thread_config,
                tta=args.tta,
                temporal_tta=args.temporal_tta,
                uhd=args.uhd,
                pattern_format=args.pattern_format,
                temp_folder=args.temp_folder  # Pass temp_folder
            )
        else:
            print("🔄 FPS Factor is 1. No final interpolation step needed.")
            # Set final_frames = restored_frames
            clear_directory(args.final_frames)
            shutil.copytree(args.restored_frames, args.final_frames)
            print(f"✅ Final frames set to restored_frames: {args.final_frames}")

        # 6) Construct final video
        # We keep the same duration => final FPS = original_fps * fps_factor
        original_fps = get_video_fps(args.input_video)
        final_fps = original_fps * args.fps_factor
        unique_out = get_unique_filename(args.output_video)
        print(f"🎬 Reconstructing video at {final_fps} FPS...")
        reconstruct_video(
            args.final_frames,
            args.input_video,
            unique_out,
            final_fps=final_fps,
            output_format=args.output_format,
        )
        print("✅ Done! Output video:", unique_out)

    finally:
        # Cleanup temp folders
        print("🧹 Cleaning up temporary directories...")
        for folder in temp_folders:
            clear_directory(folder)
        print("✅ Cleanup complete.")

# ---------------------------------------------------------
# Additional helper functions for main()
# ---------------------------------------------------------
def get_video_frame_count(video_path):
    """
    Use ffprobe to get the total frame count in the original video.
    """
    cmd = [
        "ffprobe", "-v", "error", "-count_frames",
        "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames",
        "-of", "csv=p=0", video_path
    ]
    try:
        out = subprocess.check_output(cmd, text=True).strip()
        return int(out)
    except Exception as e:
        print(f"❌ Error getting frame count: {e}")
        # Fallback to counting extracted frames
        temp_frames_folder = "temp_frame_count"
        extract_frames(video_path, temp_frames_folder)
        count = count_frames_in_folder(temp_frames_folder)
        clear_directory(temp_frames_folder)
        return count

def get_video_fps(video_path):
    """
    Use ffprobe to parse the average frame rate (avg_frame_rate).
    """
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=avg_frame_rate",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    raw = subprocess.check_output(cmd, text=True).strip()
    try:
        num, den = raw.split("/")
        return float(num) / float(den)
    except:
        print("⚠️ Could not parse FPS, defaulting to 30.0")
        return 30.0

# ---------------------------------------------------------
# Run if main
# ---------------------------------------------------------
if __name__ == "__main__":
    main()
