---
name: latex-paper-assistant
description: Comprehensive assistant for authoring, structuring, formatting, and compiling academic research papers and journal submissions in LaTeX. Use when the user asks to write or format a paper, thesis, or manuscript in LaTeX, structure equations and tables (booktabs), debug LaTeX compilation errors, format citations (BibTeX/natbib), or package a project for arXiv submission.
---

# LaTeX Academic Paper Assistant

This skill guides the creation, mathematical formatting, table structuring, bibliography linking, and debugging of scientific manuscripts in LaTeX for venues like Nature/Springer, IEEE, Elsevier, ACM, and arXiv.

## Workflow Overview

1. **Document Setup & Class Selection**
   - General preprint / arXiv: `article` (with geometry `[margin=0.75in]`) or `article` twocolumn.
   - IEEE submissions: `\documentclass[journal]{IEEEtran}`.
   - Elsevier: `\documentclass[preprint,12pt]{elsarticle}`.
   - ACM: `\documentclass[sigconf]{acmart}`.
2. **Professional Mathematical Formatting**
   - Always load `amsmath`, `amssymb`, `amsfonts`, and `bm` (for bold math vectors $\bm{x}$).
   - Multi-line equations: Use `align` or `aligned` instead of legacy `eqnarray`.
   - Custom operators: Define with `\DeclareMathOperator{\Tr}{Tr}`.
   - Matrices: Use `pmatrix` (parentheses) or `bmatrix` (brackets).
3. **Publication-Quality Tables (Booktabs Rule)**
   - **Never use vertical lines** (`|`).
   - Use `\toprule`, `\midrule`, and `\bottomrule` from `booktabs`.
   - Align numbers by decimal point using `siunitx` (`S` column specifier).
   - Use `tabularx` for auto-wrapped paragraph columns.
4. **Citations and References**
   - Use `\usepackage[numbers,sort&compress]{natbib}` with `\bibliographystyle{unsrtnat}` (or journal-specific bst).
   - Ensure special characters like `&` in journal names or publishers are escaped as `\&`.
5. **Cross-Referencing**
   - Use `\usepackage[capitalize,noabbrev]{cleveref}` and cite with `\cref{fig:my_figure}`, `\cref{tab:my_table}`, `\cref{eq:my_equation}` for automatic labeling ("Figure 1", "Table 2", "Equation 3").

---

## LaTeX Tools Helper Script

A utility script is available at:
[latex_tools.py](./scripts/latex_tools.py)

### 1. Check Available Compilers
```bash
python .agents/skills/latex-paper-assistant/scripts/latex_tools.py check
```

### 2. Validate a BibTeX File
```bash
python .agents/skills/latex-paper-assistant/scripts/latex_tools.py validate-bib path/to/references.bib
```
Checks for unescaped characters (`&`), missing brackets, and duplicate citation keys.

### 3. Compile a LaTeX File
```bash
python .agents/skills/latex-paper-assistant/scripts/latex_tools.py compile main.tex
```
Automatically attempts compilation with available engines and parses `.log` files to extract specific errors with exact line numbers.

### 4. Package Project for arXiv
```bash
python .agents/skills/latex-paper-assistant/scripts/latex_tools.py arxiv main.tex --output submission.zip
```
Collects `main.tex`, figures (`\includegraphics`), and the generated `.bbl` into a clean zip ready for upload.

---

## Common LaTeX Errors & How to Fix Them

| Error in Log | Cause | Solution |
| :--- | :--- | :--- |
| `! LaTeX Error: Something's wrong--perhaps a missing \item.` | List or table environment error. | Ensure every `itemize` or `enumerate` block has `\item`. In `thebibliography`, ensure `\bibitem{key}` exists. |
| `! Undefined control sequence.` | Typo in macro or missing `\usepackage`. | Check the spelling of the command or add the missing package in the preamble. |
| `! Overfull \hbox (X pt too wide)` | Line or equation is wider than column width. | Break long equations with `split` or `aligned`. Use `\allowbreak` in long URLs/strings. |
| `! Missing $ inserted` | Math symbol placed in text mode (e.g. `_` or `^`). | Escape as `\_` in text or wrap inside `$ ... $`. |
| `! File ended while scanning use of...` | Missing closing brace `}`. | Count matching opening and closing braces in the flagged line. |
| `! I can't find file 'figure.png'` | Path mismatch or missing extension. | Check relative path from where the compilation is executed. |

---

## Starter Templates

A starter two-column preprint template is provided at:
- Manuscript: [article_template.tex](./templates/article_template.tex)
- BibTeX: [references.bib](./templates/references.bib)
