#!/usr/bin/env python3
"""
Downloader Core Module for Academic Paper Studio.
Handles metadata resolution (Crossref), cascaded PDF downloading (OA, Sci-Hub, PyPaperBot),
BibTeX generation, and Zotero synchronization.
"""

import os
import re
import csv
import json
import time
import requests
import zipfile
from bs4 import BeautifulSoup

SCI_HUB_DEFAULT_MIRRORS = [
    "https://sci-hub.ru",
    "https://sci-hub.st",
    "https://sci-hub.se"
]

def sanitize_filename(text, max_len=60):
    """Sanitize strings for Windows/Linux safe filenames without illegal chars or unicode crashes."""
    if not text:
        return "untitled"
    # Replace unicode dashes and quotation marks with standard ASCII equivalents
    text = text.replace('\u2013', '-').replace('\u2014', '-').replace('–', '-').replace('—', '-')
    text = text.replace('“', '').replace('”', '').replace('"', '').replace("'", '').replace("’", '')
    # Strip illegal filesystem characters, commas, and semicolons
    clean = re.sub(r'[\\/*?:"<>|;,]', '', text)
    clean = re.sub(r'[\s_]+', '_', clean).strip('._ ')
    clean = clean[:max_len].strip('._ ')
    return clean or "untitled"

def extract_doi(text):
    """Clean and extract standard DOI format from text or URLs."""
    if not text:
        return ""
    text = text.strip()
    match = re.search(r'10\.\d{4,9}/[-._;()/:A-Za-z0-9]+', text)
    if match:
        doi = match.group(0).rstrip('.,;')
        return doi
    return text

def fetch_crossref_metadata(doi, mailto="academic.studio@local"):
    """Fetch rich metadata for DOI from Crossref REST API."""
    headers = {"User-Agent": f"AcademicStudio/1.0 (mailto:{mailto})"}
    url = f"https://api.crossref.org/works/{doi}"
    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code == 200:
            msg = resp.json().get("message", {})
            title = msg.get("title", [""])[0] if msg.get("title") else "Unknown Title"
            authors = []
            for a in msg.get("author", []):
                given = a.get("given", "").strip()
                family = a.get("family", "").strip()
                name = f"{given} {family}".strip() if given or family else a.get("name", "")
                if name:
                    authors.append(name)
            
            first_author = msg.get("author", [{}])[0].get("family") or (authors[0] if authors else "Author")
            year = (
                msg.get("published-print", {}).get("date-parts", [[None]])[0][0]
                or msg.get("published-online", {}).get("date-parts", [[None]])[0][0]
                or msg.get("created", {}).get("date-parts", [[None]])[0][0]
                or "UnknownYear"
            )
            journal = msg.get("container-title", [""])[0] if msg.get("container-title") else ""
            cites = msg.get("is-referenced-by-count", 0)
            
            # Check for direct Open Access PDF link in Crossref
            oa_link = None
            for link_obj in msg.get("link", []):
                ct = link_obj.get("content-type", "")
                if "application/pdf" in ct or "pdf" in link_obj.get("URL", "").lower():
                    oa_link = link_obj.get("URL")
                    break

            return {
                "success": True,
                "doi": msg.get("DOI", doi),
                "title": title,
                "first_author": first_author,
                "authors": authors,
                "year": year,
                "journal": journal,
                "publisher": msg.get("publisher", ""),
                "citations": cites,
                "url": msg.get("URL", f"https://doi.org/{doi}"),
                "oa_link": oa_link,
                "abstract": msg.get("abstract", "")
            }
    except Exception as e:
        pass
    
    return {
        "success": False,
        "doi": doi,
        "title": doi,
        "first_author": "Unknown",
        "authors": [],
        "year": "Unknown",
        "journal": "",
        "citations": 0,
        "url": f"https://doi.org/{doi}",
        "oa_link": None
    }

def download_pdf_from_url(url, output_path, headers=None, timeout=25):
    """Safely stream and validate a PDF download from a given URL."""
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    if headers:
        default_headers.update(headers)
    try:
        r = requests.get(url, headers=default_headers, timeout=timeout, allow_redirects=True)
        if r.status_code == 200 and len(r.content) > 1500:
            ct = r.headers.get("Content-Type", "").lower()
            if b"%PDF" in r.content[:1024] or "application/pdf" in ct:
                with open(output_path, "wb") as f:
                    f.write(r.content)
                return True
    except Exception:
        pass
    return False

def try_unpaywall(doi, output_path, mailto="academic.studio@local"):
    """
    Query Unpaywall API for Open Access PDF locations.
    Unpaywall indexes 50,000+ journals and university repositories.
    """
    url = f"https://api.unpaywall.org/v2/{doi}?email={mailto}"
    try:
        r = requests.get(url, timeout=12)
        if r.status_code == 200:
            data = r.json()
            if data.get("is_oa"):
                # 1. Best OA location
                best = data.get("best_oa_location") or {}
                best_pdf = best.get("url_for_pdf")
                if best_pdf and download_pdf_from_url(best_pdf, output_path):
                    host = best.get("repository_institution") or "Unpaywall"
                    return {"success": True, "source": f"Open Access (Unpaywall: {host[:20]})"}

                # 2. Iterate other locations
                for loc in data.get("oa_locations", []):
                    pdf_url = loc.get("url_for_pdf")
                    if pdf_url and download_pdf_from_url(pdf_url, output_path):
                        return {"success": True, "source": "Open Access (Unpaywall Repository)"}
    except Exception:
        pass
    return {"success": False}

def try_publisher_highwire(doi, output_path):
    """
    Visit DOI landing page and extract Highwire Press citation_pdf_url meta tag.
    Used by Nature, Science, Springer, Wiley, PLOS, Frontiers, MDPI, Oxford, etc.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    try:
        r = requests.get(f"https://doi.org/{doi}", headers=headers, timeout=15, allow_redirects=True)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            meta_pdf = soup.find("meta", {"name": "citation_pdf_url"}) or soup.find("meta", {"name": "dc.identifier", "scheme": "publisher-id"})
            if meta_pdf and meta_pdf.get("content"):
                pdf_url = meta_pdf["content"]
                if download_pdf_from_url(pdf_url, output_path):
                    return {"success": True, "source": "Open Access (Publisher Direct)"}

            # Check direct download anchor tag
            a_pdf = soup.find("a", href=lambda h: h and (".pdf" in h.lower() or "type=printable" in h.lower()))
            if a_pdf and a_pdf.get("href"):
                link = a_pdf["href"]
                if link.startswith("/"):
                    from urllib.parse import urlparse
                    parsed = urlparse(r.url)
                    link = f"{parsed.scheme}://{parsed.netloc}{link}"
                if download_pdf_from_url(link, output_path):
                    return {"success": True, "source": "Open Access (Publisher Direct)"}
    except Exception:
        pass
    return {"success": False}

def try_europe_pmc(doi, output_path):
    """
    Query Europe PMC / PubMed Central (PMC) API for open access papers.
    """
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:{doi}&format=json"
    try:
        r = requests.get(url, timeout=12)
        if r.status_code == 200:
            data = r.json()
            results = data.get("resultList", {}).get("result", [])
            if results:
                item = results[0]
                pmcid = item.get("pmcid")
                if pmcid:
                    pmc_pdf_url = f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf"
                    if download_pdf_from_url(pmc_pdf_url, output_path):
                        return {"success": True, "source": f"Open Access (Europe PMC: {pmcid})"}
    except Exception:
        pass
    return {"success": False}

def try_preprints(doi, output_path):
    """
    Direct resolver for arXiv and bioRxiv/medRxiv preprints.
    """
    # 1. arXiv
    if "arxiv" in doi.lower() or "10.48550" in doi:
        m = re.search(r'arXiv\.([0-9]+\.[0-9]+)', doi, re.IGNORECASE) or re.search(r'([0-9]{4}\.[0-9]{4,5})', doi)
        if m:
            arxiv_id = m.group(1)
            url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            if download_pdf_from_url(url, output_path):
                return {"success": True, "source": f"Preprint (arXiv: {arxiv_id})"}

    # 2. bioRxiv / medRxiv (10.1101/...)
    if doi.startswith("10.1101/"):
        url = f"https://www.biorxiv.org/content/{doi}.full.pdf"
        if download_pdf_from_url(url, output_path):
            return {"success": True, "source": "Preprint (bioRxiv/medRxiv)"}

    return {"success": False}

def try_download_oa(oa_url, output_path):
    """Attempt download from open access URL."""
    return download_pdf_from_url(oa_url, output_path)

def try_download_scihub(doi, output_path, mirrors=None):
    """Attempt download from active Sci-Hub mirrors."""
    mirrors = mirrors or SCI_HUB_DEFAULT_MIRRORS
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    for mirror in mirrors:
        mirror = mirror.rstrip('/')
        url = f"{mirror}/{doi}"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            pdf_url = None

            # 1. Object with application/pdf
            obj = soup.find("object", type="application/pdf")
            if obj and obj.get("data"):
                pdf_url = obj["data"]

            # 2. Embed or iframe with id=pdf
            if not pdf_url:
                embed = soup.find("embed", id="pdf") or soup.find("iframe", id="pdf")
                if embed and embed.get("src"):
                    pdf_url = embed["src"]

            # 3. Direct button onclick
            if not pdf_url:
                btn = soup.find("button", onclick=True)
                if btn:
                    m = re.search(r'location\.href\s*=\s*[\x27\x22]([^\x27\x22]+)[\x27\x22]', btn['onclick'])
                    if m:
                        pdf_url = m.group(1)

            # 4. Direct <a> tag containing .pdf
            if not pdf_url:
                a_tag = soup.find("a", href=lambda h: h and ".pdf" in h)
                if a_tag:
                    pdf_url = a_tag["href"]

            if pdf_url:
                if pdf_url.startswith("//"):
                    pdf_url = "https:" + pdf_url
                elif pdf_url.startswith("/"):
                    pdf_url = mirror + pdf_url

                # Stream and save PDF
                pdf_resp = requests.get(pdf_url, headers=headers, timeout=30)
                if pdf_resp.status_code == 200 and len(pdf_resp.content) > 1000:
                    with open(output_path, "wb") as f:
                        f.write(pdf_resp.content)
                    return {"success": True, "source": mirror, "size": len(pdf_resp.content)}
        except Exception:
            continue

    return {"success": False}

def generate_bibtex_entry(meta):
    """Format metadata into standard BibTeX entry."""
    first_author_clean = sanitize_filename(meta.get("first_author", "Unknown"), 20)
    year = meta.get("year", "Year")
    cite_key = f"{first_author_clean}{year}"
    authors_str = " and ".join(meta.get("authors", [])) if meta.get("authors") else meta.get("first_author", "Unknown")
    
    title = meta.get("title", "").replace("{", "").replace("}", "")
    journal = meta.get("journal", "")
    doi = meta.get("doi", "")
    url = meta.get("url", "")
    
    bib = f"""@article{{{cite_key},
  title = {{{title}}},
  author = {{{authors_str}}},
  journal = {{{journal}}},
  year = {{{year}}},
  doi = {{{doi}}},
  url = {{{url}}}
}}
"""
    return cite_key, bib

def generate_ris_entry(meta):
    """Format metadata into standard RIS format (Zotero, Mendeley, EndNote)."""
    lines = ["TY  - JOUR"]
    if meta.get("title"):
        lines.append(f"TI  - {meta['title']}")
    for a in meta.get("authors", []):
        lines.append(f"AU  - {a}")
    if not meta.get("authors") and meta.get("first_author"):
        lines.append(f"AU  - {meta['first_author']}")
    if meta.get("journal"):
        lines.append(f"JO  - {meta['journal']}")
        lines.append(f"T2  - {meta['journal']}")
    if meta.get("year"):
        lines.append(f"PY  - {meta['year']}")
    if meta.get("doi"):
        lines.append(f"DO  - {meta['doi']}")
    if meta.get("url"):
        lines.append(f"UR  - {meta['url']}")
    if meta.get("abstract"):
        lines.append(f"AB  - {meta['abstract']}")
    lines.append("ER  - \n")
    return "\n".join(lines)

def generate_enw_entry(meta):
    """Format metadata into EndNote Tagged (.enw) format."""
    lines = ["%0 Journal Article"]
    if meta.get("title"):
        lines.append(f"%T {meta['title']}")
    for a in meta.get("authors", []):
        lines.append(f"%A {a}")
    if not meta.get("authors") and meta.get("first_author"):
        lines.append(f"%A {meta['first_author']}")
    if meta.get("journal"):
        lines.append(f"%J {meta['journal']}")
    if meta.get("year"):
        lines.append(f"%D {meta['year']}")
    if meta.get("doi"):
        lines.append(f"%R {meta['doi']}")
    if meta.get("url"):
        lines.append(f"%U {meta['url']}")
    if meta.get("abstract"):
        lines.append(f"%X {meta['abstract']}")
    return "\n".join(lines) + "\n"

def sync_to_zotero(meta, pdf_path=None, library_id=None, api_key=None, collection_key=None):
    """Optional sync item and attachment to Zotero using pyzotero."""
    try:
        from pyzotero import zotero
        if not library_id or not api_key:
            return {"success": False, "error": "Missing library_id or api_key"}

        zot = zotero.Zotero(library_id, "user", api_key)
        template = zot.item_template("journalArticle")
        template["title"] = meta.get("title", "")
        template["publicationTitle"] = meta.get("journal", "")
        template["date"] = str(meta.get("year", ""))
        template["DOI"] = meta.get("doi", "")
        template["url"] = meta.get("url", "")
        template["abstractNote"] = meta.get("abstract", "")

        creators = []
        for a in meta.get("authors", []):
            parts = a.split(" ")
            if len(parts) > 1:
                creators.append({"creatorType": "author", "firstName": " ".join(parts[:-1]), "lastName": parts[-1]})
            else:
                creators.append({"creatorType": "author", "name": a})
        if creators:
            template["creators"] = creators
        if collection_key:
            template["collections"] = [collection_key]

        created = zot.create_items([template])
        return {"success": True, "created": created}
    except Exception as e:
        return {"success": False, "error": str(e)}

def process_batch(dois, options, progress_callback=None, output_dir="downloads"):
    """
    Process list of DOIs sequentially with progress reporting.
    """
    os.makedirs(output_dir, exist_ok=True)
    results = []
    all_bibs = []
    all_ris = []
    all_enw = []
    
    mirrors = options.get("mirrors") or SCI_HUB_DEFAULT_MIRRORS
    if isinstance(mirrors, str):
        mirrors = [m.strip() for m in mirrors.split(",") if m.strip()]

    rename_mode = options.get("rename_mode", "readable")  # 'readable' or 'doi'
    zotero_enabled = options.get("zotero_enabled", False)
    zotero_id = options.get("zotero_id", "")
    zotero_key = options.get("zotero_key", "")
    
    total = len(dois)
    for idx, raw_doi in enumerate(dois):
        doi = extract_doi(raw_doi)
        if not doi:
            continue

        item_result = {
            "doi": doi,
            "title": "",
            "journal": "",
            "year": "",
            "citations": 0,
            "status": "processing",
            "source": "",
            "pdf_filename": None,
            "pdf_size": 0,
            "bibtex": "",
            "ris": "",
            "enw": "",
            "zotero_synced": False
        }

        if progress_callback:
            progress_callback(idx, total, f"Consultando metadatos para {doi}...", item_result)

        # 1. Fetch metadata
        meta = fetch_crossref_metadata(doi)
        item_result["title"] = meta.get("title", doi)
        item_result["journal"] = meta.get("journal", "")
        item_result["year"] = meta.get("year", "")
        item_result["citations"] = meta.get("citations", 0)

        # 2. Bibliographic Formats (BibTeX, RIS, EndNote)
        cite_key, bib_entry = generate_bibtex_entry(meta)
        ris_entry = generate_ris_entry(meta)
        enw_entry = generate_enw_entry(meta)

        item_result["bibtex"] = bib_entry
        item_result["ris"] = ris_entry
        item_result["enw"] = enw_entry
        item_result["cite_key"] = cite_key

        all_bibs.append(bib_entry)
        all_ris.append(ris_entry)
        all_enw.append(enw_entry)

        # 3. Determine file name
        if rename_mode == "readable":
            auth = sanitize_filename(meta.get("first_author", "Paper"), 25)
            yr = str(meta.get("year", ""))
            tit = sanitize_filename(meta.get("title", ""), 45)
            pdf_name = f"{yr}_{auth}_{tit}.pdf".strip("_")
        else:
            clean_doi = re.sub(r'[^a-zA-Z0-9_\-.]', '_', doi)
            pdf_name = f"{clean_doi}.pdf"

        pdf_path = os.path.join(output_dir, pdf_name)

        if progress_callback:
            progress_callback(idx, total, f"Descargando PDF para {doi}...", item_result)

        # 4. Cascaded Download (Multi-Engine Open Access + Sci-Hub)
        downloaded = False
        source_used = ""

        # Tier 1: Direct link in Crossref metadata
        if meta.get("oa_link"):
            if download_pdf_from_url(meta["oa_link"], pdf_path):
                downloaded = True
                source_used = "Open Access (Crossref)"

        # Tier 2: Unpaywall API (50,000+ journals and repositories)
        if not downloaded:
            res_unpaywall = try_unpaywall(doi, pdf_path)
            if res_unpaywall.get("success"):
                downloaded = True
                source_used = res_unpaywall["source"]

        # Tier 3: Publisher Landing Page (Highwire Press citation_pdf_url meta tag)
        if not downloaded:
            res_highwire = try_publisher_highwire(doi, pdf_path)
            if res_highwire.get("success"):
                downloaded = True
                source_used = res_highwire["source"]

        # Tier 4: Europe PMC / PubMed Central (PMC) API
        if not downloaded:
            res_epmc = try_europe_pmc(doi, pdf_path)
            if res_epmc.get("success"):
                downloaded = True
                source_used = res_epmc["source"]

        # Tier 5: Preprint Resolvers (arXiv / bioRxiv / medRxiv)
        if not downloaded:
            res_prep = try_preprints(doi, pdf_path)
            if res_prep.get("success"):
                downloaded = True
                source_used = res_prep["source"]

        # Tier 6: Sci-Hub Multi-Mirror (.ru, .st, .se)
        if not downloaded:
            res_scihub = try_download_scihub(doi, pdf_path, mirrors=mirrors)
            if res_scihub.get("success"):
                downloaded = True
                source_used = f"Sci-Hub ({res_scihub.get('source', '')})"

        if downloaded and os.path.exists(pdf_path):
            size = os.path.getsize(pdf_path)
            item_result["status"] = "success"
            item_result["source"] = source_used
            item_result["pdf_filename"] = pdf_name
            item_result["pdf_size"] = size

            # Tier C: Zotero sync if requested
            if zotero_enabled and zotero_id and zotero_key:
                z_res = sync_to_zotero(meta, pdf_path=pdf_path, library_id=zotero_id, api_key=zotero_key)
                item_result["zotero_synced"] = z_res.get("success", False)
        else:
            item_result["status"] = "not_found"
            item_result["source"] = "No disponible"

        results.append(item_result)
        time.sleep(0.5)  # Politeness interval

    # Generate bundle zip (PDFs + references.bib + metadata.csv)
    zip_filename = "AcademicPapers_Bundle.zip"
    zip_path = os.path.join(output_dir, zip_filename)
    
    # Save combined BibTeX (.bib)
    bib_path = os.path.join(output_dir, "references.bib")
    with open(bib_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(all_bibs))

    # Save combined RIS (.ris)
    ris_path = os.path.join(output_dir, "references.ris")
    with open(ris_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(all_ris))

    # Save combined EndNote (.enw)
    enw_path = os.path.join(output_dir, "references.enw")
    with open(enw_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(all_enw))

    # Save summary CSV
    csv_path = os.path.join(output_dir, "summary.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["DOI", "Title", "Journal", "Year", "Citations", "Status", "Source", "PDF File"])
        for r in results:
            writer.writerow([
                r["doi"], r["title"], r["journal"], r["year"],
                r["citations"], r["status"], r["source"], r["pdf_filename"] or ""
            ])

    # Build ZIP archive (PDFs + references.bib + references.ris + references.enw + summary.csv)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if os.path.exists(bib_path):
            zf.write(bib_path, "references.bib")
        if os.path.exists(ris_path):
            zf.write(ris_path, "references.ris")
        if os.path.exists(enw_path):
            zf.write(enw_path, "references.enw")
        if os.path.exists(csv_path):
            zf.write(csv_path, "summary.csv")
        for r in results:
            if r.get("pdf_filename"):
                file_full = os.path.join(output_dir, r["pdf_filename"])
                if os.path.exists(file_full):
                    zf.write(file_full, r["pdf_filename"])

    return {
        "results": results,
        "zip_file": zip_filename,
        "total": total,
        "success_count": sum(1 for r in results if r["status"] == "success")
    }
