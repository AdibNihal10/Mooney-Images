"""
build_slides.py: build slides/CompVP_Part1_<team>.pptx from the results.

    python slides/build_slides.py            (from the project root, in the venv)

Team name, member names and the course line come from slides/team.json.
Edit that file and rerun to change them (or edit the text in PowerPoint).

Needs: python-pptx, matplotlib, pillow, and the files written by
vision/summarize_results.py in slides_assets/ (plus gui.png and code.png).
"""

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "slides_assets"
BUILD = ASSETS / "slide_build"          # derived images (git-ignored with slides_assets/)
CFG = json.loads((ROOT / "slides" / "team.json").read_text(encoding="utf-8"))
OUT = ROOT / "slides" / f"CompVP_Part1_{CFG['team']}.pptx"

INK = RGBColor(0x1F, 0x23, 0x28)
MUTED = RGBColor(0x6B, 0x72, 0x7B)
BLUE = RGBColor(0x2A, 0x7A, 0xD6)       # Original (same as summary_chart.png)
ORANGE = RGBColor(0xE8, 0x6A, 0x33)     # Mooney
LINE = RGBColor(0xD8, 0xDC, 0xE0)
PALE = RGBColor(0xF4, 0xF6, 0xF8)
FONT = "Calibri"

SW, SH = Inches(13.333), Inches(7.5)
MARGIN = Inches(0.6)


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
def read_csv(name):
    with open(ASSETS / name, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


SUMMARY = read_csv("summary.csv")
BY_LIGHT = read_csv("summary_by_light.csv")
# Hand check of Result4/metrics.csv (see PROGRESS.md): synonyms such as mug/couch/statue
# count as right; strict = the automatic string match.
QWEN_LENIENT = {"Original": 0.96, "Mooney": 0.22}


def metric(label_start):
    return next(r for r in SUMMARY if r["metric"].startswith(label_start))


def light_row(label_start, split):
    r = next(r for r in BY_LIGHT if r["metric"].startswith(label_start) and r["split"] == split)
    return [float(r[f"L{k}"]) for k in range(5)]


# --------------------------------------------------------------------------
# Derived images
# --------------------------------------------------------------------------
def on_black(src, dst):
    """Originals are RGBA with a transparent background; show them on black like the Mooneys."""
    im = Image.open(src).convert("RGBA")
    bg = Image.new("RGBA", im.size, (0, 0, 0, 255))
    Image.alpha_composite(bg, im).convert("RGB").save(dst)
    return dst


def light_chart(path):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 13})
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), dpi=200)
    x = range(5)
    names = ["L0\nleft\nside", "L1\nright\nside", "L2\nupper\nleft", "L3\nupper\nright", "L4\nfrom\nabove"]
    panels = [("CLIP: top-1 accuracy", "CLIP top-1 accuracy (higher is better)", (0, 1.05)),
              ("Normals: angular error", "Normals: mean angular error, ° (lower is better)", (0, 50))]
    for ax, (key, title, ylim) in zip(axes, panels):
        for split, col in (("Original", "#2A7AD6"), ("Mooney", "#E86A33")):
            ys = light_row(key, split)
            ax.plot(x, ys, color=col, lw=2.5, marker="o", ms=8, zorder=3)
            ax.annotate(split, (4, ys[-1]), xytext=(10, 0), textcoords="offset points",
                        va="center", color="#1F2328", fontsize=13)
            for k, y in enumerate(ys):
                fmt = f"{y:.2f}" if ylim[1] < 2 else f"{y:.0f}°"
                ax.annotate(fmt, (k, y), xytext=(0, 10), textcoords="offset points",
                            ha="center", fontsize=11, color="#4A5058")
        ax.set_title(title, fontsize=14, color="#1F2328", pad=12)
        ax.set_xticks(list(x), names, fontsize=11)
        ax.set_ylim(*ylim)
        ax.set_xlim(-0.4, 4.9)
        ax.grid(axis="y", color="#E3E6E9", lw=1)
        ax.set_axisbelow(True)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color("#B0B5BA")
        ax.tick_params(colors="#4A5058", length=0)
    fig.tight_layout(w_pad=4)
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    return path


# --------------------------------------------------------------------------
# Slide helpers
# --------------------------------------------------------------------------
prs = Presentation()
prs.slide_width, prs.slide_height = SW, SH
BLANK = prs.slide_layouts[6]


def text(slide, x, y, w, h, runs, size=20, color=INK, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, spacing=1.0, after=0):
    """runs: a string, or a list of paragraphs; each paragraph is a string or a list of
    (text, {size, color, bold}) pieces."""
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.03)
    paras = [runs] if isinstance(runs, str) else runs
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        p.space_after = Pt(after)
        for piece in ([(para, {})] if isinstance(para, str) else para):
            t, st = piece
            r = p.add_run()
            r.text = t
            r.font.name = FONT
            r.font.size = Pt(st.get("size", size))
            r.font.bold = st.get("bold", bold)
            r.font.color.rgb = st.get("color", color)
    return tb


def title(slide, t, sub=None):
    text(slide, MARGIN, Inches(0.35), SW - 2 * MARGIN, Inches(0.7), t, size=32, bold=True)
    if sub:
        text(slide, MARGIN, Inches(0.98), SW - 2 * MARGIN, Inches(0.45), sub, size=17, color=MUTED)


def footer(slide, n):
    text(slide, SW - Inches(1.6), SH - Inches(0.45), Inches(1.1), Inches(0.3), str(n),
         size=11, color=MUTED, align=PP_ALIGN.RIGHT)
    text(slide, MARGIN, SH - Inches(0.45), Inches(6), Inches(0.3),
         f"Team {CFG['team']} · CompVP Part 1", size=11, color=MUTED)


def picture(slide, path, x, y, w=None, h=None, box=None):
    """Place an image. With box=(w, h) it is fitted inside and centred."""
    if box:
        iw, ih = Image.open(path).size
        bw, bh = box
        s = min(bw / iw, bh / ih)
        w, h = int(iw * s), int(ih * s)
        x, y = x + (bw - w) // 2, y + (bh - h) // 2
    return slide.shapes.add_picture(str(path), x, y, w, h)


def rect(slide, x, y, w, h, fill=PALE, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE):
    s = slide.shapes.add_shape(shape, x, y, w, h)
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
    s.shadow.inherit = False
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = 0.08
    return s


def arrow(slide, x1, y1, x2, y2):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
    c.line.color.rgb = MUTED
    c.line.width = Pt(2)
    ln = c.line._get_or_add_ln()
    tail = ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"})
    ln.append(tail)
    return c


def table(slide, x, y, w, rows, col_w, size=16, row_h=Inches(0.45), header_fill=INK):
    shp = slide.shapes.add_table(len(rows), len(rows[0]), x, y, w, row_h * len(rows))
    tbl = shp.table
    # plain look: no banding, no built-in style colours
    tblPr = tbl._tbl.tblPr
    tblPr.set("bandRow", "0")
    tblPr.set("firstRow", "1")
    for i, cw in enumerate(col_w):
        tbl.columns[i].width = cw
    for r, row in enumerate(rows):
        tbl.rows[r].height = row_h
        for c, val in enumerate(row):
            cell = tbl.cell(r, c)
            cell.fill.solid()
            cell.fill.fore_color.rgb = header_fill if r == 0 else (PALE if r % 2 == 0 else RGBColor(255, 255, 255))
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = cell.margin_right = Inches(0.1)
            cell.margin_top = cell.margin_bottom = Inches(0.03)
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = ""
            run = p.add_run()
            run.text = str(val)
            run.font.name = FONT
            run.font.size = Pt(size)
            run.font.bold = r == 0 or c == 0
            run.font.color.rgb = RGBColor(255, 255, 255) if r == 0 else INK
    return tbl


def new_slide(n, t=None, sub=None):
    s = prs.slides.add_slide(BLANK)
    if t:
        title(s, t, sub)
    if n > 1:
        footer(s, n)
    return s


def big_number(slide, x, y, w, label, before, after, note=None):
    text(slide, x, y, w, Inches(0.5), label, size=18, color=MUTED)
    text(slide, x, y + Inches(0.45), w, Inches(0.9),
         [[(before, {"color": BLUE}), ("  →  ", {"color": MUTED}), (after, {"color": ORANGE})]],
         size=44 if len(before + after) <= 9 else 34, bold=True)
    text(slide, x, y + Inches(1.3), w, Inches(0.35),
         [[("Original", {"color": BLUE}), ("   ", {}), ("Mooney", {"color": ORANGE})]], size=14)
    if note:
        text(slide, x, y + Inches(1.85), w, Inches(1.6), note, size=16, color=INK, spacing=1.1, after=6)


# --------------------------------------------------------------------------
# Slides
# --------------------------------------------------------------------------
def main():
    BUILD.mkdir(exist_ok=True)
    subset = sorted((ROOT / "Subset" / "Original").glob("*.png"))
    assert len(subset) == 10, f"expected 10 subset images, found {len(subset)}"
    n = 0

    # 1. Title
    n += 1
    s = new_slide(n)
    rect(s, 0, 0, Inches(0.35), SH, fill=ORANGE, shape=MSO_SHAPE.RECTANGLE)
    text(s, Inches(1.0), Inches(1.9), Inches(11.3), Inches(1.9),
         "Mooney Images: Do Pretrained Vision Models Generalize?", size=48, bold=True, spacing=0.95)
    text(s, Inches(1.0), Inches(3.95), Inches(11.3), Inches(0.5), CFG["course"], size=22, color=MUTED)
    text(s, Inches(1.0), Inches(5.0), Inches(11.3), Inches(0.5), f"Team {CFG['team']}", size=24, bold=True)
    text(s, Inches(1.0), Inches(5.5), Inches(11.3), Inches(0.5), " · ".join(CFG["members"]), size=22)

    # 2. Approach
    n += 1
    s = new_slide(n, "Approach")
    bullets = [
        [("100 renders: ", {"bold": True}), ("20 Objaverse objects × 5 hard sun-light directions (Blender), with GT depth + normals", {})],
        [("Mooney: ", {"bold": True}), ("grayscale → Gaussian blur (σ = 3) → threshold found by binary search so 30% of object pixels are white", {})],
        [("4 pretrained models, no fine-tuning, ", {"bold": True}), ("run on all 100 originals + 100 Mooneys", {})],
    ]
    text(s, MARGIN, Inches(1.35), SW - 2 * MARGIN, Inches(1.9), bullets, size=20, spacing=1.05, after=10)
    # pipeline: render -> Mooney -> 4 models -> compare
    eg = "obj07_guitar_L0.png"
    orig_img = on_black(ROOT / "Original" / eg, BUILD / f"black_{eg}")
    steps = [("Render", "Blender, 512×512\n+ GT depth/normals", orig_img),
             ("Mooney", "blur σ=3,\n30% white", ROOT / "Mooney" / eg),
             ("4 models", "depth · normals\nCLIP · Qwen3-VL", None),
             ("Compare", "Original vs Mooney\nvs GT / labels", None)]
    bw, bh, gap = Inches(2.55), Inches(3.3), Inches(0.6)
    x0 = (SW - (4 * bw + 3 * gap)) // 2
    y0 = Inches(3.45)
    for i, (head, sub, img) in enumerate(steps):
        x = x0 + i * (bw + gap)
        rect(s, x, y0, bw, bh, fill=PALE, line=LINE)
        text(s, x, y0 + Inches(0.12), bw, Inches(0.45), head, size=20, bold=True, align=PP_ALIGN.CENTER)
        if img:
            picture(s, img, x + (bw - Inches(1.75)) // 2, y0 + Inches(0.62), Inches(1.75), Inches(1.75))
            text(s, x, y0 + Inches(2.45), bw, Inches(0.8), sub, size=14, color=MUTED, align=PP_ALIGN.CENTER)
        else:
            text(s, x, y0 + Inches(0.6), bw, bh - Inches(0.75), sub, size=18, color=INK,
                 align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, spacing=1.2)
        if i < 3:
            arrow(s, x + bw + Inches(0.08), y0 + bh // 2, x + bw + gap - Inches(0.08), y0 + bh // 2)

    # 3./4. Subset grids
    for folder, head in (("Original", "Our 10 picks: originals"), ("Mooney", "The same 10 as Mooney images")):
        n += 1
        s = new_slide(n, head)
        cell, cap = Inches(2.2), Inches(0.35)
        gx = Inches(0.25)
        x0 = (SW - (5 * cell + 4 * gx)) // 2
        y0 = Inches(1.25)
        for i, f in enumerate(subset):
            src = ROOT / "Subset" / folder / f.name
            img = on_black(src, BUILD / f"black_{f.name}") if folder == "Original" else src
            r, c = divmod(i, 5)
            x = x0 + c * (cell + gx)
            y = y0 + r * (cell + cap + Inches(0.15))
            picture(s, img, x, y, cell, cell)
            text(s, x - Inches(0.1), y + cell, cell + Inches(0.2), cap, f.name, size=12, color=MUTED,
                 align=PP_ALIGN.CENTER)

    # 5. Vision systems table
    n += 1
    s = new_slide(n, "Vision systems used", "All pretrained, used as-is (no fine-tuning)")
    rows = [["Model", "Task", "Output", "Metric"],
            ["Depth Anything V2 Small", "Monocular depth", "Relative depth map", "Spearman ρ + AbsRel vs GT depth"],
            ["Marigold normals v1.1", "Surface normals", "Normal map", "Mean angular error vs GT normals"],
            ["CLIP ViT-L/14", "Zero-shot recognition", "Scores for our 20 labels", "Top-1 / top-3 accuracy (chance 5%)"],
            ["Qwen3-VL-2B", "Open recognition (VLM)", "Free-form answer", "Names the object correctly"]]
    table(s, MARGIN, Inches(1.75), SW - 2 * MARGIN, rows,
          [Inches(3.1), Inches(2.6), Inches(2.6), Inches(3.833)], size=18, row_h=Inches(0.75))

    # 6.-9. One slide per system
    rho, absrel = metric("Depth: Spearman"), metric("Depth: AbsRel")
    ang = metric("Normals")
    t1, t3 = metric("CLIP: top-1"), metric("CLIP: top-3")
    vlm = metric("VLM")
    pct = lambda v: f"{float(v) * 100:.0f}%"
    systems = [
        ("Result 1: Depth Anything V2 Small", "panel_Result1.png", "Spearman ρ vs GT depth",
         f"{float(rho['Original']):.2f}", f"{float(rho['Mooney']):.2f}",
         [f"AbsRel {float(absrel['Original']):.3f} → {float(absrel['Mooney']):.3f}",
          "On Mooneys the depth map mostly follows the white blobs, not the 3D shape"]),
        ("Result 2: Marigold normals v1.1", "panel_Result2.png", "Mean angular error vs GT",
         f"{float(ang['Original']):.1f}°", f"{float(ang['Mooney']):.1f}°",
         ["Lower is better", "Mooney normals are close to flat, facing the camera"]),
        ("Result 3: CLIP ViT-L/14 (zero-shot)", "panel_Result3.png", "Top-1 accuracy, 20 labels",
         pct(t1["Original"]), pct(t1["Mooney"]),
         [f"Top-3: {pct(t3['Original'])} → {pct(t3['Mooney'])}", "Chance level: 5%"]),
        ("Result 4: Qwen3-VL-2B (free-form)", "panel_Result4.png", "Names the object correctly",
         pct(vlm["Original"]), pct(vlm["Mooney"]),
         [f"Lenient (mug, couch, statue … count): {pct(QWEN_LENIENT['Original'])} → {pct(QWEN_LENIENT['Mooney'])}",
          "No label list given: the model must name the object itself"]),
    ]
    for head, panel, label, a, b, note in systems:
        n += 1
        s = new_slide(n, head)
        picture(s, ASSETS / panel, MARGIN, Inches(1.2), box=(Inches(8.6), Inches(5.65)))
        big_number(s, Inches(9.45), Inches(2.0), Inches(3.4), label, a, b, note)

    # 10. Summary
    n += 1
    s = new_slide(n, "Summary: every model drops on Mooney images")
    picture(s, ASSETS / "summary_chart.png", MARGIN, Inches(1.1), box=(SW - 2 * MARGIN, Inches(3.15)))
    f2 = lambda v: f"{float(v):.2f}"
    rows = [["System", "Metric", "Original", "Mooney"],
            ["Depth Anything V2", "Spearman ρ ↑", f2(rho["Original"]), f2(rho["Mooney"])],
            ["Depth Anything V2", "AbsRel ↓", f"{float(absrel['Original']):.3f}", f"{float(absrel['Mooney']):.3f}"],
            ["Marigold normals", "Angular error ↓", f"{float(ang['Original']):.1f}°", f"{float(ang['Mooney']):.1f}°"],
            ["CLIP ViT-L/14", "Top-1 / top-3 ↑", f"{f2(t1['Original'])} / {f2(t3['Original'])}",
             f"{f2(t1['Mooney'])} / {f2(t3['Mooney'])}"],
            ["Qwen3-VL-2B", "Names object ↑ (lenient)", f"{f2(vlm['Original'])} ({QWEN_LENIENT['Original']:.2f})",
             f"{f2(vlm['Mooney'])} ({QWEN_LENIENT['Mooney']:.2f})"]]
    table(s, Inches(1.9), Inches(4.35), Inches(9.53), rows,
          [Inches(2.8), Inches(2.9), Inches(1.915), Inches(1.915)], size=15, row_h=Inches(0.42))

    # 11. Light direction
    n += 1
    s = new_slide(n, "Does the light direction matter?")
    chart = light_chart(BUILD / "light_chart.png")
    picture(s, chart, MARGIN, Inches(1.15), box=(SW - 2 * MARGIN, Inches(4.75)))
    clip_m = light_row("CLIP: top-1", "Mooney")
    text(s, MARGIN, Inches(6.0), SW - 2 * MARGIN, Inches(0.9),
         [[("Recognition: ", {"bold": True}),
           (f"CLIP on Mooneys is {clip_m[0]:.2f} with side light (L0/L1) vs {clip_m[3]:.2f} with higher light (L3 upper right, L4 from above).  ", {}),
           ("3D: ", {"bold": True}), ("normal error stays flat at ~40° for every direction.", {})]],
         size=17, spacing=1.05)

    # 12. Observations
    n += 1
    s = new_slide(n, "Observations")
    obs = [
        [("No generalization without fine-tuning: ", {"bold": True}), ("every model drops a lot on Mooneys", {})],
        [("3D shape collapses: ", {"bold": True}),
         (f"depth ρ {float(rho['Original']):.2f} → {float(rho['Mooney']):.2f}, although humans do see shape in Mooneys (as the paper argues)", {})],
        [("Knowing the labels helps: ", {"bold": True}),
         (f"CLIP {pct(t1['Mooney'])} vs Qwen {pct(vlm['Mooney'])} on Mooneys", {})],
        [("Side light is hardest ", {"bold": True}), ("for recognition", {})],
        [("Qwen hallucinates: ", {"bold": True}),
         ("shoe → “motorcycle with rider”, piggy bank → “skull”, pumpkin → “world map”", {})],
    ]
    text(s, MARGIN, Inches(1.3), Inches(7.6), Inches(5.4), [[("•  ", {"color": ORANGE})] + o for o in obs],
         size=20, spacing=1.05, after=16)
    lx = Inches(8.55)
    rect(s, lx, Inches(1.3), SW - lx - MARGIN, Inches(4.2), fill=PALE, line=LINE)
    lim = ["Qwen is scored by strict string matching (“mug” ≠ cup)",
           "AbsRel is not very sensitive here",
           "Some objects (airplane, pear) are very hard even for humans",
           "Busts came from Objaverse statue/sculpture models (no “bust” class)"]
    text(s, lx + Inches(0.25), Inches(1.45), SW - lx - MARGIN - Inches(0.5), Inches(0.5),
         "Limitations", size=20, bold=True)
    text(s, lx + Inches(0.25), Inches(2.0), SW - lx - MARGIN - Inches(0.5), Inches(3.4),
         [[("–  ", {"color": MUTED}), (l, {})] for l in lim], size=16, spacing=1.05, after=12)

    # 13./14. GUI and code
    n += 1
    s = new_slide(n, "Our Mooney tool", "Gradio GUI: sliders for blur and white %, live preview, batch mode")
    picture(s, ASSETS / "gui.png", MARGIN, Inches(1.5), box=(SW - 2 * MARGIN, Inches(5.4)))
    n += 1
    s = new_slide(n, "Mooney code", "mooney_generator/mooney_tool.py: threshold by binary search on the white %")
    picture(s, ASSETS / "code.png", MARGIN, Inches(1.5), box=(SW - 2 * MARGIN, Inches(5.4)))

    # 15. AI usage declaration (placeholder)
    n += 1
    s = new_slide(n, "AI usage declaration")
    box = s.shapes.add_textbox(MARGIN, Inches(1.4), SW - 2 * MARGIN, Inches(5.2))
    box.line.color.rgb = ORANGE
    box.line.width = Pt(2)
    box.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = Inches(0.25)
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = "[PLACEHOLDER: write the AI usage declaration here]"
    r.font.name, r.font.size, r.font.bold, r.font.color.rgb = FONT, Pt(22), True, ORANGE

    prs.save(OUT)
    print(f"Wrote {OUT} ({n} slides)")


if __name__ == "__main__":
    main()
