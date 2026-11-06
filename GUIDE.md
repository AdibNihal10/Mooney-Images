# CompVP Project Part 1 — Step-by-step guide

Deadline: **20 Nov** (upload at the university by 18–19 Nov).
Our plan: **20 everyday objects × 5 light directions = 100 renders** → 100 Mooneys → 4 vision systems.

```
compvp_part1/
├── render/   download_objects.py, render_objects.py   (Task 1)
├── mooney/   mooney_tool.py, mooney_gui.py             (Task 2)
├── tools/    contact_sheet.py                          (previews + slides)
├── vision/   (Task 3 scripts, coming next)
│
├── Original/   ← 100 renders appear here
├── Mooney/     ← 100 Mooneys appear here
├── GT/         ← ground-truth depth + normals (for us, not the zip)
└── metadata.csv
```

---

## 0. One-time setup (≈20 min)

0. Free disk space: you need **~20 GB free** (PyTorch + model weights ≈ 15 GB, plus renders/results).
1. Install **Python 3.11 or 3.12** (python.org), not 3.13/3.14, since some packages lag behind new Pythons. On Windows, tick "Add to PATH".
2. Install **Blender** (latest LTS, blender.org). It's free; we only use it from the command line.
3. Unzip `compvp_part1.zip`, open a terminal **inside the `compvp_part1` folder**, and run:
   ```bash
   python -m venv .venv
   # Windows:      .venv\Scripts\activate
   # Mac/Linux:    source .venv/bin/activate
   pip install opencv-python numpy gradio objaverse
   ```
   Do this activation step every time you open a new terminal.

---

## 1. Task 1 — get 3D objects and render 100 images

**1a. Download candidate meshes** (2 per category, 40 files):
```bash
cd render
python download_objects.py
```
If a category name isn't found, the script picks the closest match. To search names, run `python download_objects.py --list cup`.

**1b. Preview them** (1 render per mesh, fast). Replace the Blender path with yours:
```bash
# Windows example
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b -P render_objects.py -- --meshes meshes_candidates --out ../preview --no-gt --lights 1 --samples 16 --res 256
# Mac example
/Applications/Blender.app/Contents/MacOS/Blender -b -P render_objects.py -- --meshes meshes_candidates --out ../preview --no-gt --lights 1 --samples 16 --res 256

python ../tools/contact_sheet.py ../preview -o ../preview_sheet.png --cols 8
```
Open `preview_sheet.png`. For each category, copy the **better** of the two files into a new folder `render/meshes/`. Skip anything broken, flat, or a whole scene instead of one object. You need **exactly 20 files** in `meshes/`. If a category has no usable mesh, download another (`--categories kettle --candidates 3`).

**1c. Final render** (100 images + ground truth):
```bash
"<blender path>" -b -P render_objects.py -- --meshes meshes --out ../Original --gt ../GT
```
The script uses your NVIDIA GPU automatically. Check the first lines of the output for "Rendering on GPU via OPTIX/CUDA". Expect roughly 5–20 min.

What it does: each object is centred and scaled the same way. The camera is fixed. One sharp sun light comes from 5 directions (left, right, top-left, top-right, top), with zero ambient light and a black background. Hard shadows like these are what make good Mooneys (the paper uses extreme illumination for the same reason).

---

## 2. Task 2 — Mooney images

**2a. Tune the settings in the GUI.** Take your tool screenshot here too:
```bash
cd ../mooney
python mooney_gui.py
```
Load a few renders from `Original/` and tick "Count white % on object only". Good starting values are **sigma 2–4** and **white 25–35%**. Find settings where the object is recognizable but tricky.

**2b. Batch convert all 100** with the settings you chose:
```bash
python mooney_tool.py ../Original -o ../Mooney --sigma 3 --white 30 --use-alpha
```

**2c. Pick the top 10:**
```bash
python ../tools/contact_sheet.py ../Original ../Mooney -o ../pairs_sheet.png --cols 10
```
Look at the sheet as a team and choose 10 where the object is still guessable but the outline is broken up by shadow. Ideally pick a mix of objects and light directions. Copy those 10 files into `Subset/Original/` and `Subset/Mooney/` (same file names in both).

For the pptx, screenshot the `find_threshold` and `make_mooney` functions in `mooney_tool.py`.

---

## 3. Task 3 — four vision systems

| Result folder | System | What it tells us | Metric vs. our ground truth |
|---|---|---|---|
| Result1 | Depth Anything V2 (monocular depth) | Is 3D shape (near/far) recovered? | Spearman ρ + AbsRel vs GT depth |
| Result2 | Marigold normals (diffusion) | Is surface orientation recovered? (shape, the paper's key factor) | Mean angular error vs GT normals |
| Result3 | CLIP ViT-L/14 (zero-shot) | Which of the 20 objects is it? (invariance-style model, like VGG-Face in the paper) | Top-1/top-3 accuracy (chance = 5%) |
| Result4 | Qwen3-VL-2B (VLM) | What does it say it sees, with no hints? | Names the object correctly? |

Geometry vs. semantics is the story for the slides: does the model recover the *shape* from a Mooney, the *identity*, both, or neither?

**3.0 Install PyTorch with GPU support (once):**
1. Run `nvidia-smi` to see your GPU name and memory (VRAM).
2. Go to **pytorch.org/get-started** → choose Stable / your OS / Pip and a CUDA version **not higher than the "CUDA Version" shown in the top-right of `nvidia-smi`** (e.g. driver shows 12.8 → pick CUDA 12.6) → copy the command and run it inside the venv.
3. Then install the rest:
   ```bash
   pip install transformers diffusers accelerate matplotlib pillow
   ```
4. Check that PyTorch sees your GPU. This must print `True`:
   ```bash
   python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
   ```

**3.1 Smoke test first** (2 images per split, catches errors fast):
```bash
cd vision
python run_depth.py --limit 2
python run_clip.py --limit 2
python run_normals.py --limit 2
python run_vlm.py --limit 2
```
The first run of each script downloads the model weights: about 0.1 / 1.7 / 2 / 4.5 GB.

**3.2 Full runs** (all 100 originals + 100 Mooneys each):
```bash
python run_depth.py      # ~1–2 min
python run_clip.py       # ~2 min
python run_normals.py    # ~10–20 min
python run_vlm.py        # ~10–20 min
```
VRAM needs: depth/CLIP < 2 GB, Marigold ~4 GB, Qwen3-VL-2B ~6 GB. On GTX 16xx cards, half precision can give black/NaN outputs: add `--fp32` to `run_normals.py` / `run_vlm.py`, and always look at a few outputs rather than trusting a clean exit. If the VLM runs out of memory ("CUDA out of memory"), run `python run_vlm.py --device cpu` (slow but works) or use Google Colab for that one script.

**3.3 Summary numbers + slide pictures:**
```bash
python summarize_results.py
```
This writes `slides_assets/` with `summary.csv`, `summary_by_light.csv`, `summary_chart.png`, and `panel_Result1..4.png` (the 10 subset images: original | result | Mooney | result).

Also read through `Result4/metrics.csv` by hand. The automatic check is strict, so "cup" for a mug counts as wrong; say how you handled that in the slides.

---

## 4. Packaging + slides

**4.1 Slides.** Send me these, and I'll build the pptx in the required structure (title, approach, 10+10 images, systems, results per system, tool screenshot, code screenshot, AI declaration):
- the `slides_assets/` folder
- a GUI screenshot
- your team members' names
- the Mooney settings you chose
- 2–3 things *you* noticed in the results

**4.2 The zip:**
```bash
cd tools
python make_submission.py --name CompVP_Part1_<TeamName>
```
It checks the counts (100 / 100 / 10 / 10), that file names match, and that every Result folder is complete. It writes the zip into `compvp_part1/` and prints the **md5 hash**; save that hash. The raw `.npy` arrays are left out so the zip stays small.

**4.3 Upload to StudOn at the university by 18–19 Nov.** If the upload fails, send the md5 before the deadline and an alternative download link within 24 h.

---

## Staying in the driver seat (AI declaration)
The course allows AI if you can explain your work. For each script, make sure someone on the team can answer:
"what goes in, what comes out, which 2–3 parameters matter".
The docstring at the top of every file answers exactly that. In the AI declaration, write honestly that the code was written with Claude, and say what the team decided and checked: the object choice, Mooney settings, top-10 selection, and interpretation of results.
