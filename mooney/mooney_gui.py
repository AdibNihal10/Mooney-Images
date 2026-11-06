"""
mooney_gui.py — a small web GUI for the Mooney tool (built with Gradio).

    pip install gradio opencv-python numpy
    python mooney_gui.py            # opens http://127.0.0.1:7860 in your browser
    python mooney_gui.py --share    # public link (useful on Google Colab)

Tab 1 "Single image": upload an image, move the sliders, see the result live.
Tab 2 "Batch":        point it at a folder (e.g. Original/) and convert all
                      images with the chosen settings into another folder.

All image processing lives in mooney_tool.py; this file is only the interface.
"""

import argparse

import cv2
import gradio as gr
import numpy as np

from mooney_tool import make_mooney, process, to_gray_and_mask


def preview(image_rgba, sigma, white_pct, use_alpha, paper_kernel):
    """Called every time the image or a slider changes."""
    if image_rgba is None:
        return None, None, "Upload an image to start."
    bgra = cv2.cvtColor(image_rgba, cv2.COLOR_RGBA2BGRA)
    gray, mask = to_gray_and_mask(bgra)
    if mask is not None and mask.all():
        mask = None                      # no real transparency in this image
    ksize = 7 if paper_kernel else None
    mooney, blurred, t, actual = make_mooney(
        gray, sigma, white_pct, mask if use_alpha else None, ksize)
    info = (f"threshold = {t:.1f}   |   white pixels = {actual:.1f}% "
            f"(target {white_pct:.0f}%)   |   kernel = {'7x7' if ksize else 'auto'}"
            + ("   |   measured on object only" if use_alpha and mask is not None else ""))
    return np.clip(blurred, 0, 255).astype(np.uint8), mooney, info


def run_batch(in_dir, out_dir, sigma, white_pct, use_alpha, paper_kernel):
    try:
        rows = process(in_dir, out_dir, sigma, white_pct, use_alpha,
                       7 if paper_kernel else None, verbose=False)
    except (SystemExit, Exception) as e:   # show errors in the UI instead of crashing
        return f"Error: {e}", []
    gallery = [f"{out_dir}/{r[1]}" for r in rows[:24]]
    return f"Converted {len(rows)} images -> {out_dir}/ (log: {out_dir}/mooney_log.csv)", gallery


def build_app():
    with gr.Blocks(title="Mooney Image Generator") as app:
        gr.Markdown("# Mooney Image Generator\n"
                    "Gaussian blur → threshold chosen so that a fixed % of pixels is white "
                    "(binary search, as in Egger et al.).")
        with gr.Row():
            sigma = gr.Slider(0, 40, value=3, step=0.5, label="Blur strength (sigma, px)")
            white = gr.Slider(1, 60, value=16, step=1, label="White pixels (%)")
        with gr.Row():
            use_alpha = gr.Checkbox(value=False, label="Count white % on object only (PNG alpha)")
            paper_kernel = gr.Checkbox(value=False, label="Paper kernel (fixed 7x7)")
        settings = [sigma, white, use_alpha, paper_kernel]

        with gr.Tab("Single image"):
            with gr.Row():
                inp = gr.Image(label="Original", type="numpy", image_mode="RGBA")
                blur_out = gr.Image(label="Blurred (grayscale)")
                moon_out = gr.Image(label="Mooney")
            info = gr.Markdown()
            for comp in [inp] + settings:
                comp.change(preview, [inp] + settings, [blur_out, moon_out, info])

        with gr.Tab("Batch"):
            with gr.Row():
                in_dir = gr.Textbox(value="Original", label="Input folder")
                out_dir = gr.Textbox(value="Mooney", label="Output folder")
            btn = gr.Button("Convert all images", variant="primary")
            status = gr.Markdown()
            gallery = gr.Gallery(label="First results", columns=6, height="auto")
            btn.click(run_batch, [in_dir, out_dir] + settings, [status, gallery])
    return app


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--share", action="store_true", help="create a public link (Colab)")
    build_app().launch(share=ap.parse_args().share)
