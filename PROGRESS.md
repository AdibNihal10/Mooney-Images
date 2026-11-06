# CompVP Part 1: progress

Last updated: 6 Nov 2026, 23:26
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
- **`Mooney/` and `mooney/` are the same folder on Windows.** The Mooney batch in step 4 will write its 100
  PNGs and `mooney_log.csv` next to the tool's scripts. `.gitignore` handles this, but the team has not yet
  decided whether to rename the tool folder. Decide before step 4.
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
4. **Mooney batch and sheet**, from `mooney/`:
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
