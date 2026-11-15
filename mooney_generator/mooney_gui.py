"""
mooney_gui.py — a small web GUI for the Mooney tool (built with Gradio).

    pip install gradio opencv-python numpy
    python mooney_gui.py            # opens http://127.0.0.1:7860 in your browser
    python mooney_gui.py --share    # public link (useful on Google Colab)

Tab 1 "Single image": upload an image, move the sliders, see the result live.
Tab 2 "Batch":        point it at a folder (e.g. Original/) and convert all
                      images with the chosen settings into another folder.

All image processing lives in mooney_tool.py; this file is only the interface.

Relative folder names in the Batch tab are resolved against the PROJECT ROOT
(the parent of mooney_generator/), not the folder the GUI was started from.
The batch tab never overwrites the real Mooney/ folder with different images:
it refuses and shows a warning instead (regenerate Mooney/ with mooney_tool.py).
"""

import argparse
import os
from pathlib import Path

import cv2
import gradio as gr
import numpy as np

from mooney_tool import list_images, load_gray_and_mask, make_mooney, process, to_gray_and_mask

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROTECTED_DIR = PROJECT_ROOT / "Mooney"


def resolve_dir(folder):
    """Absolute paths stay as they are; relative ones are taken from the project root."""
    p = Path(str(folder).strip()).expanduser()
    return (p if p.is_absolute() else PROJECT_ROOT / p).resolve()


def same_dir(a, b):
    """Path comparison that ignores case on Windows (Mooney == mooney there)."""
    return os.path.normcase(str(Path(a).resolve())) == os.path.normcase(str(Path(b).resolve()))


def compare_with_existing(in_dir, out_dir, sigma, white_pct, use_alpha, ksize):
    """Generate every Mooney in memory and compare it with the file already in out_dir.
    Returns a list of output names that are missing or different."""
    changed = []
    for f in list_images(in_dir):
        gray, mask = load_gray_and_mask(f)
        mooney, *_ = make_mooney(gray, sigma, white_pct, mask if use_alpha else None, ksize)
        existing = cv2.imread(str(out_dir / (f.stem + ".png")), cv2.IMREAD_GRAYSCALE)
        if existing is None or existing.shape != mooney.shape or not np.array_equal(existing, mooney):
            changed.append(f.stem + ".png")
    return changed


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
    ksize = 7 if paper_kernel else None
    try:
        src, dst = resolve_dir(in_dir), resolve_dir(out_dir)
        if not src.exists():
            return f"Error: input folder not found: `{src}`", []
        if same_dir(dst, PROTECTED_DIR):
            changed = compare_with_existing(src, dst, sigma, white_pct, use_alpha, ksize)
            if changed:
                return (f"⚠️ **Refused: nothing was written.** `{dst}` holds the agreed Mooney set, and "
                        f"{len(changed)} of {len(list_images(src))} images would change with these settings "
                        f"(first: {changed[0]}). Use another output folder, e.g. `Mooney_test`. "
                        "To regenerate the real set on purpose, use `mooney_tool.py` from the command line."), []
            rows = [[f.name, f.stem + ".png"] for f in list_images(src)]
            msg = (f"`{dst}` already matches these settings exactly ({len(rows)} images), "
                   "so nothing was written.")
        else:
            rows = process(src, dst, sigma, white_pct, use_alpha, ksize, verbose=False)
            msg = f"Converted {len(rows)} images -> `{dst}` (log: `{dst / 'mooney_log.csv'}`)"
    except (SystemExit, Exception) as e:   # show errors in the UI instead of crashing
        return f"Error: {e}", []
    # images as arrays, so Gradio can show them wherever the folder is
    gallery = [(cv2.imread(str(dst / r[1]), cv2.IMREAD_GRAYSCALE), r[1]) for r in rows[:24]]
    return msg, gallery


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
                in_dir = gr.Textbox(value="Original", label="Input folder (relative = from project root)")
                out_dir = gr.Textbox(value="Mooney_test", label="Output folder (relative = from project root)")
            gr.Markdown(f"Project root: `{PROJECT_ROOT}`. The real `Mooney/` folder is protected: "
                        "a batch into it is refused if any image would change.")
            btn = gr.Button("Convert all images", variant="primary")
            status = gr.Markdown()
            gallery = gr.Gallery(label="First results", columns=6, height="auto")
            btn.click(run_batch, [in_dir, out_dir] + settings, [status, gallery])
    return app


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--share", action="store_true", help="create a public link (Colab)")
    build_app().launch(share=ap.parse_args().share)
