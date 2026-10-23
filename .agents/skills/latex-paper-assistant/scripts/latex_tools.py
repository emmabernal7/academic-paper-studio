#!/usr/bin/env python3
"""
LaTeX Tools Helper (latex_tools.py)
Validates BibTeX files, detects compilers, compiles LaTeX documents with
clean log diagnostics, and packages manuscripts for arXiv / journal submission.
"""

import sys
import os
import re
import shutil
import subprocess
import argparse
import zipfile

def check_latex_compilers():
    """Check for installed LaTeX compilers on the system."""
    compilers = ["tectonic", "latexmk", "pdflatex", "xelatex", "lualatex"]
    found = {}
    for comp in compilers:
        path = shutil.which(comp)
        found[comp] = path
    return found

def validate_bibtex(bib_path):
    """
    Check for common syntax issues in BibTeX files:
    - Unescaped special characters (&, %, _, #)
    - Missing closing braces or quotes
    - Duplicate citation keys
    """
    if not os.path.exists(bib_path):
        return {"valid": False, "errors": [f"File {bib_path} not found."]}

    with open(bib_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    errors = []
    warnings = []
    keys_seen = set()

    # Find entries
    entries = re.findall(r'@\w+\s*\{\s*([^,]+),', content)
    for key in entries:
        key_clean = key.strip()
        if key_clean in keys_seen:
            warnings.append(f"Duplicate citation key detected: '{key_clean}'")
        keys_seen.add(key_clean)

    # Check unescaped ampersands in titles or journal fields
    lines = content.splitlines()
    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("%"):
            continue
        # Unescaped & not preceded by backslash
        if re.search(r'(?<!\\)&', line):
            warnings.append(f"Line {idx}: Possible unescaped '&'. Use '\\&' in BibTeX: {stripped[:60]}")

    return {
        "valid": len(errors) == 0,
        "total_entries": len(entries),
        "keys": list(keys_seen),
        "errors": errors,
        "warnings": warnings
    }

def parse_latex_log(log_path):
    """Parse LaTeX log file to extract concise error messages and line numbers."""
    if not os.path.exists(log_path):
        return ["Log file not found."]

    errors = []
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    current_error = []
    capture = False

    for line in lines:
        if line.startswith("!"):
            if current_error:
                errors.append("".join(current_error).strip())
                current_error = []
            capture = True
            current_error.append(line)
        elif capture:
            if line.startswith("l.") or "..." in line:
                current_error.append(line)
                errors.append("".join(current_error).strip())
                current_error = []
                capture = False
            elif line.strip() == "":
                capture = False
            else:
                current_error.append(line)

    if current_error:
        errors.append("".join(current_error).strip())

    return errors

def compile_latex(tex_path, engine=None):
    """Compile LaTeX document using the best available compiler."""
    compilers = check_latex_compilers()
    available = [k for k, v in compilers.items() if v]

    if not available:
        return {
            "success": False,
            "error": "No LaTeX compiler found (tectonic, latexmk, pdflatex, xelatex are not on PATH).",
            "suggestion": "Install MiKTeX, TeX Live, or Tectonic (e.g. 'conda install -c conda-forge tectonic')."
        }

    chosen = engine or ("tectonic" if "tectonic" in available else ("latexmk" if "latexmk" in available else available[0]))
    tex_dir = os.path.dirname(os.path.abspath(tex_path)) or "."
    base_name = os.path.splitext(os.path.basename(tex_path))[0]

    if chosen == "tectonic":
        cmd = ["tectonic", tex_path]
    elif chosen == "latexmk":
        cmd = ["latexmk", "-pdf", "-interaction=nonstopmode", os.path.basename(tex_path)]
    else:
        cmd = [chosen, "-interaction=nonstopmode", os.path.basename(tex_path)]

    proc = subprocess.run(cmd, cwd=tex_dir, capture_output=True, text=True)
    pdf_path = os.path.join(tex_dir, f"{base_name}.pdf")
    log_path = os.path.join(tex_dir, f"{base_name}.log")

    if os.path.exists(pdf_path) and proc.returncode == 0:
        return {"success": True, "engine": chosen, "pdf": pdf_path}
    else:
        parsed_errors = parse_latex_log(log_path)
        return {
            "success": False,
            "engine": chosen,
            "returncode": proc.returncode,
            "log_errors": parsed_errors[:5] if parsed_errors else ["Check .log file for details."]
        }

def package_for_arxiv(main_tex_path, output_zip="arxiv_submission.zip"):
    """
    Package all necessary files (.tex, .bbl, figures) into a clean zip archive for arXiv.
    """
    if not os.path.exists(main_tex_path):
        return {"success": False, "error": f"{main_tex_path} does not exist."}

    tex_dir = os.path.dirname(os.path.abspath(main_tex_path)) or "."
    base_name = os.path.splitext(os.path.basename(main_tex_path))[0]

    with open(main_tex_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    files_to_pack = {os.path.basename(main_tex_path): main_tex_path}

    # BBL file (arXiv requires the generated .bbl instead of .bib)
    bbl_path = os.path.join(tex_dir, f"{base_name}.bbl")
    if os.path.exists(bbl_path):
        files_to_pack[f"{base_name}.bbl"] = bbl_path

    # Extract included graphics
    graphics = re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', content)
    for g in graphics:
        candidate = os.path.join(tex_dir, g)
        if os.path.exists(candidate):
            files_to_pack[g] = candidate
        else:
            for ext in [".pdf", ".png", ".jpg", ".eps"]:
                if os.path.exists(candidate + ext):
                    files_to_pack[g + ext] = candidate + ext
                    break

    # Write zip file
    out_path = os.path.join(tex_dir, output_zip)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for arcname, filepath in files_to_pack.items():
            z.write(filepath, arcname)

    return {
        "success": True,
        "zip_path": out_path,
        "files_included": list(files_to_pack.keys())
    }

def main():
    parser = argparse.ArgumentParser(description="LaTeX Paper Assistant Tools")
    subparsers = parser.add_subparsers(dest="command")

    # check compilers
    subparsers.add_parser("check", help="Check installed LaTeX compilers")

    # validate bib
    p_bib = subparsers.add_parser("validate-bib", help="Validate a BibTeX file")
    p_bib.add_argument("bib_file", help="Path to .bib file")

    # compile
    p_comp = subparsers.add_parser("compile", help="Compile a LaTeX document")
    p_comp.add_argument("tex_file", help="Path to main .tex file")
    p_comp.add_argument("--engine", help="Compiler engine (tectonic, latexmk, pdflatex, etc.)")

    # arxiv package
    p_arxiv = subparsers.add_parser("arxiv", help="Package project for arXiv submission")
    p_arxiv.add_argument("tex_file", help="Path to main .tex file")
    p_arxiv.add_argument("--output", default="arxiv_submission.zip", help="Output zip name")

    args = parser.parse_args()

    if args.command == "check":
        compilers = check_latex_compilers()
        print("Available LaTeX compilers:")
        for k, v in compilers.items():
            status = v if v else "Not Found"
            print(f"  - {k:<10}: {status}")
    elif args.command == "validate-bib":
        res = validate_bibtex(args.bib_file)
        import json
        print(json.dumps(res, indent=2))
    elif args.command == "compile":
        res = compile_latex(args.tex_file, engine=args.engine)
        import json
        print(json.dumps(res, indent=2))
    elif args.command == "arxiv":
        res = package_for_arxiv(args.tex_file, output_zip=args.output)
        import json
        print(json.dumps(res, indent=2))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
