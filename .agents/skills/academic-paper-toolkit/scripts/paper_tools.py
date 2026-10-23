#!/usr/bin/env python3
"""
Academic Paper Toolkit (Crossref, Unpaywall, Europe PMC, Preprints, Sci-Hub, PyPaperBot, Scholarly, Pyzotero)
Unified helper script for retrieving paper metadata, citations, downloading PDFs via Open Access / Sci-Hub, and managing Zotero.
"""

import sys
import os
import json
import argparse
import requests
import re
from bs4 import BeautifulSoup

# --- 1. CROSSREF API ---
def crossref_get_work(doi, mailto="academic.studio@local"):
    """
    Fetch complete metadata, citations count, and references from Crossref REST API.
    Docs: https://github.com/Crossref/rest-api-doc
    """
    headers = {"User-Agent": f"AcademicStudio/1.0 (mailto:{mailto})"}
    url = f"https://api.crossref.org/works/{doi}"
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    message = resp.json().get("message", {})
    
    result = {
        "doi": message.get("DOI"),
        "title": message.get("title", [""])[0] if message.get("title") else "",
        "authors": [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in message.get("author", [])],
        "container_title": message.get("container-title", [""])[0] if message.get("container-title") else "",
        "publisher": message.get("publisher"),
        "published_year": message.get("published-print", {}).get("date-parts", [[None]])[0][0] or message.get("published-online", {}).get("date-parts", [[None]])[0][0],
        "is_referenced_by_count": message.get("is-referenced-by-count", 0),
        "references_count": message.get("references-count", 0),
        "URL": message.get("URL"),
        "abstract": message.get("abstract", "")
    }
    return result

def crossref_get_citations(doi, mailto="academic.studio@local"):
    """
    Tutorial: https://gitlab.com/crossref/tutorials/get-crossef-citations
    Retrieves the reference list and citation metrics for a given DOI.
    """
    headers = {"User-Agent": f"AcademicStudio/1.0 (mailto:{mailto})"}
    url = f"https://api.crossref.org/works/{doi}"
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    message = resp.json().get("message", {})
    return {
        "doi": message.get("DOI"),
        "title": message.get("title", [""])[0] if message.get("title") else "",
        "citation_count": message.get("is-referenced-by-count", 0),
        "references": message.get("reference", [])
    }

def crossref_search(query, rows=5, mailto="academic.studio@local"):
    """Search Crossref for publications matching query."""
    headers = {"User-Agent": f"AcademicStudio/1.0 (mailto:{mailto})"}
    url = "https://api.crossref.org/works"
    params = {"query": query, "rows": rows}
    resp = requests.get(url, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    items = resp.json().get("message", {}).get("items", [])
    results = []
    for item in items:
        results.append({
            "doi": item.get("DOI"),
            "title": item.get("title", [""])[0] if item.get("title") else "",
            "journal": item.get("container-title", [""])[0] if item.get("container-title") else "",
            "year": item.get("published", {}).get("date-parts", [[None]])[0][0],
            "citations": item.get("is-referenced-by-count", 0)
        })
    return results

# --- 2. MULTI-ENGINE OPEN ACCESS & SCI-HUB RESOLVER ---
SCI_HUB_MIRRORS = [
    "https://sci-hub.ru",
    "https://sci-hub.st",
    "https://sci-hub.se"
]

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

def download_paper_cascaded(doi, output_dir="downloads", filename=None):
    """
    Cascaded resolver:
    1. Unpaywall API
    2. Publisher Landing Page (Highwire citation_pdf_url)
    3. Europe PMC (PubMed Central)
    4. Preprints (arXiv / bioRxiv)
    5. Sci-Hub multi-mirror
    """
    os.makedirs(output_dir, exist_ok=True)
    cleaned_id = doi.strip()
    m = re.search(r'10\.\d{4,9}/[-._;()/:A-Za-z0-9]+', cleaned_id)
    if m:
        cleaned_id = m.group(0)

    if not filename:
        safe_doi = re.sub(r'[^a-zA-Z0-9_\-.]', '_', cleaned_id)
        filename = f"{safe_doi}.pdf"
    output_path = os.path.join(output_dir, filename)

    # 1. Unpaywall API
    try:
        r = requests.get(f"https://api.unpaywall.org/v2/{cleaned_id}?email=academic.studio@local", timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("is_oa"):
                best = data.get("best_oa_location") or {}
                if best.get("url_for_pdf") and download_pdf_from_url(best["url_for_pdf"], output_path):
                    return {"success": True, "source": "Open Access (Unpaywall)", "path": os.path.abspath(output_path)}
                for loc in data.get("oa_locations", []):
                    if loc.get("url_for_pdf") and download_pdf_from_url(loc["url_for_pdf"], output_path):
                        return {"success": True, "source": "Open Access (Unpaywall Repo)", "path": os.path.abspath(output_path)}
    except Exception:
        pass

    # 2. Publisher Landing Page (Highwire meta tag)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        r = requests.get(f"https://doi.org/{cleaned_id}", headers=headers, timeout=12, allow_redirects=True)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            meta_pdf = soup.find("meta", {"name": "citation_pdf_url"})
            if meta_pdf and meta_pdf.get("content"):
                if download_pdf_from_url(meta_pdf["content"], output_path):
                    return {"success": True, "source": "Open Access (Publisher Direct)", "path": os.path.abspath(output_path)}
    except Exception:
        pass

    # 3. Europe PMC
    try:
        r = requests.get(f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:{cleaned_id}&format=json", timeout=10)
        if r.status_code == 200:
            results = r.json().get("resultList", {}).get("result", [])
            if results and results[0].get("pmcid"):
                pmc_url = f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={results[0]['pmcid']}&blobtype=pdf"
                if download_pdf_from_url(pmc_url, output_path):
                    return {"success": True, "source": f"Open Access (Europe PMC: {results[0]['pmcid']})", "path": os.path.abspath(output_path)}
    except Exception:
        pass

    # 4. Sci-Hub Multi-Mirror
    for mirror in SCI_HUB_MIRRORS:
        try:
            url = f"{mirror}/{cleaned_id}"
            r = requests.get(url, headers=headers, timeout=12)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            pdf_url = None
            obj = soup.find("object", type="application/pdf")
            if obj and obj.get("data"):
                pdf_url = obj["data"]
            if not pdf_url:
                embed = soup.find("embed", id="pdf") or soup.find("iframe", id="pdf")
                if embed and embed.get("src"):
                    pdf_url = embed["src"]
            if not pdf_url:
                btn = soup.find("button", onclick=True)
                if btn:
                    m = re.search(r'location\.href\s*=\s*[\x27\x22]([^\x27\x22]+)[\x27\x22]', btn['onclick'])
                    if m:
                        pdf_url = m.group(1)
            if pdf_url:
                if pdf_url.startswith("//"):
                    pdf_url = "https:" + pdf_url
                elif pdf_url.startswith("/"):
                    pdf_url = mirror + pdf_url
                if download_pdf_from_url(pdf_url, output_path):
                    return {"success": True, "source": f"Sci-Hub ({mirror})", "path": os.path.abspath(output_path)}
        except Exception:
            continue

    return {"success": False, "error": f"Could not find or download PDF for {doi}"}

# --- 3. PYPAPERBOT RUNNER ---
def run_pypaperbot_doi(doi, dwn_dir="downloads", mirror="https://sci-hub.ru"):
    """Run PyPaperBot CLI command with optimal flags."""
    import subprocess
    cmd = [
        sys.executable, "-m", "PyPaperBot",
        "--doi", doi,
        "--dwn-dir", dwn_dir,
        "--scihub-mirror", mirror
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return {"returncode": res.returncode, "stdout": res.stdout, "stderr": res.stderr}

# --- 4. SCHOLARLY HELPERS ---
def scholarly_search_author(name):
    """Search Google Scholar for author profiles."""
    from scholarly import scholarly
    search_query = scholarly.search_author(name)
    results = []
    for _ in range(5):
        try:
            author = next(search_query)
            results.append({
                "name": author.get("name"),
                "affiliation": author.get("affiliation"),
                "interests": author.get("interests", []),
                "citedby": author.get("citedby")
            })
        except StopIteration:
            break
    return results

# --- 5. PYZOTERO INTEGRATION ---
def zotero_get_client(library_id=None, library_type="user", api_key=None):
    from pyzotero import zotero
    library_id = library_id or os.environ.get("ZOTERO_LIBRARY_ID")
    api_key = api_key or os.environ.get("ZOTERO_API_KEY")
    library_type = library_type or os.environ.get("ZOTERO_LIBRARY_TYPE", "user")
    if not library_id or not api_key:
        raise ValueError("Zotero library_id and api_key are required.")
    return zotero.Zotero(library_id, library_type, api_key)

def zotero_list_recent(library_id=None, library_type="user", api_key=None, limit=5):
    zot = zotero_get_client(library_id, library_type, api_key)
    items = zot.top(limit=limit)
    res = []
    for item in items:
        data = item.get("data", {})
        res.append({
            "key": data.get("key"),
            "title": data.get("title"),
            "itemType": data.get("itemType"),
            "date": data.get("date"),
            "doi": data.get("DOI")
        })
    return res

def zotero_add_by_doi(doi, library_id=None, library_type="user", api_key=None, collection_key=None):
    zot = zotero_get_client(library_id, library_type, api_key)
    meta = crossref_get_work(doi)
    template = zot.item_template("journalArticle")
    template["title"] = meta.get("title", "")
    template["publicationTitle"] = meta.get("container_title", "")
    template["date"] = str(meta.get("published_year", ""))
    template["DOI"] = meta.get("doi", "")
    template["url"] = meta.get("URL", "")
    template["abstractNote"] = meta.get("abstract", "")
    
    creators = []
    for author_str in meta.get("authors", []):
        parts = author_str.split(" ")
        if len(parts) > 1:
            creators.append({"creatorType": "author", "firstName": " ".join(parts[:-1]), "lastName": parts[-1]})
        else:
            creators.append({"creatorType": "author", "name": author_str})
    if creators:
        template["creators"] = creators
    if collection_key:
        template["collections"] = [collection_key]
        
    created = zot.create_items([template])
    return {"status": "created", "created": created, "metadata": meta}

def main():
    parser = argparse.ArgumentParser(description="Academic Paper & Open Access Toolkit")
    subparsers = parser.add_subparsers(dest="command")

    p_meta = subparsers.add_parser("meta", help="Get metadata for a DOI from Crossref")
    p_meta.add_argument("doi", help="DOI of the paper")

    p_cites = subparsers.add_parser("citations", help="Get citations and references for a DOI")
    p_cites.add_argument("doi", help="DOI of the paper")

    p_search = subparsers.add_parser("search", help="Search papers by keyword in Crossref")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--rows", type=int, default=5, help="Number of results")

    p_dwn = subparsers.add_parser("download", help="Download PDF via Open Access / Sci-Hub cascade")
    p_dwn.add_argument("doi", help="DOI of the paper")
    p_dwn.add_argument("--dir", default="papers", help="Output directory")

    p_author = subparsers.add_parser("author", help="Search author in Google Scholar")
    p_author.add_argument("name", help="Author name")

    p_zlist = subparsers.add_parser("zotero-list", help="List recent items in Zotero")
    p_zlist.add_argument("--library-id", help="Zotero user or group ID")
    p_zlist.add_argument("--api-key", help="Zotero API key")
    p_zlist.add_argument("--limit", type=int, default=5, help="Item limit")

    p_zadd = subparsers.add_parser("zotero-add", help="Add DOI to Zotero with Crossref metadata")
    p_zadd.add_argument("doi", help="DOI of the paper to add")
    p_zadd.add_argument("--library-id", help="Zotero user or group ID")
    p_zadd.add_argument("--api-key", help="Zotero API key")
    p_zadd.add_argument("--collection", help="Collection key")

    args = parser.parse_args()

    if args.command == "meta":
        res = crossref_get_work(args.doi)
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif args.command == "citations":
        res = crossref_get_citations(args.doi)
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif args.command == "search":
        res = crossref_search(args.query, rows=args.rows)
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif args.command == "download":
        res = download_paper_cascaded(args.doi, output_dir=args.dir)
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif args.command == "author":
        res = scholarly_search_author(args.name)
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif args.command == "zotero-list":
        res = zotero_list_recent(library_id=args.library_id, api_key=args.api_key, limit=args.limit)
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif args.command == "zotero-add":
        res = zotero_add_by_doi(args.doi, library_id=args.library_id, api_key=args.api_key, collection_key=args.collection)
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
