import os
import argparse
import shutil
from glob import glob
from tqdm import tqdm

def get_image_files(folder):
    """Detects image files regardless of naming convention."""
    valid_extensions = (".png", ".jpg", ".jpeg")
    return sorted([f for f in os.listdir(folder) if f.lower().endswith(valid_extensions)])

def remove_duplicate_frames(input_folder, output_folder, duplicate_rate):
    """Removes duplicate frames based on the given duplicate rate."""
    frames = get_image_files(input_folder)

    if not frames:
        print("❌ No frames found in the folder!")
        return

    total_frames = len(frames)

    # ✅ Correct selection of frames based on duplicate_rate
    step = duplicate_rate
    selected_indices = [round(i * step) for i in range(int(total_frames / step))]
    selected_indices = list(dict.fromkeys(selected_indices))  # Remove duplicates

    frames_to_keep = [frames[i] for i in selected_indices if i < total_frames]

    # Create output folder safely
    if os.path.exists(output_folder):
        print(f"⚠️ Output folder '{output_folder}' already exists. Choose an action:")
        print("1️⃣ Overwrite existing folder")
        print("2️⃣ Create a new folder (output_1, output_2, etc.)")
        choice = input("Enter 1 or 2: ").strip()

        if choice == "1":
            shutil.rmtree(output_folder)
        elif choice == "2":
            count = 1
            while os.path.exists(output_folder):
                output_folder = os.path.join(os.path.dirname(output_folder), f"{os.path.basename(output_folder)}_{count}")
                count += 1
        else:
            print("❌ Invalid choice. Exiting.")
            return

    os.makedirs(output_folder, exist_ok=True)

    print(f"📂 Processing {total_frames} frames, keeping {len(frames_to_keep)} frames...")

    for frame in tqdm(frames_to_keep, desc="Processing"):
        shutil.copy(os.path.join(input_folder, frame), os.path.join(output_folder, frame))

    print(f"✅ Done! Kept {len(frames_to_keep)} frames. Output saved in: {output_folder}")

def main():
    parser = argparse.ArgumentParser(description="Remove duplicate frames based on a given duplicate rate.")
    parser.add_argument("--input_folder", type=str, help="Path to the folder containing frames.")
    parser.add_argument("--output_folder", type=str, help="Path to the folder where filtered frames will be saved.")
    parser.add_argument("--rate", type=float, help="Duplicate frame rate (e.g., 2.0, 1.25, 1.33).")

    args = parser.parse_args()

    if not args.input_folder:
        args.input_folder = input("📂 Enter the path to the folder containing frames: ").strip()

    if not args.output_folder:
        args.output_folder = input("📁 Enter the path for the output folder: ").strip()
    
    if not args.rate:
        try:
            args.rate = float(input("🔢 Enter the duplicate frame rate (e.g., 2.0, 1.25, 1.33): ").strip())
            if args.rate < 1.0:
                raise ValueError("Duplicate rate must be at least 1.0.")
        except ValueError:
            print("❌ Invalid duplicate rate! Must be a decimal number (e.g., 1.25, 2.0).")
            return

    remove_duplicate_frames(args.input_folder, args.output_folder, args.rate)

if __name__ == "__main__":
    main()
