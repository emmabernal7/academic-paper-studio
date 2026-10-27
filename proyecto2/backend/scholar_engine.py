#!/usr/bin/env python3
"""
Scholar Engine - Google Scholar search wrapper using scholarly.
Provides article discovery, citation metrics, author profiles, and publication tracking.
"""

import sys
import logging
from typing import Dict, List, Any, Optional

try:
    from scholarly import scholarly, ProxyGenerator
except ImportError:
    scholarly = None

logger = logging.getLogger("scholar_engine")
logging.basicConfig(level=logging.INFO)


def is_available() -> bool:
    """Check if scholarly is installed and functional."""
    return scholarly is not None


def search_articles(query: str, limit: int = 10, year_low: Optional[int] = None, year_high: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Search Google Scholar for publications matching query.
    Returns structured list of articles with citations, snippets, and PDF links.
    """
    if not scholarly:
        return []

    results = []
    try:
        # Build search with optional year bounds
        search_query = scholarly.search_pubs(query)
        
        count = 0
        for pub in search_query:
            if count >= limit:
                break

            bib = pub.get("bib", {})
            pub_year = bib.get("pub_year")
            
            # Filter by year if specified
            if pub_year:
                try:
                    yr = int(pub_year)
                    if year_low and yr < year_low:
                        continue
                    if year_high and yr > year_high:
                        continue
                except ValueError:
                    pass

            # Extract authors
            authors = bib.get("author", [])
            if isinstance(authors, str):
                authors = [a.strip() for a in authors.split(" and ")]

            item = {
                "id": pub.get("pub_url", "") or pub.get("author_id", [""])[0] or str(count),
                "title": bib.get("title", "Sin título"),
                "authors": authors,
                "year": bib.get("pub_year", ""),
                "venue": bib.get("venue", ""),
                "publisher": bib.get("publisher", ""),
                "abstract": bib.get("abstract", ""),
                "url": pub.get("pub_url", ""),
                "eprint_url": pub.get("eprint_url", ""),  # Direct PDF if indexed on Scholar
                "citations": pub.get("num_citations", 0),
                "cites_id": pub.get("cites_id", []),
                "url_scholarbib": pub.get("url_scholarbib", ""),
                "source": "Google Scholar"
            }
            results.append(item)
            count += 1

    except Exception as e:
        logger.error(f"Error in search_articles for '{query}': {e}")

    return results


def search_authors(name: str, limit: int = 6) -> List[Dict[str, Any]]:
    """
    Search Google Scholar for researcher profiles.
    Returns profile information: affiliation, research interests, citation metrics.
    """
    if not scholarly:
        return []

    authors = []
    try:
        search_query = scholarly.search_author(name)
        count = 0
        for author in search_query:
            if count >= limit:
                break

            scholar_id = author.get("scholar_id", "")
            
            # Construct standard Google Scholar profile photo URL if available
            photo_url = f"https://scholar.google.com/citations?view_op=view_photo&user={scholar_id}" if scholar_id else ""
            profile_url = f"https://scholar.google.com/citations?user={scholar_id}" if scholar_id else ""

            item = {
                "scholar_id": scholar_id,
                "name": author.get("name", ""),
                "affiliation": author.get("affiliation", ""),
                "email_domain": author.get("email_domain", ""),
                "interests": author.get("interests", []),
                "citations": author.get("citedby", 0),
                "photo_url": photo_url,
                "profile_url": profile_url,
                "source": "Google Scholar"
            }
            authors.append(item)
            count += 1

    except Exception as e:
        logger.error(f"Error in search_authors for '{name}': {e}")

    return authors


def get_author_details(scholar_id: str, fill_publications: bool = True) -> Dict[str, Any]:
    """
    Retrieve in-depth profile for an author by scholar_id, including h-index,
    i10-index, citation trajectory, and top publications.
    """
    if not scholarly or not scholar_id:
        return {}

    try:
        author_stub = {"scholar_id": scholar_id}
        sections = ["basics", "indices", "counts"]
        if fill_publications:
            sections.append("publications")

        filled = scholarly.fill(author_stub, sections=sections)
        
        # Parse top publications
        pubs = []
        raw_pubs = filled.get("publications", [])
        for p in raw_pubs[:25]:  # Top 25 most cited/recent
            bib = p.get("bib", {})
            pubs.append({
                "title": bib.get("title", ""),
                "year": bib.get("pub_year", ""),
                "venue": bib.get("venue", ""),
                "citations": p.get("num_citations", 0),
                "pub_url": p.get("pub_url", "")
            })

        return {
            "scholar_id": scholar_id,
            "name": filled.get("name", ""),
            "affiliation": filled.get("affiliation", ""),
            "interests": filled.get("interests", []),
            "citations_total": filled.get("citedby", 0),
            "citations_recent": filled.get("citedby5y", 0),
            "h_index": filled.get("hindex", 0),
            "h_index_recent": filled.get("hindex5y", 0),
            "i10_index": filled.get("i10index", 0),
            "i10_index_recent": filled.get("i10index5y", 0),
            "cites_per_year": filled.get("cites_per_year", {}),
            "publications": pubs,
            "profile_url": f"https://scholar.google.com/citations?user={scholar_id}"
        }
    except Exception as e:
        logger.error(f"Error in get_author_details for '{scholar_id}': {e}")
        return {}


if __name__ == "__main__":
    print("Testing Scholar Engine...")
    print("1. Searching articles for 'quantum machine learning'...")
    arts = search_articles("quantum machine learning", limit=2)
    for a in arts:
        print(f"  -> {a['title']} ({a['year']}) - Citas: {a['citations']}")

    print("2. Searching authors for 'Geoffrey Hinton'...")
    auths = search_authors("Geoffrey Hinton", limit=1)
    for au in auths:
        print(f"  -> {au['name']} | {au['affiliation']} | Citas: {au['citations']}")
