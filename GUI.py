import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "tkinterdnd2"], check=True)
        from tkinterdnd2 import DND_FILES, TkinterDnD
        HAS_DND = True
    except Exception:
        print("Drag-and-drop disabled. Install tkinterdnd2 for this feature.")
        HAS_DND = False

def install_dependencies():
    """Runs the installation script for RIFE and FFmpeg."""
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        subprocess.run([sys.executable, "install_requirements.py"], check=True)
    except subprocess.CalledProcessError:
        print("Failed to run install_requirements.py. Ensure requirements.txt packages are installed.")
    # messagebox.showinfo("Installation", "Dependencies installed successfully!")

def select_video():
    """Opens file dialog to select input video."""
    file_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4;*.avi;*.mkv;*.gif")])
    input_video_entry.delete(0, tk.END)
    input_video_entry.insert(0, file_path)
    update_output_filename()

def select_output():
    """Opens file dialog to select output video location."""
    ext = "." + output_format_var.get()
    filetypes = [("MP4 files", "*.mp4"), ("GIF files", "*.gif"), ("All Files", "*.*")]
    file_path = filedialog.asksaveasfilename(defaultextension=ext, filetypes=filetypes)
    output_video_entry.delete(0, tk.END)
    output_video_entry.insert(0, file_path)

def handle_input_drop(event):
    """Handle a file dropped onto the input entry."""
    if event.data:
        path = root.tk.splitlist(event.data)[0]
        input_video_entry.delete(0, tk.END)
        input_video_entry.insert(0, path)
        update_output_filename()

def handle_output_drop(event):
    """Handle a file dropped onto the output entry."""
    if event.data:
        path = root.tk.splitlist(event.data)[0]
        output_video_entry.delete(0, tk.END)
        output_video_entry.insert(0, path)

def update_output_filename(*args):
    """Updates the output filename based on selected parameters."""
    input_video = input_video_entry.get()
    if not input_video:
        return

    base_name = os.path.splitext(os.path.basename(input_video))[0]
    param_string = f"_fps{fps_factor_var.get()}_{model_var.get()}"
    ext = output_format_var.get()
    output_name = f"{base_name}{param_string}.{ext}"
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

def run_upscaling(video_path):
    """Runs optional video upscaling after interpolation."""
    method = upscale_method_var.get()
    scale = scale_factor_var.get()
    base, ext = os.path.splitext(video_path)
    upscaled_output = f"{base}_{method}_{scale}x{ext}"

    model_arg = method.lower()

    command = [
        sys.executable, "upscale_video.py", video_path, upscaled_output,
        "--model", model_arg,
        "--scale", str(scale),
        "--output_format", output_format_var.get()
    ]

    print("Running command:", " ".join(command))
    subprocess.run(command, check=True)
    messagebox.showinfo("Upscaling", "Video upscaling completed!")
    return upscaled_output

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
        sys.executable, "interpolate_video.py", input_video, output_video,
        "--model", model,
        "--fps_factor", str(fps_factor),
        "--output_format", output_format_var.get()
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

    final_output = output_video
    if upscale_var.get():
        final_output = run_upscaling(output_video)

    messagebox.showinfo("Done", f"Processing completed! Output: {final_output}")


install_dependencies()

# Initialize Tkinter GUI
root = TkinterDnD.Tk() if HAS_DND else tk.Tk()
root.title("RIFE Video Interpolation GUI")
root.geometry("650x600")

output_format_var = tk.StringVar(value="mp4")

# -------------------------------------------------
# Input Section
# -------------------------------------------------
input_frame = ttk.LabelFrame(root, text="Input Video")
input_frame.pack(fill="x", padx=10, pady=5)

ttk.Label(input_frame, text="Input Video:").pack(anchor="w")
input_video_entry = ttk.Entry(input_frame, width=50)
input_video_entry.pack(side="left", padx=5, pady=2, expand=True, fill="x")
ttk.Button(input_frame, text="Browse", command=select_video).pack(side="right", padx=5)

ttk.Label(input_frame, text="Output Video:").pack(anchor="w")
output_video_entry = ttk.Entry(input_frame, width=50)
output_video_entry.pack(side="left", padx=5, pady=2, expand=True, fill="x")
ttk.Button(input_frame, text="Browse", command=select_output).pack(side="right", padx=5)
ttk.Label(input_frame, text="Format:").pack(anchor="w")
format_menu = ttk.OptionMenu(input_frame, output_format_var, output_format_var.get(), "mp4", "gif", command=update_output_filename)
format_menu.pack(fill="x", pady=2)

if HAS_DND:
    input_video_entry.drop_target_register(DND_FILES)
    input_video_entry.dnd_bind("<<Drop>>", handle_input_drop)
    output_video_entry.drop_target_register(DND_FILES)
    output_video_entry.dnd_bind("<<Drop>>", handle_output_drop)

parameters_label = ttk.Label(input_frame, text="Parameters: ")
parameters_label.pack(anchor="w", pady=2)

# -------------------------------------------------
# Interpolation Section
# -------------------------------------------------
interpolation_frame = ttk.LabelFrame(root, text="Interpolation Options")
interpolation_frame.pack(fill="x", padx=10, pady=5)

ttk.Label(interpolation_frame, text="RIFE Model:").pack(anchor="w")
models = load_models()
model_var = tk.StringVar(value="rife-v4.6" if "rife-v4.6" in models else (models[0] if models else "No Models Found"))
model_dropdown = ttk.OptionMenu(interpolation_frame, model_var, model_var.get(), *models, command=update_output_filename)
model_dropdown.pack(fill="x", pady=2)

ttk.Label(interpolation_frame, text="FPS Factor:").pack(anchor="w")
fps_factor_var = tk.IntVar(value=2)
fps_spinbox = ttk.Spinbox(interpolation_frame, from_=1, to=8, textvariable=fps_factor_var, command=update_output_filename)
fps_spinbox.pack(fill="x", pady=2)

ttk.Label(interpolation_frame, text="GPU ID:").pack(anchor="w")
gpu_var = tk.StringVar(value="Auto")
ttk.OptionMenu(interpolation_frame, gpu_var, gpu_var.get(), "Auto", "0", "1", "2", "-1 (CPU)").pack(fill="x", pady=2)

tta_var = tk.BooleanVar()
ttk.Checkbutton(interpolation_frame, text="Enable TTA Mode", variable=tta_var, command=update_output_filename).pack(anchor="w")
uhd_var = tk.BooleanVar()
ttk.Checkbutton(interpolation_frame, text="Enable UHD Mode", variable=uhd_var, command=update_output_filename).pack(anchor="w")
remove_duplicates_var = tk.BooleanVar()
ttk.Checkbutton(interpolation_frame, text="Remove Duplicate Frames", variable=remove_duplicates_var).pack(anchor="w")

# -------------------------------------------------
# Upscaling Section
# -------------------------------------------------
upscale_frame = ttk.LabelFrame(root, text="Upscaling")
upscale_frame.pack(fill="x", padx=10, pady=5)

upscale_var = tk.BooleanVar()

def update_upscale_state(*args):
    state = "normal" if upscale_var.get() else "disabled"
    method_combo.configure(state=state)
    scale_combo.configure(state=state)

ttk.Checkbutton(upscale_frame, text="Enable Upscaling", variable=upscale_var, command=update_upscale_state).pack(anchor="w")

ttk.Label(upscale_frame, text="Method:").pack(anchor="w")
upscale_method_var = tk.StringVar(value="RealSR")
method_combo = ttk.Combobox(upscale_frame, textvariable=upscale_method_var, values=["RealSR", "Waifu2x"], state="disabled")
method_combo.pack(fill="x", pady=2)

ttk.Label(upscale_frame, text="Scale:").pack(anchor="w")
scale_factor_var = tk.IntVar(value=2)
scale_combo = ttk.Combobox(upscale_frame, textvariable=scale_factor_var, values=[2, 4], state="disabled")
scale_combo.pack(fill="x", pady=2)
update_upscale_state()

# -------------------------------------------------
# Run Button
# -------------------------------------------------
ttk.Button(root, text="Start", command=run_interpolation).pack(pady=10)

root.mainloop()
