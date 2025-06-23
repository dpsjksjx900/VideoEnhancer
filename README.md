VideoEnhancer provides scripts for video frame interpolation using RIFE and optional upscaling with RealSR or waifu2x. A simple Tkinter GUI is included to run the tools interactively.

## Installation

Install the required Python packages and fetch the RIFE and FFmpeg binaries:

```bash
pip install -r requirements.txt
python install_requirements.py
```

For upscaling you need external binaries:

- **RealSR** – download the `realsr-ncnn-vulkan` release from [nihui/realsr-ncnn-vulkan](https://github.com/nihui/realsr-ncnn-vulkan/releases)
- **waifu2x** – download the `waifu2x-ncnn-vulkan` release from [nihui/waifu2x-ncnn-vulkan](https://github.com/nihui/waifu2x-ncnn-vulkan/releases)

Place the extracted folders next to the Python scripts or adjust your PATH so the executables are found.

## Interpolating Videos

`interpolate_video.py` extracts frames, removes duplicates, interpolates to the desired frame rate and reconstructs a new video. The output format can be selected with the `--output_format` option (mp4 or gif). Example:

```bash
python interpolate_video.py input.mp4 output.mp4 --model rife-v4.6 --fps_factor 2 --output_format mp4
```

## Upscaling Videos

`upscale_video.py` uses RealSR or waifu2x to increase the resolution of a video. The output format can also be chosen with `--output_format`. Specify the model name and output path:

```bash
python upscale_video.py input.mp4 output_upscaled.mp4 --model realsr-x4plus --output_format mp4
```

Available models include `realsr-x4plus`, `realsr-x4plus-anime`, `waifu2x-cunet` and `waifu2x-upresnet10`. Check the respective repositories for more model options.

### GUI Usage

The Tkinter GUI (`GUI.py`) now exposes upscaling alongside interpolation. Select an input file, choose a RIFE model, enable the *Upscale* checkbox and pick the desired upscaler and model. When you click **Start**, the video will be interpolated and optionally upscaled using your chosen settings.

## Example Commands

```bash
# Interpolate only
python interpolate_video.py src.mp4 out.gif --fps_factor 4 --output_format gif

# Upscale only
python upscale_video.py src.gif out_upscaled.gif --model waifu2x-cunet --output_format gif

# Interpolate then upscale
python interpolate_video.py src.mp4 temp.mp4 --fps_factor 2
python upscale_video.py temp.mp4 final.mp4 --model realsr-x4plus
```

