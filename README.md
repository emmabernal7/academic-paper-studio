# 📚 Academic Paper Studio & Toolkit

> A modern, unified academic research suite: batch DOI downloader with a multi-engine Open Access cascade, citation manager (BibTeX, RIS, EndNote), Zotero synchronization, and Agent Skills for AI coding assistants.

---

## 🌟 Features

- **🌐 Smart Open Access Cascade**:
  1. **Crossref REST API**: Official publisher metadata and direct open links.
  2. **Unpaywall API**: Global repository of legal open access PDFs.
  3. **Publisher Landing Page Scraper**: Highwire Press and Dublin Core meta-tags (`<meta name="citation_pdf_url">`).
  4. **Europe PMC / PubMed Central**: Direct open access biomedical paper fetching.
  5. **Preprint Resolvers**: Automatic resolution for arXiv, bioRxiv, and medRxiv.
  6. **Sci-Hub Multi-Mirror Network**: Resilient fallback for paywalled pre-2021 literature.
  7. **Anna's Archive Engine (SciDB / Z-Library / LibGen / IPFS)**: Native fallback for post-2021 paywalled articles, book chapters, and scientific books.

- **📚 Dual-Mode Research Suite (Papers & Books)**:
  - **📄 Papers Mode (DOI Batch Downloader)**: Process dozens of DOIs simultaneously with real-time progress, PDF bundling, and citation generation.
  - **📚 Book Downloader Mode (Anna's Archive / Z-Library / LibGen Unified Catalog)**:
    - Search books by **Title, Author, Publisher, or ISBN**.
    - Instant reactive filters by **Language** (Spanish, English, Portuguese, French, German, Italian), **Publication Year Range (`From–To`)**, and **File Format (`PDF`, `EPUB`, `DJVU`)**.
    - Interactive **column sorting** (`Title & Publisher`, `Author`, `Year`, `Language`, `Format / Size`).
    - Dynamic pagination with customizable items per page (**`10`, `25`, `50`, `100`, or `All`**), automatic `@book` citation generation (`.bib`, `.ris`, `.enw`), and 1-click direct book downloads.

- **📑 Multi-Format Citation Generator**:
  - Automatically generates `.bib` (BibTeX), `.ris` (EndNote / Mendeley / Zotero), and `.enw` (EndNote Web) files for both journal articles (`@article`) and books (`@book`).
  - Generates a summary `summary.csv` and bundles everything into an `AcademicPapers_Bundle.zip` with 1 click.

- **🔄 Zotero Cloud Sync**:
  - Direct integration via `pyzotero` to create collections, upload metadata, and attach downloaded PDFs directly to your personal or group library.

- **💻 Modern Web Interface (`web_downloader/`)**:
  - Dark / Light mode switch.
  - Bilingual interface (Español / English).
  - Real-time download progress bar and live terminal-like activity log.
  - Direct individual PDF download buttons and interactive preview modal.

- **🤖 Built-in Agent Skills (`.agents/skills/`)**:
  - `academic-paper-toolkit`: CLI and programmatic API for AI agents.
  - `scientific-plotting`: Publication-quality figures (Nature, Science, Cell standards).
  - `latex-paper-assistant`: LaTeX paper structure, BibTeX management, and compilation.

---

## 🚀 Quick Start (Local Web App)

### 1. Requirements
Ensure you have Python 3.9+ installed. Install dependencies:

```bash
pip install -r requirements.txt
```

### 2. Launch the Application
- **On Windows**: Double-click [`iniciar_descargador.bat`](iniciar_descargador.bat).
- **Via Terminal**:
  ```bash
  python web_downloader/app.py
  ```

Open your browser at **[http://localhost:8765](http://localhost:8765)**.

---

## 📁 Repository Structure

```text
├── .agents/
│   └── skills/
│       ├── academic-paper-toolkit/   # Core academic agent skill & tools
│       ├── scientific-plotting/      # Publication-quality plotting skill
│       └── latex-paper-assistant/    # Academic paper LaTeX assistant
├── web_downloader/
│   ├── app.py                        # Local lightweight Python HTTP server
│   ├── downloader_core.py            # 7-tier OA/Sci-Hub/Anna's Archive cascade & citation logic
│   ├── static/
│   │   └── index.html                # Responsive web frontend (ES / EN)
│   └── downloads/                    # Target directory for PDFs & citations
├── requirements.txt                  # Python dependencies
├── render.yaml                       # Cloud deployment blueprint
├── iniciar_descargador.bat           # 1-click Windows launcher
└── README.md
```

---

## 🔑 Environment Variables (Optional)

You can set these in your environment or via a `.env` file:

```bash
UNPAYWALL_EMAIL=your_email@domain.com    # Recommended for Unpaywall higher rate limits
ANNAS_ARCHIVE_KEY=your_secret_key        # Optional: for Anna's Archive Fast Download API
ZOTERO_API_KEY=your_zotero_api_key       # If using Zotero sync
ZOTERO_USER_ID=your_zotero_user_id       # Your Zotero numerical ID
```

---

## 📄 License
MIT License.
