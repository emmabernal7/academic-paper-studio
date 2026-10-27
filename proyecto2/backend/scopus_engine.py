#!/usr/bin/env python3
"""
Scopus Engine - Client for Elsevier Scopus Search and Author Retrieval API.
Based on the architecture and parameters of Christopher Belter's scopusAPI (R/Python).
Provides Scopus Author ID search, indexed documents count, h-index, and author profile details.
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
DEFAULT_USER_AGENT = "AcademicPaperStudio/2.0"


def get_api_key(provided_key: Optional[str] = None) -> Optional[str]:
    """Retrieve API key from argument or environment variable."""
    return provided_key or os.environ.get("SCOPUS_API_KEY") or os.environ.get("ELSEVIER_API_KEY")


def search_authors(query: str, api_key: Optional[str] = None, limit: int = 8) -> Dict[str, Any]:
    """
    Search Scopus for authors matching a name or affiliation.
    Follows Christopher Belter's scopusAPI query structure:
    `authlast(LastName) and authfirst(FirstName)` or general author search.
    """
    key = get_api_key(api_key)
    if not key:
        return {
            "success": False,
            "error": "Clave API de Scopus requerida. Puedes obtener una gratuita en dev.elsevier.com o ingresar tu clave en la configuración.",
            "requires_key": True,
            "results": []
        }

    cleaned = query.strip()
    parts = cleaned.split()
    if len(parts) >= 2:
        scopus_query = f"authlast({parts[-1]}) and authfirst({parts[0]})"
    else:
        scopus_query = f"authlast({cleaned})"

    params = {
        "query": scopus_query,
        "count": limit
    }
    encoded_params = urllib.parse.urlencode(params)
    url = f"{SCOPUS_SEARCH_URL}?{encoded_params}"

    req = urllib.request.Request(
        url,
        headers={
            "X-ELS-APIKey": key,
            "Accept": "application/json",
            "User-Agent": DEFAULT_USER_AGENT
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                search_results = data.get("search-results", {})
                entries = search_results.get("entry", [])
                
                authors = []
                for entry in entries:
                    # Ignore error stubs
                    if "error" in entry:
                        continue

                    raw_id = entry.get("dc:identifier", "")
                    author_id = raw_id.replace("AUTHOR_ID:", "")

                    # Preferred name
                    pref_name = entry.get("preferred-name", {})
                    given = pref_name.get("given-name", "")
                    surname = pref_name.get("surname", "")
                    name = f"{given} {surname}".strip() or entry.get("authname", author_id)

                    # Affiliation
                    affil = entry.get("affiliation-current", {})
                    affil_name = affil.get("affiliation-name", "Sin institución reportada")
                    city = affil.get("affiliation-city", "")
                    country = affil.get("affiliation-country", "")
                    loc = f", {city}, {country}".strip(", ") if city or country else ""
                    full_affil = f"{affil_name}{loc}" if affil_name else ""

                    # Documents count
                    doc_count = entry.get("document-count", "0")
                    try:
                        doc_count = int(doc_count)
                    except ValueError:
                        doc_count = 0

                    # Subject areas
                    subjects = []
                    raw_subj = entry.get("subject-area", [])
                    if isinstance(raw_subj, list):
                        for s in raw_subj:
                            v = s.get("$", "")
                            if v:
                                subjects.append(v)

                    authors.append({
                        "scopus_id": author_id,
                        "name": name,
                        "affiliation": full_affil,
                        "documents_count": doc_count,
                        "subject_areas": subjects,
                        "profile_url": f"https://www.scopus.com/authid/detail.uri?authorId={author_id}",
                        "source": "Scopus (Elsevier)"
                    })

                return {
                    "success": True,
                    "total": search_results.get("opensearch:totalResults", len(authors)),
                    "results": authors
                }

    except Exception as e:
        logger.error(f"Error querying Scopus API: {e}")
        return {
            "success": False,
            "error": str(e),
            "requires_key": False,
            "results": []
        }


def get_author_profile(author_id: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieve full author profile from Scopus, including h-index and citation metrics.
    """
    key = get_api_key(api_key)
    if not key:
        return {"success": False, "error": "Clave API de Scopus requerida."}

    clean_id = author_id.replace("AUTHOR_ID:", "").strip()
    url = f"{SCOPUS_AUTHOR_URL}/{clean_id}?view=ENHANCED"

    req = urllib.request.Request(
        url,
        headers={
            "X-ELS-APIKey": key,
            "Accept": "application/json",
            "User-Agent": DEFAULT_USER_AGENT
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                retrieval = data.get("author-retrieval-response", [{}])[0]
                coredata = retrieval.get("coredata", {})
                
                h_index = retrieval.get("h-index", "0")
                try:
                    h_index = int(h_index)
                except ValueError:
                    h_index = 0

                citation_count = coredata.get("citation-count", "0")
                try:
                    citation_count = int(citation_count)
                except ValueError:
                    citation_count = 0

                return {
                    "success": True,
                    "scopus_id": clean_id,
                    "h_index": h_index,
                    "citation_count": citation_count,
                    "document_count": coredata.get("document-count", 0),
                    "profile_url": f"https://www.scopus.com/authid/detail.uri?authorId={clean_id}"
                }
    except Exception as e:
        logger.error(f"Error retrieving Scopus author details: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    print("Testing Scopus Engine...")
    res = search_authors("Geoffrey Hinton")
    print("Result:", res)
