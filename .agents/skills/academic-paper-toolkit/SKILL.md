---
name: academic-paper-toolkit
description: Academic research assistant for searching, retrieving metadata, tracking citations, downloading scientific papers, and syncing with Zotero using Crossref REST API, Sci-Hub, PyPaperBot, Google Scholar (scholarly), and Pyzotero. Use whenever the user asks to search for papers, fetch citations, get metadata by DOI, download article PDFs, or manage Zotero references.
---

# Academic Paper Toolkit

Comprehensive workflow for discovering scientific literature, retrieving Crossref metadata and citation networks, downloading article PDFs, and managing references with Zotero.

## Supported Tools & APIs

1. **Crossref REST API (`habanero` / REST API)**
   - Official metadata and citation indexing for DOIs.
   - Endpoints: `https://api.crossref.org/works/{doi}`
   - Features: Retrieve citation counts (`is-referenced-by-count`), bibliographic references, abstracts, authors, journals, and funding information.
2. **Sci-Hub PDF Downloader**
   - Direct download using operational mirrors (`https://sci-hub.ru`, `https://sci-hub.st`, `https://sci-hub.se`).
3. **PyPaperBot**
   - Automated batch downloader from Google Scholar, Crossref, and Sci-Hub.
   - Saves organized PDFs, CSV summaries, and BibTeX files.
4. **Scholarly**
   - Google Scholar scraping for researcher profiles, citation counts, h-index, and publication lists.
5. **Pyzotero (`pyzotero`)**
   - Full read/write Zotero Web API integration.
   - Query user/group libraries, create items from Crossref metadata, manage collections, tags, and attach PDFs.

---

## Quick Usage via Helper Script

The unified helper script is located at:
[paper_tools.py](./scripts/paper_tools.py)

### 1. Get Article Metadata by DOI
```bash
python .agents/skills/academic-paper-toolkit/scripts/paper_tools.py meta <DOI>
```
*Example:* `python .agents/skills/academic-paper-toolkit/scripts/paper_tools.py meta 10.1038/nature12373`

### 2. Get Citations & Bibliographic References
```bash
python .agents/skills/academic-paper-toolkit/scripts/paper_tools.py citations <DOI>
```
Returns citation count and full array of referenced papers (with DOIs).

### 3. Search Papers on Crossref
```bash
python .agents/skills/academic-paper-toolkit/scripts/paper_tools.py search "quantum computing" --rows 5
```

### 4. Download Paper PDF via Sci-Hub
```bash
python .agents/skills/academic-paper-toolkit/scripts/paper_tools.py download <DOI> --dir papers/
```

### 5. Search Author Profile on Google Scholar
```bash
python .agents/skills/academic-paper-toolkit/scripts/paper_tools.py author "Geoffrey Hinton"
```

### 6. Zotero Integration
```bash
# List recent items
python .agents/skills/academic-paper-toolkit/scripts/paper_tools.py zotero-list --library-id <ID> --api-key <KEY>

# Add a paper to Zotero by DOI (fetches Crossref metadata automatically)
python .agents/skills/academic-paper-toolkit/scripts/paper_tools.py zotero-add <DOI> --library-id <ID> --api-key <KEY>
```
*(You can also set `ZOTERO_LIBRARY_ID` and `ZOTERO_API_KEY` as environment variables).*

---

## Pyzotero Python SDK Examples

```python
from pyzotero import zotero

# Initialize (library_type is 'user' or 'group')
zot = zotero.Zotero(library_id='1234567', library_type='user', api_key='your_api_key')

# Fetch recent items
items = zot.top(limit=5)
for item in items:
    print(item['data']['key'], item['data'].get('title'))

# Create an item using template
template = zot.item_template('journalArticle')
template['title'] = 'My Research Paper'
template['DOI'] = '10.1038/example'
zot.create_items([template])
```

---

## PyPaperBot Direct Usage

PyPaperBot can be run directly from terminal:

### Download by Single DOI
```bash
python -m PyPaperBot --doi 10.1038/nature12373 --dwn-dir ./papers --scihub-mirror https://sci-hub.ru
```

### Download from DOI List File
```bash
python -m PyPaperBot --doi-file dois.txt --dwn-dir ./papers --scihub-mirror https://sci-hub.ru
```

### Search Google Scholar and Download Top Papers
```bash
python -m PyPaperBot --query "crispr cas9 off target effects" --scholar-pages 1 --scholar-results 5 --dwn-dir ./papers --scihub-mirror https://sci-hub.ru
```
