#!/usr/bin/env python3
"""
Downloader Core Module for Academic Paper Studio.
Handles metadata resolution (Crossref), 7-tier cascaded PDF downloading (OA, Sci-Hub, Anna's Archive),
BibTeX/RIS/EndNote generation, and Zotero synchronization.
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

ANNAS_ARCHIVE_MIRRORS = [
    "https://annas-archive.gl",
    "https://annas-archive.org",
    "https://annas-archive.se"
]

LIBGEN_BOOK_MIRRORS = [
    "https://libgen.li",
    "https://libgen.gs",
    "https://libgen.vg"
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

def try_annas_archive(doi, output_path):
    """
    Tier 7: Query Anna's Archive (SciDB + Z-Library / LibGen / IPFS index) for DOI.
    Tries:
      1. Anna's Archive SciDB direct DOI page (/scidb/{doi})
      2. Anna's Archive unified search (/search?q={doi}) -> MD5 page -> IPFS / LibGen / Fast API links
    """
    from urllib.parse import quote
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    api_key = os.environ.get("ANNAS_ARCHIVE_KEY", "").strip()

    for mirror in ANNAS_ARCHIVE_MIRRORS:
        mirror = mirror.rstrip("/")
        # 1. Try SciDB direct endpoint on Anna's Archive
        try:
            scidb_url = f"{mirror}/scidb/{doi}"
            r = requests.get(scidb_url, headers=headers, timeout=15)
            if r.status_code == 200:
                if b"%PDF" in r.content[:1024]:
                    with open(output_path, "wb") as f:
                        f.write(r.content)
                    return {"success": True, "source": f"Anna's Archive (SciDB)"}

                soup = BeautifulSoup(r.text, "html.parser")
                pdf_url = None
                embed = soup.find("embed", type="application/pdf") or soup.find("iframe", src=True) or soup.find("object", type="application/pdf")
                if embed:
                    pdf_url = embed.get("src") or embed.get("data")
                if not pdf_url:
                    a_tag = soup.find("a", href=lambda h: h and (".pdf" in h.lower() or "ipfs" in h.lower() or "download" in h.lower()))
                    if a_tag:
                        pdf_url = a_tag["href"]
                if pdf_url:
                    if pdf_url.startswith("//"):
                        pdf_url = "https:" + pdf_url
                    elif pdf_url.startswith("/"):
                        pdf_url = mirror + pdf_url
                    if download_pdf_from_url(pdf_url, output_path, headers=headers):
                        return {"success": True, "source": "Anna's Archive (SciDB)"}
        except Exception:
            pass

        # 2. Try Anna's Archive Unified Search (indexes Z-Library, LibGen, Sci-Hub)
        try:
            search_url = f"{mirror}/search?q={quote(doi)}"
            r_search = requests.get(search_url, headers=headers, timeout=15)
            if r_search.status_code == 200:
                md5_matches = re.findall(r'/md5/([a-fA-F0-9]{32})', r_search.text)
                if md5_matches:
                    md5_hash = md5_matches[0].lower()

                    # 2a. Optional Official Fast Download API if key is configured
                    if api_key:
                        fast_api = f"{mirror}/dyn/api/fast_download.json?md5={md5_hash}&key={api_key}"
                        r_fast = requests.get(fast_api, headers=headers, timeout=12)
                        if r_fast.status_code == 200:
                            dl_url = r_fast.json().get("download_url")
                            if dl_url and download_pdf_from_url(dl_url, output_path, headers=headers):
                                return {"success": True, "source": "Anna's Archive (Fast API / Z-Lib)"}

                    # 2b. Parse MD5 details page for IPFS / LibGen / Z-Lib mirror links
                    md5_url = f"{mirror}/md5/{md5_hash}"
                    r_md5 = requests.get(md5_url, headers=headers, timeout=15)
                    if r_md5.status_code == 200:
                        soup_md5 = BeautifulSoup(r_md5.text, "html.parser")
                        candidate_links = []
                        for a in soup_md5.find_all("a", href=True):
                            href = a["href"]
                            if any(k in href.lower() for k in ["ipfs", "library.lol", "libgen", ".pdf", "slow_download"]):
                                if href.startswith("//"):
                                    href = "https:" + href
                                elif href.startswith("/"):
                                    href = mirror + href
                                candidate_links.append(href)

                        for link in candidate_links[:5]:
                            if download_pdf_from_url(link, output_path, headers=headers):
                                return {"success": True, "source": "Anna's Archive (Z-Lib/LibGen)"}
                            # If link is a LibGen/library.lol landing page, extract its direct GET link
                            try:
                                if "library.lol" in link or "libgen" in link:
                                    r_lg = requests.get(link, headers=headers, timeout=12)
                                    if r_lg.status_code == 200:
                                        soup_lg = BeautifulSoup(r_lg.text, "html.parser")
                                        get_a = soup_lg.find("a", href=lambda h: h and ("get.php" in h or ".pdf" in h.lower() or "ipfs" in h.lower()))
                                        if get_a and get_a.get("href"):
                                            dl_link = get_a["href"]
                                            if dl_link.startswith("/"):
                                                from urllib.parse import urlparse
                                                p = urlparse(link)
                                                dl_link = f"{p.scheme}://{p.netloc}{dl_link}"
                                            if download_pdf_from_url(dl_link, output_path, headers=headers):
                                                return {"success": True, "source": "Anna's Archive (LibGen/Z-Lib)"}
                            except Exception:
                                pass
        except Exception:
            continue

    # 3. Unified MD5 Catalog Mirror Fallback (bypasses Cloudflare on cloud servers)
    for lg_mirror in LIBGEN_BOOK_MIRRORS:
        try:
            r_lg = requests.get(f"{lg_mirror.rstrip('/')}/index.php?req={quote(doi)}&res=10", headers=headers, timeout=12)
            if r_lg.status_code == 200:
                md5s = re.findall(r'md5=([a-fA-F0-9]{32})', r_lg.text)
                if md5s:
                    direct_url = resolve_book_download_url(md5s[0].lower())
                    if direct_url and "get.php" in direct_url:
                        if download_pdf_from_url(direct_url, output_path, headers=headers):
                            return {"success": True, "source": "Anna's Archive (Z-Lib/LibGen)"}
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

        # Tier 7: Anna's Archive (SciDB / Z-Library / LibGen / IPFS)
        if not downloaded:
            res_annas = try_annas_archive(doi, pdf_path)
            if res_annas.get("success"):
                downloaded = True
                source_used = res_annas["source"]

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


# ==============================================================================
# BOOK SEARCH & DOWNLOADER ENGINE (Anna's Archive / Z-Library / LibGen Catalog)
# ==============================================================================

LANGUAGE_ALIASES = {
    "es": ["spanish", "español", "espanol", "es", "spa", "castellano"],
    "en": ["english", "inglés", "ingles", "en", "eng"],
    "pt": ["portuguese", "português", "portugues", "pt", "por"],
    "fr": ["french", "français", "francais", "fr", "fre", "fra"],
    "de": ["german", "deutsch", "de", "ger", "deu"],
    "it": ["italian", "italiano", "it", "ita"],
    "ru": ["russian", "ru", "rus"],
    "zh": ["chinese", "zh", "chi", "zho"]
}

def generate_book_citations(book):
    """Generate BibTeX (@book), RIS (TY - BOOK), and EndNote (%0 Book) citations."""
    author_raw = book.get("author") or "Unknown Author"
    first_word = sanitize_filename(author_raw.split(",")[0].split(" ")[0], 18)
    year_str = str(book.get("year") or "Year")
    cite_key = f"{first_word}{year_str}"

    title = (book.get("title") or "Untitled Book").replace("{", "").replace("}", "")
    publisher = book.get("publisher") or ""
    isbn = book.get("isbn") or ""
    url = book.get("annas_url") or ""

    # 1. BibTeX (@book)
    bib = f"""@book{{{cite_key},
  title = {{{title}}},
  author = {{{author_raw}}},
  publisher = {{{publisher}}},
  year = {{{year_str}}},
  isbn = {{{isbn}}},
  url = {{{url}}}
}}"""

    # 2. RIS (BOOK)
    ris_lines = [
        "TY  - BOOK",
        f"TI  - {title}",
        f"AU  - {author_raw}"
    ]
    if publisher:
        ris_lines.append(f"PB  - {publisher}")
    if year_str and year_str.isdigit():
        ris_lines.append(f"PY  - {year_str}")
    if isbn:
        ris_lines.append(f"SN  - {isbn}")
    if url:
        ris_lines.append(f"UR  - {url}")
    ris_lines.append("ER  - ")
    ris = "\n".join(ris_lines)

    # 3. EndNote (.enw)
    enw_lines = [
        "%0 Book",
        f"%T {title}",
        f"%A {author_raw}"
    ]
    if publisher:
        enw_lines.append(f"%I {publisher}")
    if year_str and year_str.isdigit():
        enw_lines.append(f"%D {year_str}")
    if isbn:
        enw_lines.append(f"%@ {isbn}")
    if url:
        enw_lines.append(f"%U {url}")
    enw = "\n".join(enw_lines)

    return bib, ris, enw, cite_key


def search_books_catalog(query, lang="all", year_from=None, year_to=None, ext="all", page=1, max_results=100):
    """
    Search unified book catalog (Anna's Archive / Z-Library / LibGen MD5 index).
    Supports filtering by language, year range (year_from..year_to), file extension (pdf, epub, etc.), and pagination.
    """
    from urllib.parse import quote
    if not query or not query.strip():
        return {"success": False, "books": [], "error": "Empty query"}

    query_clean = query.strip()
    try:
        page_num = max(1, int(page or 1))
    except ValueError:
        page_num = 1

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    # Parse year bounds safely
    y_min = None
    y_max = None
    try:
        if year_from and str(year_from).strip():
            y_min = int(str(year_from).strip())
    except ValueError:
        pass
    try:
        if year_to and str(year_to).strip():
            y_max = int(str(year_to).strip())
    except ValueError:
        pass

    lang_norm = (lang or "all").strip().lower()
    ext_norm = (ext or "all").strip().lower()

    raw_books = []
    seen_md5 = set()
    total_catalog_results = 0
    total_pages = 1

    # 1. Primary Unified Catalog Search (LibGen / Anna's Archive MD5 Index)
    for mirror in LIBGEN_BOOK_MIRRORS:
        mirror = mirror.rstrip("/")
        # Search books (topics[]=l for Sci-Tech/Academic Books, topics[]=f for General/Fiction Books)
        search_url = (
            f"{mirror}/index.php?req={quote(query_clean)}"
            f"&columns[]=t&columns[]=a&columns[]=s&columns[]=y&columns[]=p&columns[]=i"
            f"&objects[]=f&topics[]=l&topics[]=f&res=100&page={page_num}"
        )
        try:
            r = requests.get(search_url, headers=headers, timeout=12)
            if r.status_code != 200:
                continue

            # Extract total catalog count (e.g. Files <span class="badge badge-primary">601</span>)
            m_files = re.search(r'Files\s*<span[^>]*>(\d+)</span>', r.text, re.I)
            if m_files:
                total_catalog_results = int(m_files.group(1))

            # Extract total pages from Paginator("paginator_example_top", total_pages, max_visible, current_page, ...)
            m_pag = re.search(r'Paginator\(\s*["\']paginator_example_top["\']\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', r.text)
            if m_pag:
                total_pages = max(1, int(m_pag.group(1)))
            elif total_catalog_results > 0:
                total_pages = max(1, (total_catalog_results + 24) // 25)

            soup = BeautifulSoup(r.text, "html.parser")
            table = soup.find("table", id="tablelibgen")
            if not table:
                continue

            rows = table.find_all("tr")[1:]
            for row in rows:
                tds = row.find_all("td")
                if len(tds) < 9:
                    continue

                # Extract MD5
                md5_matches = re.findall(r'md5=([a-fA-F0-9]{32})', str(tds[8])) or re.findall(r'/book/([a-fA-F0-9]{32})', str(tds[8]))
                if not md5_matches:
                    continue
                md5_hash = md5_matches[0].lower()
                if md5_hash in seen_md5:
                    continue

                # Extract Title & ISBN from td[0]
                td0 = tds[0]
                title_text = ""
                isbn_text = ""
                a_tags = td0.find_all("a", href=lambda h: h and "edition.php" in h)
                if a_tags:
                    # First edition.php link is the title; second (if green font) is ISBN
                    first_a = a_tags[0]
                    # Remove green ISBN font if nested
                    for font_tag in first_a.find_all("font"):
                        isbn_text = font_tag.get_text(" ", strip=True)
                        font_tag.decompose()
                    title_text = first_a.get_text(" ", strip=True)
                    if len(a_tags) > 1 and not isbn_text:
                        isbn_text = a_tags[1].get_text(" ", strip=True)
                else:
                    title_text = td0.get_text(" ", strip=True)

                if not title_text:
                    continue

                author_text = tds[1].get_text(" ", strip=True) or "Autor desconocido"
                publisher_text = tds[2].get_text(" ", strip=True) or ""
                year_raw = tds[3].get_text(" ", strip=True) or ""
                lang_raw = tds[4].get_text(" ", strip=True) or ""
                pages_raw = tds[5].get_text(" ", strip=True) or ""
                size_raw = tds[6].get_text(" ", strip=True) or ""
                ext_raw = tds[7].get_text(" ", strip=True).lower() or "pdf"

                # Extract 4-digit year
                ym = re.search(r'\b(18\d\d|19\d\d|20\d\d)\b', year_raw)
                book_year = int(ym.group(1)) if ym else None

                seen_md5.add(md5_hash)
                raw_books.append({
                    "md5": md5_hash,
                    "title": title_text,
                    "author": author_text,
                    "publisher": publisher_text,
                    "year": book_year if book_year else (year_raw or "N/A"),
                    "year_num": book_year,
                    "language": lang_raw or "Unknown",
                    "pages": pages_raw,
                    "size": size_raw,
                    "extension": ext_raw,
                    "isbn": isbn_text,
                    "annas_url": f"https://annas-archive.gl/md5/{md5_hash}",
                    "direct_resolve_url": f"/api/books/resolve?md5={md5_hash}"
                })

            if raw_books:
                break
        except Exception:
            continue

    # 2. Secondary Fallback: Direct Anna's Archive HTML Search if primary mirrors were unreachable
    if not raw_books:
        for aa_mirror in ANNAS_ARCHIVE_MIRRORS:
            aa_mirror = aa_mirror.rstrip("/")
            aa_url = f"{aa_mirror}/search?q={quote(query_clean)}&content=book_any"
            if lang_norm != "all":
                aa_url += f"&lang={quote(lang_norm)}"
            if ext_norm != "all":
                aa_url += f"&ext={quote(ext_norm)}"
            try:
                r_aa = requests.get(aa_url, headers=headers, timeout=12)
                if r_aa.status_code == 200 and "/md5/" in r_aa.text:
                    clean_html = r_aa.text.replace("<!--", "").replace("-->", "")
                    soup_aa = BeautifulSoup(clean_html, "html.parser")
                    for a in soup_aa.find_all("a", href=re.compile(r'^/md5/[a-fA-F0-9]{32}')):
                        md5_hash = a["href"].split("/md5/")[1][:32].lower()
                        if md5_hash in seen_md5:
                            continue
                        texts = list(a.stripped_strings)
                        if not texts:
                            continue
                        title_t = texts[0] if len(texts) == 1 else (texts[1] if len(texts) > 1 else texts[0])
                        meta_line = texts[0] if len(texts) > 1 else ""
                        ym = re.search(r'\b(19\d\d|20\d\d)\b', " ".join(texts))
                        book_year = int(ym.group(1)) if ym else None
                        ext_m = re.search(r'\b(pdf|epub|djvu|mobi)\b', meta_line.lower())
                        ext_val = ext_m.group(1) if ext_m else "pdf"
                        seen_md5.add(md5_hash)
                        raw_books.append({
                            "md5": md5_hash,
                            "title": title_t,
                            "author": texts[2] if len(texts) > 2 else "Autor",
                            "publisher": "",
                            "year": book_year or "N/A",
                            "year_num": book_year,
                            "language": lang_norm.upper() if lang_norm != "all" else "Unknown",
                            "pages": "",
                            "size": "",
                            "extension": ext_val,
                            "isbn": "",
                            "annas_url": f"{aa_mirror}/md5/{md5_hash}",
                            "direct_resolve_url": f"/api/books/resolve?md5={md5_hash}"
                        })
                    if raw_books:
                        break
            except Exception:
                continue

    # 3. Apply User Filters (Language, Year Period, Format/Extension)
    filtered_books = []
    for b in raw_books:
        # Filter by Extension
        if ext_norm != "all":
            if b["extension"].lower() != ext_norm:
                continue

        # Filter by Language
        if lang_norm != "all":
            aliases = LANGUAGE_ALIASES.get(lang_norm, [lang_norm])
            b_lang_lower = (b["language"] or "").lower()
            if not any(alias in b_lang_lower for alias in aliases):
                continue

        # Filter by Year Range (year_from .. year_to)
        b_yr = b.get("year_num")
        if y_min is not None:
            if b_yr is None or b_yr < y_min:
                continue
        if y_max is not None:
            if b_yr is None or b_yr > y_max:
                continue

        # Generate @book citations (BibTeX, RIS, EndNote)
        bib, ris, enw, cite_key = generate_book_citations(b)
        b["bibtex"] = bib
        b["ris"] = ris
        b["enw"] = enw
        b["cite_key"] = cite_key

        filtered_books.append(b)
        if len(filtered_books) >= max_results:
            break

    if total_catalog_results == 0 and raw_books:
        total_catalog_results = len(raw_books)

    return {
        "success": True,
        "query": query_clean,
        "page": page_num,
        "total_pages": total_pages,
        "per_page": 25,
        "total_catalog_results": total_catalog_results,
        "has_more": page_num < total_pages,
        "total_found": len(filtered_books),
        "books": filtered_books
    }


def resolve_book_download_url(md5_hash):
    """
    Given a 32-char MD5 book hash, resolves the direct fast download link (GET)
    from LibGen / Anna's Archive mirrors so the user's browser downloads the PDF/EPUB immediately.
    """
    if not md5_hash or not re.match(r'^[a-fA-F0-9]{32}$', md5_hash.strip()):
        return "https://annas-archive.gl"

    md5_clean = md5_hash.strip().lower()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    # 1. Optional Anna's Archive Official Fast Download API if key is set
    api_key = os.environ.get("ANNAS_ARCHIVE_KEY", "").strip()
    if api_key:
        for aa_mirror in ANNAS_ARCHIVE_MIRRORS:
            try:
                fast_url = f"{aa_mirror.rstrip('/')}/dyn/api/fast_download.json?md5={md5_clean}&key={api_key}"
                r = requests.get(fast_url, headers=headers, timeout=8)
                if r.status_code == 200:
                    dl = r.json().get("download_url")
                    if dl:
                        return dl
            except Exception:
                pass

    # 2. Resolve direct GET download link via LibGen mirrors (ads.php -> get.php?md5=...&key=...)
    for mirror in LIBGEN_BOOK_MIRRORS:
        mirror = mirror.rstrip("/")
        try:
            ads_url = f"{mirror}/ads.php?md5={md5_clean}"
            r = requests.get(ads_url, headers=headers, timeout=10)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                a_get = soup.find("a", href=lambda h: h and "get.php" in h)
                if a_get and a_get.get("href"):
                    href = a_get["href"]
                    if href.startswith("http"):
                        return href
                    return f"{mirror}/{href.lstrip('/')}"
        except Exception:
            continue

    # 3. Fallback to Anna's Archive MD5 page where the user can pick any slow/partner server
    return f"https://annas-archive.gl/md5/{md5_clean}"

