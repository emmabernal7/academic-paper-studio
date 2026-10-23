---
name: scientific-plotting
description: Create publication-ready scientific figures, charts, and diagrams conforming to standards of top academic journals (Nature, Science, Cell, IEEE, PNAS). Use when the user asks to generate scientific plots, multi-panel figures, format charts for journal submission, apply colorblind-safe palettes, or export 300+ DPI / vector figures (PDF/SVG).
---

# Scientific Plotting for Academic Publications

This skill provides comprehensive guidelines, palettes, sizing standards, and python helpers to produce publication-grade figures suitable for major peer-reviewed journals.

## Journal Figure Dimensions Quick Reference

| Journal | Single Column | 1.5 Column | Double Column | Max Height | Font Family | Font Size |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Nature** | 89 mm (3.5 in) | 120–136 mm | 183 mm (7.2 in) | 247 mm | Arial / Helvetica | 5–7 pt (ticks/axis), 8 pt (labels) |
| **Science** | 55 mm (2.2 in) | 120 mm | 178 mm (7.0 in) | 250 mm | Helvetica / Arial | 6–8 pt (main), 9 pt (panel tags) |
| **IEEE** | 88.9 mm (3.5 in) | — | 181.8 mm (7.16 in)| 228.6 mm | Times / Helvetica | 8–10 pt |
| **Cell** | 85 mm (3.35 in) | 114 mm | 174 mm (6.85 in) | 235 mm | Arial / Helvetica | 6–8 pt |
| **PNAS** | 87 mm (3.42 in) | — | 178 mm (7.0 in) | 225 mm | Arial / Helvetica | 6–8 pt |

---

## Key Design Principles

1. **Vector First**:
   - Always export line plots, scatter plots, bar charts, and diagrams as vector files (`.pdf` or `.svg`).
   - Use raster formats (`.png`, `.tiff`) at **300 to 600 DPI** only when necessary (e.g. dense heatmaps or microscopy imagery).
   - Set `pdf.fonttype: 42` so fonts remain editable TrueType in Adobe Illustrator or Inkscape.
2. **Typography**:
   - Never use default large fonts scaled down. Sizing must be exact so text doesn't become illegible when scaled into column width.
   - Capitalization of panel letters: Bold lowercase `a`, `b`, `c` for Nature; bold uppercase `A`, `B`, `C` for Science / Cell / IEEE.
3. **Colorblind-Safe Palettes**:
   - **Okabe-Ito (Wong)**: `#0072B2` (Blue), `#D55E00` (Vermilion), `#009E73` (Green), `#E69F00` (Orange), `#56B4E9` (Sky Blue), `#CC79A7` (Purple).
   - Continuous color scales: Use perceptually uniform colormaps (`viridis`, `plasma`, `cividis`, `magma`). Never use `jet` or rainbow.
4. **Data-Ink Ratio**:
   - Remove unnecessary top and right spines (`axes.spines.top = False`, `axes.spines.right = False`).
   - Avoid heavy gridlines; use light gray (`#e0e0e0`) with `linewidth=0.5` only if aiding readability.
   - Legend with transparent or absent bounding box (`frameon=False`).

---

## Python Helper Script

A ready-to-use module is located at:
[plot_styler.py](./scripts/plot_styler.py)

### Example 1: Creating a Nature-Compliant Two-Panel Figure
```python
import matplotlib.pyplot as plt
import numpy as np
from plot_styler import set_publication_style, create_figure, add_panel_label, save_figure, OKABE_ITO

# 1. Apply style presets
set_publication_style(journal="nature", base_fontsize=7)

# 2. Create figure with journal column width
fig, (ax1, ax2) = create_figure(nrows=1, ncols=2, journal="nature", column="double", aspect=2.4)

# 3. Plot Panel A
x = np.linspace(0, 10, 100)
ax1.plot(x, np.sin(x), color=OKABE_ITO[0], label="Model Fit")
ax1.set_xlabel("Time (s)")
ax1.set_ylabel("Normalized Response (a.u.)")
ax1.legend()
add_panel_label(ax1, "a")

# 4. Plot Panel B
ax2.bar(["WT", "Mut-1", "Mut-2"], [1.0, 0.45, 1.8], color=OKABE_ITO[1], width=0.5)
ax2.set_ylabel("Relative Expression")
add_panel_label(ax2, "b")

# 5. Export vector PDF + 300 DPI PNG
save_figure(fig, "figures/figure_1", dpi=300, formats=["pdf", "png"])
```

### Example 2: Heatmap with Perceptually Uniform Palette
```python
import seaborn as sns
import matplotlib.pyplot as plt
from plot_styler import set_publication_style, create_figure, save_figure

set_publication_style("nature")
fig, ax = create_figure(journal="nature", column="single", aspect=1.1)

data = np.random.randn(8, 8)
sns.heatmap(data, cmap="viridis", cbar_kws={"label": "log2 Fold Change"}, ax=ax)
ax.set_title("Expression Heatmap")

save_figure(fig, "figures/heatmap", formats=["pdf", "png"])
```
