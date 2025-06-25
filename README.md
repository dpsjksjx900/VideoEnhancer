VideoEnhancer provides scripts for video frame interpolation using RIFE and optional upscaling with multiple models including RealSR, waifu2x, RealESRGAN, SwinIR and diffusion-based pipelines. A simple Tkinter GUI is included to run the tools interactively.

## Installation

Install the required Python packages and fetch the RIFE, FFmpeg and upscaling binaries automatically:

```bash
pip install -r requirements.txt
python install_requirements.py
```

The `install_requirements.py` script now downloads the latest RealSR, waifu2x, RealESRGAN and SwinIR executables automatically. Diffusion model weights are fetched on first use.

## Interpolating Videos

`interpolate_video.py` extracts frames, removes duplicates, interpolates to the desired frame rate and reconstructs a new video. The output format can be selected with the `--output_format` option (mp4 or gif). Example:

```bash
python interpolate_video.py input.mp4 output.mp4 --model rife-v4.6 --fps_factor 2 --output_format mp4
```

## Upscaling Videos

`upscale_video.py` can upscale videos using RealSR, waifu2x, RealESRGAN, SwinIR or diffusion models such as SDx4 and LDSR. Specify the model name and output path:

```bash
python upscale_video.py input.mp4 output_upscaled.mp4 --model realsr --scale 2 --output_format mp4
```

Available models include `realsr`, `waifu2x`, `realesrgan`, `swinir`, `sdx4` and `ldsr`. RealSR and waifu2x support multiple internal models such as `realsr-x4plus` or `waifu2x-cunet`.

### GUI Usage

The Tkinter GUI (`GUI.py`) now exposes upscaling alongside interpolation. Select an input file, choose a RIFE model, enable the *Upscale* checkbox and pick the desired upscaler and model. When you click **Start**, the video will be interpolated and optionally upscaled using your chosen settings.

The GUI will automatically install RIFE and FFmpeg on first launch if they are missing. Use `python GUI.py --install` or choose **Tools → Install Dependencies** in the menu to run the installer manually.

## Example Commands

```bash
# Interpolate only
python interpolate_video.py src.mp4 out.gif --fps_factor 4 --output_format gif

# Upscale only
python upscale_video.py src.gif out_upscaled.gif --model sdx4 --scale 4 --output_format gif

# Interpolate then upscale
python interpolate_video.py src.mp4 temp.mp4 --fps_factor 2
python upscale_video.py temp.mp4 final.mp4 --model sdx4 --scale 4
```

