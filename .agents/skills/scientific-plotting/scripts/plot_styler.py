#!/usr/bin/env python3
"""
Scientific Plotting Helper (plot_styler.py)
Provides publication-quality matplotlib / seaborn styling adhering to
Nature, Science, IEEE, and Cell journal guidelines.
"""

import os
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

# Colorblind-safe palette (Wong / Okabe-Ito)
OKABE_ITO = [
    "#0072B2",  # Blue
    "#D55E00",  # Vermilion
    "#009E73",  # Bluish Green
    "#E69F00",  # Orange
    "#56B4E9",  # Sky Blue
    "#CC79A7",  # Reddish Purple
    "#F0E442",  # Yellow
    "#000000",  # Black
]

# Standard column widths in inches
JOURNAL_WIDTHS = {
    "nature": {"single": 3.5, "1.5col": 5.0, "double": 7.2},      # 89mm, 127mm, 183mm
    "science": {"single": 2.25, "double": 4.75, "triple": 7.0},    # 57mm, 121mm, 178mm
    "ieee": {"single": 3.5, "double": 7.16},                       # 88.9mm, 181.8mm
    "cell": {"single": 3.35, "1.5col": 4.5, "double": 6.85},      # 85mm, 114mm, 174mm
    "pnas": {"single": 3.42, "double": 7.0}                        # 87mm, 178mm
}

def set_publication_style(journal="nature", font_family="sans-serif", base_fontsize=7):
    """
    Apply publication-grade rcParams for matplotlib.
    """
    mpl.rcParams.update({
        # Font settings
        "font.family": font_family,
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": base_fontsize,
        "axes.labelsize": base_fontsize + 1,
        "axes.titlesize": base_fontsize + 1,
        "xtick.labelsize": base_fontsize,
        "ytick.labelsize": base_fontsize,
        "legend.fontsize": base_fontsize - 0.5,
        "figure.titlesize": base_fontsize + 2,
        
        # Line widths and spines
        "axes.linewidth": 0.8,
        "grid.linewidth": 0.5,
        "lines.linewidth": 1.2,
        "lines.markersize": 4,
        "patch.linewidth": 0.8,
        
        # Ticks
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.size": 3.5,
        "ytick.major.size": 3.5,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "xtick.minor.size": 2.0,
        "ytick.minor.size": 2.0,
        "xtick.minor.width": 0.5,
        "ytick.minor.width": 0.5,
        
        # Spines (clean scientific look: keep bottom and left, hide top and right)
        "axes.spines.top": False,
        "axes.spines.right": False,
        
        # Colors
        "axes.prop_cycle": mpl.cycler(color=OKABE_ITO),
        
        # Legend
        "legend.frameon": False,
        "legend.borderpad": 0.2,
        
        # PDF/PS rendering
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        
        # Saving
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.05
    })

def create_figure(nrows=1, ncols=1, journal="nature", column="single", aspect=1.2, **kwargs):
    """
    Create a figure and axes with dimensions scaled exactly to journal specifications.
    """
    widths = JOURNAL_WIDTHS.get(journal.lower(), JOURNAL_WIDTHS["nature"])
    width_in = widths.get(column, widths["single"])
    height_in = width_in / aspect
    
    fig, axes = plt.subplots(nrows, ncols, figsize=(width_in, height_in), **kwargs)
    return fig, axes

def add_panel_label(ax, label="A", loc=(-0.15, 1.05), fontsize=9, fontweight="bold"):
    """
    Add standard journal panel labels (A, B, C...) in bold upper-left.
    """
    ax.text(
        loc[0], loc[1], label,
        transform=ax.transAxes,
        fontsize=fontsize,
        fontweight=fontweight,
        va="top", ha="right"
    )

def save_figure(fig, filepath, dpi=300, formats=("pdf", "png")):
    """
    Export figure in vector format (PDF/SVG) and high-resolution raster (PNG/TIFF).
    """
    base, _ = os.path.splitext(filepath)
    saved_files = []
    
    for fmt in formats:
        target_path = f"{base}.{fmt.lstrip('.')}"
        fig.savefig(target_path, dpi=dpi, bbox_inches="tight", transparent=False)
        saved_files.append(target_path)
        
    return saved_files

def demo_plot(output_dir="plots"):
    """Generate a demonstration figure showing journal style."""
    os.makedirs(output_dir, exist_ok=True)
    set_publication_style("nature")
    
    fig, (ax1, ax2) = create_figure(nrows=1, ncols=2, journal="nature", column="double", aspect=2.3)
    
    # Panel A: Time series with confidence bands
    x = np.linspace(0, 10, 100)
    y1 = np.sin(x)
    y2 = np.cos(x)
    err1 = 0.2 * np.random.normal(size=len(x)) * 0.5 + 0.15
    
    ax1.plot(x, y1, label=r"$Y_1 = \sin(x)$", color=OKABE_ITO[0])
    ax1.fill_between(x, y1 - err1, y1 + err1, alpha=0.25, color=OKABE_ITO[0])
    ax1.plot(x, y2, label=r"$Y_2 = \cos(x)$", color=OKABE_ITO[1])
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Amplitude (a.u.)")
    ax1.legend(loc="upper right")
    add_panel_label(ax1, "a")
    
    # Panel B: Scatter with regression
    np.random.seed(42)
    x_scat = np.random.uniform(10, 50, 40)
    y_scat = 1.8 * x_scat + np.random.normal(0, 10, 40)
    ax2.scatter(x_scat, y_scat, color=OKABE_ITO[2], alpha=0.8, edgecolors="none", s=25)
    m, b = np.polyfit(x_scat, y_scat, 1)
    ax2.plot(x_scat, m * x_scat + b, color=OKABE_ITO[7], linestyle="--", linewidth=1)
    ax2.set_xlabel("Feature $X$ (units)")
    ax2.set_ylabel("Response $Y$ (units)")
    add_panel_label(ax2, "b")
    
    plt.tight_layout()
    saved = save_figure(fig, os.path.join(output_dir, "nature_demo_figure"), dpi=300)
    print("Demo figure saved:", saved)

if __name__ == "__main__":
    demo_plot()
