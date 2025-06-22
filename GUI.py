import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox

def install_dependencies():
    """Runs the installation script for RIFE and FFmpeg."""
    subprocess.run(["python", "install_requirements.py"], check=True)
    # messagebox.showinfo("Installation", "Dependencies installed successfully!")

def select_video():
    """Opens file dialog to select input video."""
    file_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4;*.avi;*.mkv")])
    input_video_entry.delete(0, tk.END)
    input_video_entry.insert(0, file_path)
    update_output_filename()

def select_output():
    """Opens file dialog to select output video location."""
    file_path = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 files", "*.mp4")])
    output_video_entry.delete(0, tk.END)
    output_video_entry.insert(0, file_path)

def update_output_filename(*args):
    """Updates the output filename based on selected parameters."""
    input_video = input_video_entry.get()
    if not input_video:
        return
    
    base_name = os.path.splitext(os.path.basename(input_video))[0]
    param_string = f"_fps{fps_factor_var.get()}_{model_var.get()}"
    output_name = f"{base_name}{param_string}.mp4"
    output_video_entry.delete(0, tk.END)
    output_video_entry.insert(0, os.path.join(os.path.dirname(input_video), output_name))
    parameters_label.config(text=f"Parameters: {param_string}")

def get_available_gpus():
    """Detects available GPUs using nvidia-smi."""
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=index,name", "--format=csv,noheader"], capture_output=True, text=True, check=True)
        gpus = [line.split(',')[0].strip() for line in result.stdout.splitlines()]
        return gpus
    except Exception:
        return []

def load_models():
    """Loads available models from the RIFE directory."""
    model_dir = os.path.join(os.getcwd(), "rife-ncnn-vulkan")
    if not os.path.exists(model_dir):
        messagebox.showerror("Error", "RIFE directory not found.")
        return []
    return [d for d in os.listdir(model_dir) if os.path.isdir(os.path.join(model_dir, d))]

def is_valid_fps_factor(model, fps_factor):
    # """Checks if the given fps_factor is valid for the selected model."""
    # valid_fps_factors = {2, 4, 8, 16, 32, 64, 128}
    # if "rife-v4" not in model and fps_factor not in valid_fps_factors:
    #     return False
    return True

def run_interpolation():
    """Executes the interpolation script with user-specified parameters."""
    input_video = input_video_entry.get()
    output_video = output_video_entry.get()
    model = model_var.get()
    fps_factor = fps_factor_var.get()
    gpu_id = gpu_var.get()
    tta = "--tta" if tta_var.get() else ""
    uhd = "--uhd" if uhd_var.get() else ""
    remove_duplicates = "--remove_duplicates" if remove_duplicates_var.get() else ""
    
    if not is_valid_fps_factor(model, fps_factor):
        messagebox.showerror("Error", "Selected model does not support the chosen FPS factor. Use 2, 4, 8, 16, 32, etc. for non-rife-v4 models.")
        return
    
    if not input_video or not output_video:
        messagebox.showerror("Error", "Please select input and output videos.")
        return
    
    command = [
        "python", "interpolate_video.py", input_video, output_video,
        "--model", model,
        "--fps_factor", str(fps_factor)
    ]
    
    if gpu_id != "Auto":
        command.extend(["--gpu_id", str(gpu_id)])
    if tta:
        command.append(tta)
    if uhd:
        command.append(uhd)
    if remove_duplicates:
        command.append(remove_duplicates)
    
    print("Running command:", " ".join(command))
    subprocess.run(command, check=True)
    messagebox.showinfo("Interpolation", "Video interpolation completed!")


install_dependencies()

# Initialize Tkinter GUI
root = tk.Tk()
root.title("RIFE Video Interpolation GUI")
root.geometry("600x500")

# Input Video Selection
tk.Label(root, text="Input Video:").pack()
input_video_entry = tk.Entry(root, width=50)
input_video_entry.pack()
tk.Button(root, text="Browse", command=select_video).pack()

# Output Video Entry
tk.Label(root, text="Output Video:").pack()
output_video_entry = tk.Entry(root, width=50)
output_video_entry.pack()
tk.Button(root, text="Browse", command=select_output).pack()

# Parameters Display
parameters_label = tk.Label(root, text="Parameters: ")
parameters_label.pack()

# Model Selection
tk.Label(root, text="RIFE Model:").pack()
models = load_models()
model_var = tk.StringVar(value="rife-v4.6" if "rife-v4.6" in models else (models[0] if models else "No Models Found"))
model_dropdown = tk.OptionMenu(root, model_var, *models, command=update_output_filename)
model_dropdown.pack()

# FPS Factor
tk.Label(root, text="FPS Factor:").pack()
fps_factor_var = tk.IntVar(value=2)
fps_spinbox = tk.Spinbox(root, from_=1, to=8, textvariable=fps_factor_var, command=update_output_filename)
fps_spinbox.pack()

# GPU ID
tk.Label(root, text="GPU ID:").pack()
gpu_var = tk.StringVar(value="Auto")
tk.OptionMenu(root, gpu_var, "Auto", "0", "1", "2", "-1 (CPU)").pack()

# Extra Options
tta_var = tk.BooleanVar()
tk.Checkbutton(root, text="Enable TTA Mode", variable=tta_var, command=update_output_filename).pack()
uhd_var = tk.BooleanVar()
tk.Checkbutton(root, text="Enable UHD Mode", variable=uhd_var, command=update_output_filename).pack()
remove_duplicates_var = tk.BooleanVar()
tk.Checkbutton(root, text="Remove Duplicate Frames", variable=remove_duplicates_var).pack()

# Run Button
tk.Button(root, text="Start Interpolation", command=run_interpolation).pack(pady=10)

root.mainloop()
