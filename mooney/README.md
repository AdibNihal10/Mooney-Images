# Mooney Tool — CompVP Project Part 1, Task 2

## What it does
Original image → **grayscale** → **Gaussian blur** (sigma) → **threshold** so exactly
**X % of pixels are white** (binary search, as in Egger et al.). The result is a Mooney image.

- **sigma (blur)**: bigger = smoother blobs, fewer details. At 512×512 renders, try 2–6.
- **white %**: how much of the image turns white. The paper used 16%. For objects on a black background, try 20–35% with `--use-alpha`.
- **--use-alpha**: measure the white % on the object only (uses the PNG transparency from the 3D renders). The background stays black.
- **--ksize 7 --sigma 35**: the exact paper setting (a 7×7 kernel, so effectively a strong box-like blur).

## Install (once)
```bash
pip install opencv-python numpy gradio
```

## Run
```bash
# GUI (opens in your browser) — take the "screenshot of your tool" from here
python mooney_gui.py

# CLI, one image
python mooney_tool.py some_image.png -o test_out --sigma 3 --white 16

# CLI, batch: all 100 originals -> Mooney folder
python mooney_tool.py ../Original -o ../Mooney --sigma 3 --white 25 --use-alpha
```
Every run writes `mooney_log.csv` (threshold + actual white % per image) into the output folder.

## What makes a good Mooney (for picking the top 10)
- The object is recognizable, but only just (not trivially obvious).
- There are a few large, connected white regions, not speckle noise. If you see speckles, raise sigma.
- Hard shadows cut through the shape. That comes from the lighting in the render, not from this tool.
- The outline is NOT fully visible. If it looks like a silhouette, the light is too frontal.

## For the pptx ("screenshot of code that generates Mooneys")
Screenshot the functions `find_threshold` and `make_mooney` in `mooney_tool.py`.
