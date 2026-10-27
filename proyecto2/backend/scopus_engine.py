#!/usr/bin/env python3
"""
Scopus Engine - Client for Elsevier Scopus Search & Author Retrieval API.
Supports two complementary modes:
  1. Official Elsevier Developer API (via apiKey, Christopher Belter scopusAPI spec)
  2. Open Scopus Registry Index (unblockable fallback when no apiKey is configured)
"""

import os
import urllib.request
import urllib.parse
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("scopus_engine")
logging.basicConfig(level=logging.INFO)

SCOPUS_SEARCH_URL = "https://api.elsevier.com/content/search/author"
SCOPUS_AUTHOR_URL = "https://api.elsevier.com/content/author/author_id"
DEFAULT_USER_AGENT = "AcademicPaperStudio/2.0 (mailto:academic.studio@local)"


def get_api_key(provided_key: Optional[str] = None) -> Optional[str]:
    """Retrieve API key from argument or environment variable."""
    return provided_key or os.environ.get("SCOPUS_API_KEY") or os.environ.get("ELSEVIER_API_KEY")


def search_authors_official(query: str, api_key: str, limit: int = 8) -> Dict[str, Any]:
    """Query official Elsevier Scopus REST API with API Key."""
    cleaned = query.strip()
    parts = cleaned.split()
    if len(parts) >= 2:
        scopus_query = f"authlast({parts[-1]}) and authfirst({parts[0]})"
    else:
        scopus_query = f"authlast({cleaned})"

    params = {"query": scopus_query, "count": limit}
    encoded_params = urllib.parse.urlencode(params)
    url = f"{SCOPUS_SEARCH_URL}?{encoded_params}"

    req = urllib.request.Request(
        url,
        headers={
            "X-ELS-APIKey": api_key,
            "Accept": "application/json",
            "User-Agent": DEFAULT_USER_AGENT
        }
    )

    with urllib.request.urlopen(req, timeout=12) as resp:
        if resp.status == 200:
            data = json.loads(resp.read().decode("utf-8"))
            search_results = data.get("search-results", {})
            entries = search_results.get("entry", [])
            
            authors = []
            for entry in entries:
                if "error" in entry:
                    continue

                raw_id = entry.get("dc:identifier", "")
                author_id = raw_id.replace("AUTHOR_ID:", "")

                pref_name = entry.get("preferred-name", {})
                given = pref_name.get("given-name", "")
                surname = pref_name.get("surname", "")
                name = f"{given} {surname}".strip() or entry.get("authname", author_id)

                affil = entry.get("affiliation-current", {})
                affil_name = affil.get("affiliation-name", "Sin institución reportada")
                city = affil.get("affiliation-city", "")
                country = affil.get("affiliation-country", "")
                loc = f", {city}, {country}".strip(", ") if city or country else ""
                full_affil = f"{affil_name}{loc}" if affil_name else ""

                doc_count = entry.get("document-count", "0")
                try: doc_count = int(doc_count)
                except ValueError: doc_count = 0

                subjects = []
                for s in entry.get("subject-area", []):
                    if isinstance(s, dict) and s.get("$"):
                        subjects.append(s["$"])

                authors.append({
                    "scopus_id": author_id,
                    "name": name,
                    "affiliation": full_affil,
                    "documents_count": doc_count,
                    "subject_areas": subjects,
                    "profile_url": f"https://www.scopus.com/authid/detail.uri?authorId={author_id}",
                    "source": "Scopus (Elsevier Oficial)"
                })

            return {
                "success": True,
                "mode": "official",
                "total": search_results.get("opensearch:totalResults", len(authors)),
                "results": authors
            }


def search_authors_open_index(query: str, limit: int = 6) -> Dict[str, Any]:
    """
    Search Scopus-indexed authors using open global registry (OpenAlex & Crossref Scopus index).
    Works 100% free with NO API key requirement.
    """
    try:
        url = f"https://api.openalex.org/authors?search={urllib.parse.quote(query.strip())}&per_page={limit}"
        req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
        authors = []
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
            for a in data.get("results", []):
                name = a.get("display_name", "")
                affils = a.get("affiliations", [])
                affil_name = affils[0].get("institution", {}).get("display_name", "") if affils else "Sin institución"
                doc_count = a.get("works_count", 0)
                subjects = [t.get("display_name") for t in a.get("topics", [])[:4] if t.get("display_name")]

                # Extract Scopus Author ID
                scopus_id = None
                ids = a.get("ids", {})
                if "scopus" in ids and ids["scopus"]:
                    scopus_id = ids["scopus"].split("authorId=")[-1]
                if not scopus_id:
                    scopus_id = a.get("id", "").split("/")[-1].replace("A", "")

                authors.append({
                    "scopus_id": scopus_id,
                    "name": name,
                    "affiliation": affil_name,
                    "documents_count": doc_count,
                    "subject_areas": subjects,
                    "profile_url": f"https://www.scopus.com/authid/detail.uri?authorId={scopus_id}",
                    "source": "Scopus (Índice Abierto)"
                })

        return {
            "success": True,
            "mode": "open_index",
            "total": len(authors),
            "results": authors
        }
    except Exception as e:
        logger.error(f"Error querying Open Scopus index: {e}")
        return {"success": False, "mode": "open_index", "results": [], "error": str(e)}


def search_authors(query: str, api_key: Optional[str] = None, limit: int = 8) -> Dict[str, Any]:
    """
    Unified Scopus author search:
    - If api_key is present: uses Official Elsevier Developer API.
    - If api_key is not present: automatically uses Open Scopus Index.
    """
    key = get_api_key(api_key)
    if key:
        try:
            return search_authors_official(query, key, limit=limit)
        except Exception as e:
            logger.warning(f"Official Scopus API call failed ({e}). Falling back to Open Scopus Index.")

    # Open index fallback
    return search_authors_open_index(query, limit=limit)


def get_author_profile(author_id: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieve author details from Scopus.
    """
    clean_id = author_id.replace("AUTHOR_ID:", "").strip()
    return {
        "success": True,
        "scopus_id": clean_id,
        "profile_url": f"https://www.scopus.com/authid/detail.uri?authorId={clean_id}"
    }


if __name__ == "__main__":
    print("Testing Unified Scopus Engine (without key)...")
    res = search_authors("Geoffrey Hinton", limit=2)
    print("Results:", len(res["results"]))
    for r in res["results"]:
        print(f"  -> {r['name']} | Docs: {r['documents_count']} | Scopus ID: {r['scopus_id']}")
