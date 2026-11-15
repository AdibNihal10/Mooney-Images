# CompVP Part 1: progress

Last updated: 12 Nov 2026, 20:30
Deadline: 20 Nov; upload to StudOn at the university by 18-19 Nov.

## Done
- Freed disk space (79 GB free on C: after the `pip-unpack-*` folders were deleted).
- Installed Python 3.12.10 and rebuilt `.venv` with it.
- Installed base packages: opencv-python, numpy, gradio, objaverse.
- Installed `torch 2.14.1+cu126` and `torchvision 0.29.1+cu126`.
- Downloaded the first 40 candidates and rendered `preview_sheet.png`.
- Copied the team's 16 picks to `render/meshes/`.
- Created `.gitignore`. `git init` has NOT been run (the team asked to wait).
- Blender 5.2 renders on the GTX 1650 through OptiX (confirmed in the first preview).

## Running when this was written
1. `pip install transformers diffusers accelerate matplotlib pillow`
2. GPU check, which runs right after that install.
3. Then, in order: download the 12 new candidates, render their preview sheet, and stop.

See "Latest status" at the bottom for how these turned out.

## Settings chosen
| Setting | Value |
|---|---|
| Python | 3.12 (3.14 caused package problems) |
| PyTorch | cu126 (driver 572.60 supports up to CUDA 12.8) |
| Final render | `--samples 32` (the script's default is 64) |
| Mooney | `--sigma 3 --white 30 --use-alpha` |
| Depth, CLIP | GPU |
| Marigold, Qwen | Test on GPU with `--fp32`; see step 6 for the fallback |

Blender path: `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`

## The 16 mesh picks (in `render/meshes/`)
Numbers refer to `preview_sheet.png`:
obj00 airplane, obj03 apple, obj05 banana, obj08 bottle, obj10 chair, obj13 cup,
obj15 guitar, obj16 hat, obj18 helmet, obj24 pear, obj26 pumpkin, obj29 shoe,
obj31 sofa, obj32 teapot, obj35 teddy_bear, obj37 toaster.

Dropped: bicycle, lamp, violin, mug.

## The 4 replacements still to pick
Categories: **bust, vase, pineapple, piggy_bank**, 3 candidates each (12 total).
- Meshes: `render/meshes_candidates2/`
- Previews: `preview_extra/`
- Sheet: `preview_extra_sheet.png`

Pick one per category, for 20 files total in `render/meshes/`.

Numbers refer to `preview_extra_sheet.png`:

| Sheet no. | File in `render/meshes_candidates2/` |
|---|---|
| obj00 | `bust__971482f2119e42a08a3da428ff5b3a29.glb` (Bust of Queen Margaret I of Denmark) |
| obj01 | `bust__bc3166936a574268b6c806159a1e45e0.glb` (Albin Herljevic, national hero bust) |
| obj02 | `bust__e2966085380f4c378b0e57d190ba5085.glb` (titled "bust") |
| obj03 | `piggy_bank__9531cdb48b8e4f728fb88eb24e17e027.glb` |
| obj04 | `piggy_bank__b2ea1501b04f481a8311cf8ad03a8bc3.glb` |
| obj05 | `piggy_bank__bcd2db39dcad4a488a66696b88ca67a5.glb` |
| obj06 | `pineapple__17f7e41a66af4603b47ec9f485e3bb8b.glb` |
| obj07 | `pineapple__1c77bd376c0940cab3ec72b037a6fc46.glb` |
| obj08 | `pineapple__d5eea4e95595496892ed15b711473cb2.glb` |
| obj09 | `vase__31139a065546483588ec923fe4e4361d.glb` |
| obj10 | `vase__b217bb1abb8e40beae7d3d29b9e283c7.glb` |
| obj11 | `vase__c3102c6cd57c4e60abe4ce9d0c3a41d3.glb` |

**Where the busts came from:** `bust` is not an Objaverse LVIS category, and `download_objects.py` would have
silently fallen back to `button`. So they came from a search of the LVIS statue, sculpture and figurine models
for titles containing the word "bust". That found 4; the first 3 were downloaded. The unused one is
`ce5c3a6781574d0093ee3b7b67d61851` (Bust of Sidonie Leblonde).

## Problems so far
- **Python 3.14:** the first venv used it and caused package problems, so it was replaced with 3.12.
- **Low memory:** the first PyTorch install was stopped automatically when RAM ran low. Keep heavy apps
  closed during long runs. Blender also took about 4 minutes to start during that period.
- **Low disk:** C: dropped to 4.5 GB during the first install. Now resolved.
- **Limited VRAM:** the GTX 1650 has 4 GB, and about 1.9 GB was in use with apps open. Marigold (~4 GB) and
  Qwen (~6 GB) may not fit. They are not tested yet.
- **Half precision:** GTX 16xx cards can give black/NaN output with it, so check outputs, not just exit codes.
- **`Mooney/` and `mooney/` were the same folder on Windows.** Fixed on 8 Nov: the code folder is now
  `mooney_generator/`, and the outputs live in their own `Mooney/` folder in the project root.
- **Numbering:** obj numbers are preview-specific. The final render renumbers objects, so identify meshes
  by file name.
- **`metadata.csv` is overwritten by every render**, including previews. It only matches `preview_sheet.png`
  until the next render. The final render writes the correct one.

## Next steps
Commands assume the venv: `.venv\Scripts\activate`

1. **Check "Latest status" below.** If the install, GPU check or preview did not finish, do those first.
2. **Copy the team's last 4 picks** from `render/meshes_candidates2/` to `render/meshes/`.
   Confirm there are exactly 20 files.
3. **Final render**, from `render/`:
   ```
   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b -P render_objects.py -- --meshes meshes --out ../Original --gt ../GT --samples 32
   ```
   Check for "Rendering on GPU via OPTIX" and 100 images in `Original/`.
4. **Mooney batch and sheet**, from `mooney_generator/`:
   ```
   python mooney_tool.py ../Original -o ../Mooney --sigma 3 --white 30 --use-alpha
   python ../tools/contact_sheet.py ../Original ../Mooney -o ../pairs_sheet.png --cols 10
   ```
5. **STOP: the team picks the top 10.** Copy them to `Subset/Original/` and `Subset/Mooney/` with the same
   file names.
6. **Smoke tests**, from `vision/`. Show the team a few outputs before any full run:
   ```
   python run_depth.py --limit 2
   python run_clip.py --limit 2
   python run_normals.py --limit 2 --fp32
   python run_vlm.py --limit 2 --fp32
   ```
   If Marigold or Qwen runs out of memory or gives black/garbage output, use `--device cpu`, or tell the
   team so they can use Colab.
7. **Full runs:** the same four commands without `--limit`, on whichever device passed step 6.
8. **Summary:** `python summarize_results.py` from `vision/`. Read `Result4/metrics.csv` by hand too,
   because the automatic check is strict.
9. **Zip:** `python make_submission.py --name CompVP_Part1_<TeamName>` from `tools/`.
   The team name is still needed. Save the md5 hash it prints.

## Latest status
Finished 6 Nov, about 23:40. Everything planned for tonight is done, with no errors:
- Install complete.
- GPU check: `2.14.1+cu126 True NVIDIA GeForce GTX 1650`, and a test calculation ran on `cuda:0`.
- 12 candidates downloaded and rendered on the GPU through OptiX. 73 GB free on C:.

**Stopped here: waiting for the team to pick the last 4 from `preview_extra_sheet.png`.**
Nothing past that point has been run, and the four vision models have not been tested yet.

## Update 8 Nov 2026, about 18:20
- Last 4 picks copied to `render/meshes/`: bust 02, piggy_bank 03, pineapple 08, vase 09. There are now exactly 20 meshes.
- Final render done in 14.5 min on the GPU (OptiX), `--samples 32`. It wrote 100 images to `Original/`, 200 files each
  in `GT/depth/` and `GT/normal/`, and a 100-row `metadata.csv`. Final numbering: obj00 airplane through obj19 vase,
  in alphabetical order.
- Mooney batch done (`--sigma 3 --white 30 --use-alpha`). Every image is 29.99-30.0% white.
- `pairs_sheet.png` made. Each object's originals sit above its Mooneys.
- Folder clash fixed: `git mv mooney mooney_generator` (not committed yet). The 100 PNGs and `mooney_log.csv` were
  moved into a separate `Mooney/` folder in the project root. GUIDE.md, PROGRESS.md and `.gitignore` were updated.

**Stopped here (step 5): waiting for the team to pick the top 10.**

## Update 8 Nov 2026, about 19:50 (Task 3, vision systems)

### Mooney/ was overwritten, then restored
At 18:58 a batch from the Mooney GUI overwrote the 100 Mooneys. The GUI was running from the old `mooney\` folder,
and its default output `Mooney` pointed at the same folder. That run used sigma 1, ksize 7, white 12% and no alpha.
The PNGs were silhouettes, so depth looked fine on them by mistake.
- That set is backed up in Claude's session scratchpad (`.../scratchpad/Mooney_gui_run_1858/`). It is temporary;
  regenerate it if it's needed.
- The agreed set was regenerated with `python mooney_generator/mooney_tool.py Original -o Mooney --sigma 3 --white 30 --use-alpha`
  (all 100 rows in the log are `3.0 auto 30.0 True`), so it matches `pairs_sheet.png` again.
- **Watch out:** the GUI's batch tab writes to `Mooney` relative to the folder it was started from. If it's started
  from the project root, a batch overwrites the real `Mooney/` folder. Use a test output folder in the GUI.
- Before any submission, check that `Mooney/mooney_log.csv` still shows sigma 3, white 30, use_alpha True.

### Results and measured times (GTX 1650, 4 GB VRAM, 13.9 GB RAM)
| System | Status | Device | Time |
|---|---|---|---|
| Result1 depth (Depth Anything V2 Small) | **FULL RUN DONE**, 200/200 | GPU fp16 | 78 s total (~0.3 s/img + load); first-ever run ~2 min with download |
| Result3 CLIP (ViT-L/14) | **FULL RUN DONE**, 200/200 | GPU | 1 min 52 s total (~0.4 s/img + load); first run ~5 min with 1.7 GB download |
| Result2 normals (Marigold v1-1) | **NOT WORKING YET** | see below | - |
| Result4 VLM (Qwen3-VL-2B) | **NOT TESTED** | - | - |

First numbers:
- Depth: mean Spearman on the object is 0.67 for originals and 0.17 for Mooneys. On the Mooney the model loses the
  airplane entirely; it only sees the background.
- CLIP: top-1 is 0.96 for originals and 0.44 for Mooneys; top-3 is 1.00 vs 0.60; mean p(true class) is 0.95 vs 0.37.

Marigold normals smoke test (`--limit 2`):
- **GPU fp16:** runs, but the output is **100% NaN** (the GTX 16xx half-precision bug). About 50 s per image, with
  VRAM at 3.75/4 GB and 99% GPU use. **Don't use it.**
- **GPU `--fp32`:** the model loaded at 19:40, but no image had finished after about 7 min. Claude Code then stopped
  it because system RAM was critically low (3.5 GB free). Most likely the fp32 weights don't fit in 4 GB of VRAM, so
  the driver spills into shared system RAM, which is very slow.
- **CPU:** not tried yet.
- Model cache: `~/.cache/huggingface/hub/models--prs-eth--marigold-normals-v1-1` (already downloaded).

### Next steps (tomorrow)
Close the GUI, browser and other heavy apps first, so there is enough free RAM.
1. Normals: try `python run_normals.py --limit 2 --device cpu` and time it. If it takes much over ~30 s per image,
   200 images is hours. Then also try `--steps 1` (Marigold v1-1 gives decent results in 1-4 steps), or use Colab.
   Check that the .npy has no NaNs:
   `python -c "import numpy as np; a=np.load('../Result2/Original/obj00_airplane_L0.npy'); print(np.isnan(a).mean())"`
2. VLM: `python run_vlm.py --limit 2 --fp32` (fp16 likely has the same NaN problem). The 2B model in fp32 is ~8 GB,
   so it won't fit in 4 GB of VRAM. Expect `--device cpu` or Colab. Check that the .txt answers aren't empty or garbage.
3. Full runs of normals and VLM on whatever works, then `summarize_results.py`.
4. Still waiting: the team's top-10 picks (for `Subset/`), and the team name for the zip.
5. Not committed yet: the `mooney` → `mooney_generator` rename and these doc edits.

## Update 12 Nov 2026, about 20:30 (Task 3, Marigold and Qwen tests)

### Main finding: the old fp32 "hang" was really a download
Only the **fp16** Marigold weights had been cached. Any `--fp32` or `--device cpu` run first downloads the fp32
UNet (~3.4 GB) silently, and on 8 Nov that download was still running when the job was killed. Today two abandoned
partial files (536 MB + 402 MB) were deleted and the fp32 weights were downloaded on their own (about 12 min over Wi-Fi).
The cache now has both fp16 and fp32 weights.

### Marigold normals (Result2) on the laptop, `--limit 2`
| Mode | Result | Time |
|---|---|---|
| GPU fp16 | 100% NaN output (8 Nov). Unusable. | ~50 s/img |
| GPU `--fp32` | **Works.** `obj00_airplane_L0` has 0% NaN and a sensible normal map. VRAM 3.85/4 GB, 100% GPU. | **~3 min 07 s/img** (+~1.5 min load) |
| CPU | Not measured. The first attempt was stuck in the download above. With only ~2 GB of RAM free, the fp32 model (~4-5 GB) would swap. | - |

The full run (200 images) at ~3 min/img is **about 10 h** on the GPU. That is over the 1.5 h limit, so it goes to **Colab**.
The fp32 smoke test was stopped by Claude Code after 1 image because system RAM ran critically low. Only
`Result2/Original/obj00_airplane_L0.{npy,png}` exist, and there is no `metrics.csv` yet.

### Qwen3-VL-2B (Result4)
**Not tested.** The download (4.26 GB, `model.safetensors`) was started alongside the Marigold test and stopped for
low RAM before it wrote anything. Sizes on this laptop:
- GPU fp16: 4.26 GB of weights > 4 GB VRAM (~1.1 GB already used by Windows/apps). It cannot fit. The GTX 1650 has no bf16.
- GPU `--fp32` / CPU: ~8.5 GB of weights, more than the free VRAM and the free RAM (~2 GB with Chrome, Discord, WhatsApp and VS Code open).
So it will almost certainly be over 1.5 h or not run at all. **Plan: Colab.**

### Laptop RAM is the real bottleneck
With the usual apps open there is only ~2 GB of RAM free out of 13.9 GB. Claude Code stops background jobs when
memory gets critical. Close Chrome, Discord and WhatsApp before any heavy local run, and never run a download and a model at the same time.

### Next steps
1. Colab (T4, 16 GB): `python run_normals.py` (fp16 should work on a T4, but check the NaN fraction first;
   use `--fp32` if needed) and `python run_vlm.py`. Copy `Result2/` and `Result4/` back into the project root.
2. Then `summarize_results.py`, and check `Result4/metrics.csv` by hand.
3. Still waiting: the team's top-10 (`Subset/`), the team name, and the commit of the `mooney_generator` rename and doc edits.

## Update 12 Nov 2026, about 20:50 (Colab package)
- `colab_upload.zip` (41.6 MB, in the project root, git-ignored) contains: `vision/*.py` (6), `Original/` (100 PNG),
  `Mooney/` (100 PNG + `mooney_log.csv`), `GT/depth/*.npy` (100) and `GT/normal/*.npy` (100). No GT PNGs, no `.venv`.
- `colab_vision.ipynb` (project root): 11 steps, covering the GPU check, Drive mount, unzip, pip install (Colab's torch is
  kept), Marigold `--limit 2` with a plot and NaN check, the full run, a Qwen `--limit 2` that prints the answers, the full
  run, and `results_colab.zip` saved to My Drive. The flag variables `NORMALS_FLAGS` and `VLM_FLAGS` switch to `--fp32` if fp16 gives NaN or garbage.
- **Not run on Colab yet.**

### After Colab
1. Download `results_colab.zip` from My Drive and unzip it into the project root. It replaces the 1-image `Result2/`
   from the laptop test and creates `Result4/`.
2. `python summarize_results.py` from `vision/`, and check `Result4/metrics.csv` by hand.
3. Write the Colab times per image into the table above.

## Update 15 Nov 2026 (Colab package re-checked)
- `colab_upload.zip` re-checked: 41.6 MB. Everything sits at the top level: `vision/` (6 .py), `Original/` (100 PNG), `Mooney/` (100 PNG + log),
  `GT/depth/` (100 .npy), `GT/normal/` (100 .npy). No `.venv`, no GT PNGs. Unchanged.
- `colab_vision.ipynb` fixed:
  - Step 9 had a broken f-string (a raw line break inside the string) that would have raised a SyntaxError on Colab. Fixed, and all code cells now parse.
  - The unzip target is now `/content/project` (it was `/content/compvp_part1`).
  - Qwen now uses `VLM_FLAGS = "--fp32"` by default. The T4 has no native bf16, and fp32 (~8.5 GB) fits in 16 GB.
  - Marigold still starts in fp16. If step 6 shows NaN, set `NORMALS_FLAGS = "--fp32"`.
- State: Result1 and Result3 are complete (200 outputs + `metrics.csv` each). Result2 has only the 1-image laptop test. Result4, `Subset/`
  and the team name are still missing.
- Still not committed: the `mooney_generator` rename, the doc edits and `colab_vision.ipynb`.
- **Not run on Colab yet.**
