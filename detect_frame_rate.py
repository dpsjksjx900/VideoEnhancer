import os
import sys
import re

# Auto-install missing dependencies
try:
    import cv2
    import numpy as np
except ImportError:
    print("🔄 Required libraries missing. Installing now...")
    os.system(f"{sys.executable} -m pip install opencv-python numpy")
    import cv2
    import numpy as np  # Import again after installation

from collections import Counter
from statistics import median

def read_image_unicode(image_path):
    """Reads an image while handling Unicode paths properly."""
    try:
        with open(image_path, "rb") as file:
            file_bytes = np.asarray(bytearray(file.read()), dtype=np.uint8)
            image = cv2.imdecode(file_bytes, cv2.IMREAD_GRAYSCALE)
        return image
    except Exception as e:
        return None  # Return None if reading fails

def extract_frame_number(filename):
    """Extracts the largest number from a filename to handle different naming conventions."""
    numbers = re.findall(r'\d+', filename)  # Find all numbers in filename
    return int(numbers[-1]) if numbers else None  # Use the last number found

def get_frame_differences(frame_dir, threshold=5):
    """Detects unique frames by calculating pixel-wise differences."""
    frame_files = sorted(
        [f for f in os.listdir(frame_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    )

    if not frame_files:
        return [], [], []

    # Extract frame numbers for sorting
    frame_files = sorted(frame_files, key=lambda x: extract_frame_number(x) or float('inf'))

    unique_frames = [frame_files[0]]  # First frame is always unique
    prev_frame_path = os.path.join(frame_dir, frame_files[0])
    prev_frame = read_image_unicode(prev_frame_path)

    if prev_frame is None:
        return [], [], []

    frame_indices = [extract_frame_number(f) for f in frame_files if extract_frame_number(f) is not None]
    unique_indices = [frame_indices[0]]  # Store unique frame indices

    for i in range(1, len(frame_files)):
        current_frame_path = os.path.join(frame_dir, frame_files[i])
        current_frame = read_image_unicode(current_frame_path)

        if current_frame is None:
            continue  # Skip unreadable frames

        diff = cv2.absdiff(prev_frame, current_frame)
        mean_diff = np.mean(diff)

        if mean_diff > threshold:
            unique_frames.append(frame_files[i])  # Consider as a new frame
            unique_indices.append(frame_indices[i])

        prev_frame = current_frame

    return unique_frames, unique_indices, frame_indices

def estimate_frame_duplication_rate(frame_dir, threshold):
    """
    Estimates the frame rate duplication factor by comparing total frames to unique frames.
    Returns the duplication rate as a decimal.
    """
    unique_frames, unique_indices, all_indices = get_frame_differences(frame_dir, threshold)
    if not unique_frames or not all_indices:
        return None

    total_frames = len(all_indices)  # Total frame count
    unique_frame_count = len(unique_frames)  # Unique frame count

    duplication_rate = total_frames / unique_frame_count

    if duplication_rate < 1.0:
        duplication_rate = 1.0  # Ensure no values below 1.0

    return duplication_rate

if __name__ == "__main__":
    # Allow directory input via command-line argument
    if len(sys.argv) > 1:
        frame_directory = sys.argv[1]
        threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 5  # Allow optional threshold input

        if not os.path.exists(frame_directory):
            sys.exit("Error: Directory does not exist.")
        
        duplication_rate = estimate_frame_duplication_rate(frame_directory, threshold)
        if duplication_rate is not None:
            print(duplication_rate)  # **Returns only the decimal value**
        else:
            sys.exit("Error: Could not determine duplication rate.")

    else:
        # Interactive mode (Explain duplication rate)
        frame_directory = input("📁 Enter the directory containing frames: ").strip()

        if not os.path.exists(frame_directory):
            print("❌ Error: Directory does not exist.")
        else:
            try:
                threshold = float(input("🔧 Enter the difference threshold (default: 5): ") or 5)
            except ValueError:
                print("❌ Invalid threshold! Using default value (5).")
                threshold = 5

            duplication_rate = estimate_frame_duplication_rate(frame_directory, threshold)
            if duplication_rate is not None:
                print(f"🔄 The detected frame duplication rate is: {duplication_rate}")
            else:
                print("⚠️ Could not determine frame duplication rate.")
