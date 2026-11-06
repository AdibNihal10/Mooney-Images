"""
summarize_results.py — turn the 4 metrics.csv files into numbers + pictures for the slides.

Run after the four run_*.py scripts:

    python summarize_results.py

Creates in ../slides_assets/:
    summary.csv               Original vs Mooney, one row per metric
    summary_by_light.csv      same, split by light direction L0..L4 (useful for Part 3)
    summary_chart.png         4 small bar charts, Original vs Mooney
    panel_Result1.png ...     for the 10 Subset images: original | result | Mooney | result
"""

import csv
from pathlib import Path

import cv2
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "slides_assets"
COLORS = {"Original": "#2a78d6", "Mooney": "#eb6834"}     # validated colour-blind-safe pair

# (result folder, system name, metric column, label, "higher is better"?)
METRICS = [
    ("Result1", "Depth Anything V2", "spearman", "Depth: Spearman ρ vs GT", True),
    ("Result1", "Depth Anything V2", "absrel", "Depth: AbsRel vs GT", False),
    ("Result2", "Marigold normals", "mean_angular_error_deg", "Normals: angular error (°)", False),
    ("Result3", "CLIP ViT-L/14", "top1_correct", "CLIP: top-1 accuracy", True),
    ("Result3", "CLIP ViT-L/14", "top3_correct", "CLIP: top-3 accuracy", True),
    ("Result4", "Qwen3-VL", "auto_correct", "VLM: names object correctly", True),
]
CHART_METRICS = ["spearman", "mean_angular_error_deg", "top1_correct", "auto_correct"]


def read_metrics(result):
    f = ROOT / result / "metrics.csv"
    if not f.exists():
        return None
    with open(f, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def mean(rows, col, split, light=None):
    vals = []
    for r in rows:
        if r["split"] != split or (light is not None and not r["file"].endswith(f"_L{light}.png")):
            continue
        try:
            v = float(r[col])
        except (ValueError, KeyError):
            continue
        if not np.isnan(v):
            vals.append(v)
    return float(np.mean(vals)) if vals else float("nan")


def write_summaries(data):
    OUT.mkdir(exist_ok=True)
    with open(OUT / "summary.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["system", "metric", "higher_is_better", "Original", "Mooney"])
        for res, name, col, label, hib in METRICS:
            if data.get(res):
                w.writerow([name, label, hib, round(mean(data[res], col, "Original"), 3),
                            round(mean(data[res], col, "Mooney"), 3)])
    with open(OUT / "summary_by_light.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["system", "metric", "split"] + [f"L{k}" for k in range(5)])
        for res, name, col, label, _ in METRICS:
            if data.get(res):
                for split in ("Original", "Mooney"):
                    w.writerow([name, label, split] + [round(mean(data[res], col, split, k), 3) for k in range(5)])
    print(f"Wrote {OUT / 'summary.csv'} and summary_by_light.csv")


def chart(data):
    chosen = [m for m in METRICS if m[2] in CHART_METRICS and data.get(m[0])]
    if not chosen:
        return
    plt.rcParams.update({"font.size": 10, "axes.edgecolor": "#c9c8c2", "axes.labelcolor": "#3d3d3a",
                         "xtick.color": "#3d3d3a", "ytick.color": "#6b6a64"})
    fig, axes = plt.subplots(1, len(chosen), figsize=(3.2 * len(chosen), 3.4), facecolor="#fcfcfb")
    axes = np.atleast_1d(axes)
    for ax, (res, name, col, label, hib) in zip(axes, chosen):
        vals = [mean(data[res], col, s) for s in ("Original", "Mooney")]
        bars = ax.bar(["Original", "Mooney"], vals, width=0.5,
                      color=[COLORS["Original"], COLORS["Mooney"]], edgecolor="#fcfcfb", linewidth=2)
        for b, v in zip(bars, vals):
            ax.annotate(f"{v:.2f}", (b.get_x() + b.get_width() / 2, v), ha="center", va="bottom",
                        xytext=(0, 3), textcoords="offset points", color="#1f1f1d", fontsize=10)
        ax.set_title(f"{label}\n({'higher' if hib else 'lower'} is better)", fontsize=10, color="#1f1f1d")
        ax.set_facecolor("#fcfcfb")
        ax.grid(axis="y", color="#e6e5e0", linewidth=0.8)
        ax.set_axisbelow(True)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        top = np.nanmax(vals) if not np.all(np.isnan(vals)) else 1
        if col in ("spearman", "top1_correct", "top3_correct", "auto_correct"):
            ax.set_ylim(0, 1.12)                 # these live on a 0..1 scale
            ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
        else:
            ax.set_ylim(0, top * 1.2 if top > 0 else 1)
    fig.tight_layout()
    fig.savefig(OUT / "summary_chart.png", dpi=200)
    print(f"Wrote {OUT / 'summary_chart.png'}")


# ----------------------------- picture panels ------------------------------
def load_tile(path, size=180):
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        return np.full((size, size, 3), 60, np.uint8)
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:
        img = (img[:, :, :3] * (img[:, :, 3:4] / 255.0)).astype(np.uint8)
    return cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA)


def text_tile(lines, size=180):
    tile = np.full((size, size, 3), 250, np.uint8)
    for i, line in enumerate(lines[:7]):
        cv2.putText(tile, line[:24], (6, 24 + 22 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                    (30, 30, 30), 1, cv2.LINE_AA)
    return tile


def result_tile(res, split, stem, rows):
    folder = ROOT / res / split
    if (folder / f"{stem}.png").exists():                       # depth / normals
        return load_tile(folder / f"{stem}.png")
    row = next((r for r in rows if r["split"] == split and r["file"].startswith(stem)), None)
    if row is None:
        return text_tile(["(no result)"])
    if "top1" in row:                                             # CLIP
        return text_tile(["CLIP top-1:", row["top1"], f"p(true)={float(row['p_true']):.2f}",
                          "correct" if row["top1_correct"] == "1" else "WRONG"])
    ans = row["object_answer"]                                    # VLM
    return text_tile(["VLM says:"] + [ans[i:i + 22] for i in range(0, min(len(ans), 88), 22)]
                     + ["correct" if row["auto_correct"] == "1" else "WRONG"])


def panels(data):
    subset = sorted((ROOT / "Subset" / "Original").glob("*.png"))
    if not subset:
        print("No Subset/Original images yet -> skipping picture panels")
        return
    for res in ("Result1", "Result2", "Result3", "Result4"):
        if not data.get(res):
            continue
        rows_img = []
        for f in subset:
            row = [load_tile(ROOT / "Original" / f.name), result_tile(res, "Original", f.stem, data[res]),
                   load_tile(ROOT / "Mooney" / f.name), result_tile(res, "Mooney", f.stem, data[res])]
            rows_img.append(np.hstack([np.pad(t, ((3, 3), (3, 3), (0, 0)), constant_values=255) for t in row]))
        # two columns of 5 images keep the panel slide-shaped
        half = (len(rows_img) + 1) // 2
        left, right = rows_img[:half], rows_img[half:]
        right += [np.full_like(rows_img[0], 255)] * (len(left) - len(right))
        header = np.full((34, rows_img[0].shape[1], 3), 255, np.uint8)
        for j, t in enumerate(["Original", "Result", "Mooney", "Result"]):
            cv2.putText(header, t, (10 + j * 186, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 1, cv2.LINE_AA)
        panel = np.hstack([np.vstack([header] + left), np.full((34 + sum(r.shape[0] for r in left), 20, 3), 255, np.uint8),
                           np.vstack([header] + right)])
        cv2.imwrite(str(OUT / f"panel_{res}.png"), panel)
        print(f"Wrote {OUT / f'panel_{res}.png'}")


def main():
    data = {r: read_metrics(r) for r in ("Result1", "Result2", "Result3", "Result4")}
    if not any(data.values()):
        raise SystemExit("No Result*/metrics.csv found. Run the run_*.py scripts first.")
    write_summaries(data)
    chart(data)
    panels(data)


if __name__ == "__main__":
    main()
