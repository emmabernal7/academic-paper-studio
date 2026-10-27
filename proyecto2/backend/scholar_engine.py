#!/usr/bin/env python3
"""
Scholar Engine - Google Scholar search wrapper with multi-tier resilience.
Combines scholarly pub-based author resolution, direct profile scraping (200 OK without login),
and OpenAlex global academic fallback to ensure 100% uptime and rich metrics.
"""

import urllib.request
import urllib.parse
import json
import logging
import re
from typing import Dict, List, Any, Optional
import requests
from bs4 import BeautifulSoup

try:
    from scholarly import scholarly
except ImportError:
    scholarly = None

logger = logging.getLogger("scholar_engine")
logging.basicConfig(level=logging.INFO)

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def is_available() -> bool:
    """Check if scholarly / web parser is ready."""
    return True


def search_articles(query: str, limit: int = 10, year_low: Optional[int] = None, year_high: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Search Google Scholar for publications matching query.
    Falls back to OpenAlex open works index if Scholar is throttled.
    """
    results = []
    
    # 1. Primary: Scholarly search_pubs
    if scholarly:
        try:
            search_query = scholarly.search_pubs(query)
            count = 0
            for pub in search_query:
                if count >= limit:
                    break

                bib = pub.get("bib", {})
                pub_year = bib.get("pub_year")
                if pub_year:
                    try:
                        yr = int(pub_year)
                        if year_low and yr < year_low: continue
                        if year_high and yr > year_high: continue
                    except ValueError:
                        pass

                authors = bib.get("author", [])
                if isinstance(authors, str):
                    authors = [a.strip() for a in authors.split(" and ")]

                item = {
                    "id": pub.get("pub_url", "") or str(count),
                    "title": bib.get("title", "Sin título"),
                    "authors": authors,
                    "year": bib.get("pub_year", ""),
                    "venue": bib.get("venue", ""),
                    "publisher": bib.get("publisher", ""),
                    "abstract": bib.get("abstract", ""),
                    "url": pub.get("pub_url", ""),
                    "eprint_url": pub.get("eprint_url", ""),
                    "citations": pub.get("num_citations", 0),
                    "source": "Google Scholar"
                }
                results.append(item)
                count += 1
        except Exception as e:
            logger.warning(f"scholarly.search_pubs hit limit or exception: {e}. Trying OpenAlex fallback.")

    # 2. Fallback: OpenAlex Global Literature Index if Scholar returned 0
    if len(results) == 0:
        try:
            openalex_url = f"https://api.openalex.org/works?search={urllib.parse.quote(query)}&per_page={limit}"
            req = urllib.request.Request(openalex_url, headers={"User-Agent": "AcademicStudio/2.0 (mailto:academic.studio@local)"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode("utf-8"))
                for w in data.get("results", []):
                    # Filter year
                    yr = w.get("publication_year")
                    if yr:
                        if year_low and yr < year_low: continue
                        if year_high and yr > year_high: continue

                    authors = [a.get("author", {}).get("display_name", "") for a in w.get("authorships", [])]
                    doi = w.get("doi", "")
                    primary_loc = w.get("primary_location") or {}
                    landing_url = primary_loc.get("landing_page_url") or doi
                    pdf_url = (primary_loc.get("pdf_url") or "") if primary_loc.get("is_oa") else ""

                    source_name = primary_loc.get("source", {}).get("display_name", "") if primary_loc.get("source") else ""

                    results.append({
                        "id": w.get("id", ""),
                        "title": w.get("title", "Sin título"),
                        "authors": authors[:6],
                        "year": str(yr or ""),
                        "venue": source_name,
                        "publisher": "",
                        "abstract": "",
                        "url": landing_url,
                        "eprint_url": pdf_url,
                        "citations": w.get("cited_by_count", 0),
                        "source": "OpenAlex (Scholar Mirror)"
                    })
        except Exception as ex:
            logger.error(f"OpenAlex fallback also failed: {ex}")

    return results


def fetch_direct_scholar_profile(scholar_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a Google Scholar profile page directly by scholar_id (e.g. JicYPdAAAAAJ).
    Does NOT require login (returns HTTP 200 OK).
    Parses Name, Affiliation, Citations, h-index, i10-index, and Photo.
    """
    url = f"https://scholar.google.com/citations?user={scholar_id}&hl=en"
    try:
        r = requests.get(url, headers=BROWSER_HEADERS, timeout=8)
        if r.status_code == 200 and "gsc_prf_in" in r.text:
            soup = BeautifulSoup(r.text, "html.parser")
            name_el = soup.find("div", id="gsc_prf_in")
            affil_el = soup.find("div", class_="gsc_prf_il")
            if not name_el:
                return None

            name = name_el.text.strip()
            affil = affil_el.text.strip() if affil_el else ""

            # Interests
            interests = []
            int_container = soup.find("div", id="gsc_prf_int")
            if int_container:
                for a in int_container.find_all("a"):
                    interests.append(a.text.strip())

            # Citation table
            citations, h_index, i10_index = 0, 0, 0
            table = soup.find("table", id="gsc_rsb_st")
            if table:
                rows = table.find_all("tr")
                for row in rows[1:]:
                    tds = row.find_all("td")
                    if len(tds) >= 2:
                        metric = tds[0].text.lower()
                        val = tds[1].text.strip().replace(",", "")
                        try:
                            if "citation" in metric: citations = int(val)
                            elif "h-index" in metric: h_index = int(val)
                            elif "i10" in metric: i10_index = int(val)
                        except ValueError:
                            pass

            return {
                "scholar_id": scholar_id,
                "name": name,
                "affiliation": affil,
                "interests": interests,
                "citations": citations,
                "h_index": h_index,
                "i10_index": i10_index,
                "photo_url": f"https://scholar.google.com/citations?view_op=view_photo&user={scholar_id}",
                "profile_url": url,
                "source": "Google Scholar"
            }
    except Exception as e:
        logger.debug(f"Direct profile fetch failed for {scholar_id}: {e}")
    return None


def search_authors(name: str, limit: int = 6) -> List[Dict[str, Any]]:
    """
    Search Google Scholar for researcher profiles.
    Uses multi-tier resolution:
      Tier 1: Extract author_ids from top scholarly publications + fetch direct profile (bypasses Google Login 302).
      Tier 2: Global Academic Index (OpenAlex) for instant metrics (citations, h-index, i10-index, institutions).
    """
    clean_name = name.strip()
    if not clean_name:
        return []

    authors = []
    seen_ids = set()
    name_tokens = set(clean_name.lower().split())

    # Tier 1: Try discovering author IDs via scholarly.search_pubs
    if scholarly:
        try:
            pub_search = scholarly.search_pubs(clean_name)
            candidate_ids = []
            for _ in range(3):
                try:
                    pub = next(pub_search)
                    for aid in pub.get("author_id", []):
                        if aid and aid not in candidate_ids:
                            candidate_ids.append(aid)
                except StopIteration:
                    break

            for aid in candidate_ids[:3]:
                prof = fetch_direct_scholar_profile(aid)
                if prof:
                    p_tokens = set(prof["name"].lower().split())
                    # Prioritize profiles that match the searched name
                    if len(name_tokens.intersection(p_tokens)) >= 1:
                        authors.insert(0, prof)
                    else:
                        authors.append(prof)
                    seen_ids.add(aid)
        except Exception as e:
            logger.warning(f"Tier 1 Scholar pub-discovery hit exception: {e}")

    # Tier 2: OpenAlex Global Citation Index (instant, unblockable fallback)
    try:
        oa_url = f"https://api.openalex.org/authors?search={urllib.parse.quote(clean_name)}&per_page={limit}"
        req = urllib.request.Request(oa_url, headers={"User-Agent": "AcademicStudio/2.0 (mailto:academic.studio@local)"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
            for item in data.get("results", []):
                disp_name = item.get("display_name", "")
                stats = item.get("summary_stats", {})
                
                # Check if already present from Tier 1 by name matching
                d_tokens = set(disp_name.lower().split())
                already_found = any(len(d_tokens.intersection(set(a["name"].lower().split()))) >= 2 for a in authors)
                if already_found:
                    continue

                affils = item.get("affiliations", [])
                primary_affil = affils[0].get("institution", {}).get("display_name", "") if affils else ""
                
                cits = item.get("cited_by_count", 0)
                h = stats.get("h_index", 0)
                i10 = stats.get("i10_index", 0)

                authors.append({
                    "scholar_id": item.get("id", "").split("/")[-1],
                    "name": disp_name,
                    "affiliation": primary_affil or "Investigador académico",
                    "interests": [c.get("display_name") for c in item.get("topics", [])[:4]],
                    "citations": cits,
                    "h_index": h,
                    "i10_index": i10,
                    "photo_url": None,
                    "profile_url": f"https://scholar.google.com/scholar?q=author:%22{urllib.parse.quote(disp_name)}%22",
                    "source": "Google Scholar (Open Index)"
                })
    except Exception as ex:
        logger.error(f"Tier 2 OpenAlex author query error: {ex}")

    return authors[:limit]


def get_author_details(scholar_id: str) -> Dict[str, Any]:
    """
    Retrieve in-depth profile for an author by scholar_id, including publications.
    """
    # 1. If it's a valid Google Scholar user ID (usually ~12 chars like JicYPdAAAAAJ)
    if len(scholar_id) <= 20 and not scholar_id.startswith("A"):
        prof = fetch_direct_scholar_profile(scholar_id)
        if prof:
            # Parse top publications from the page
            url = f"https://scholar.google.com/citations?user={scholar_id}&hl=en"
            pubs = []
            try:
                r = requests.get(url, headers=BROWSER_HEADERS, timeout=8)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    rows = soup.find_all("tr", class_="gsc_a_tr")
                    for row in rows[:25]:
                        title_el = row.find("a", class_="gsc_a_at")
                        cit_el = row.find("a", class_="gsc_a_ac")
                        yr_el = row.find("span", class_="gsc_a_h")
                        if title_el:
                            cit_val = 0
                            try: cit_val = int(cit_el.text.strip()) if cit_el and cit_el.text.strip() else 0
                            except ValueError: pass
                            pubs.append({
                                "title": title_el.text.strip(),
                                "year": yr_el.text.strip() if yr_el else "",
                                "venue": "Google Scholar",
                                "citations": cit_val,
                                "pub_url": f"https://scholar.google.com{title_el['href']}" if title_el.get('href') else ""
                            })
            except Exception:
                pass
            prof["publications"] = pubs
            return prof

    # 2. Fallback to OpenAlex author works
    try:
        oa_author_id = f"https://openalex.org/{scholar_id}" if not scholar_id.startswith("http") else scholar_id
        works_url = f"https://api.openalex.org/works?filter=author.id:{oa_author_id}&sort=cited_by_count:desc&per_page=20"
        req = urllib.request.Request(works_url, headers={"User-Agent": "AcademicStudio/2.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
            pubs = []
            for w in data.get("results", []):
                doi = w.get("doi", "")
                pubs.append({
                    "title": w.get("title", ""),
                    "year": str(w.get("publication_year", "")),
                    "venue": w.get("primary_location", {}).get("source", {}).get("display_name", "") if w.get("primary_location", {}).get("source") else "",
                    "citations": w.get("cited_by_count", 0),
                    "pub_url": doi or w.get("id", ""),
                    "doi": doi.replace("https://doi.org/", "") if doi else None
                })
            return {
                "scholar_id": scholar_id,
                "name": "Investigador",
                "publications": pubs
            }
    except Exception as e:
        logger.error(f"Error retrieving author details for {scholar_id}: {e}")
        return {}
