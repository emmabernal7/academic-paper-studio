#!/usr/bin/env python3
"""
Profile Aggregator - Combines researcher profiles from Google Scholar, ORCID, and Scopus.
Provides multi-source querying, metric cross-referencing, and unified researcher cards.
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Optional

from . import scholar_engine
from . import orcid_engine
from . import scopus_engine

logger = logging.getLogger("profile_aggregator")
logging.basicConfig(level=logging.INFO)


def search_all_sources(query: str, scopus_api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Search simultaneously across Google Scholar, ORCID, and Scopus using ThreadPoolExecutor.
    Returns consolidated multi-source results for the researcher.
    """
    cleaned_query = query.strip()
    if not cleaned_query:
        return {"scholar": [], "orcid": [], "scopus": [], "unified": []}

    scholar_results = []
    orcid_results = []
    scopus_response = {"results": [], "requires_key": True}

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_scholar = executor.submit(scholar_engine.search_authors, cleaned_query, limit=5)
        future_orcid = executor.submit(orcid_engine.search_researchers, cleaned_query, rows=6)
        future_scopus = executor.submit(scopus_engine.search_authors, cleaned_query, api_key=scopus_api_key, limit=5)

        try:
            scholar_results = future_scholar.result(timeout=10)
        except Exception as e:
            logger.error(f"Scholar search failed: {e}")

        try:
            orcid_results = future_orcid.result(timeout=10)
        except Exception as e:
            logger.error(f"ORCID search failed: {e}")

        try:
            scopus_response = future_scopus.result(timeout=10)
        except Exception as e:
            logger.error(f"Scopus search failed: {e}")

    scopus_results = scopus_response.get("results", [])

    # Synthesize unified cards
    unified_cards = []

    # 1. Primary pass from Google Scholar (rich in citation metrics)
    for s in scholar_results:
        card = {
            "name": s.get("name"),
            "scholar_id": s.get("scholar_id"),
            "scholar_url": s.get("profile_url"),
            "citations": s.get("citations", 0),
            "affiliation": s.get("affiliation", ""),
            "interests": s.get("interests", []),
            "photo_url": s.get("photo_url"),
            "orcid_id": None,
            "orcid_url": None,
            "scopus_id": None,
            "scopus_url": None,
            "sources": ["Google Scholar"]
        }

        # Match with ORCID by name tokens if possible
        s_tokens = set(s.get("name", "").lower().split())
        for o in orcid_results:
            o_tokens = set(o.get("name", "").lower().split())
            if len(s_tokens.intersection(o_tokens)) >= 2:
                card["orcid_id"] = o.get("orcid_id")
                card["orcid_url"] = o.get("profile_url")
                if "ORCID" not in card["sources"]:
                    card["sources"].append("ORCID")
                if not card["affiliation"] and o.get("affiliation"):
                    card["affiliation"] = o.get("affiliation")
                break

        # Match with Scopus by surname / tokens
        for sc in scopus_results:
            sc_tokens = set(sc.get("name", "").lower().split())
            if len(s_tokens.intersection(sc_tokens)) >= 2:
                card["scopus_id"] = sc.get("scopus_id")
                card["scopus_url"] = sc.get("profile_url")
                if "Scopus" not in card["sources"]:
                    card["sources"].append("Scopus")
                break

        unified_cards.append(card)

    # 2. Add remaining ORCID records not matched
    matched_orcids = {c["orcid_id"] for c in unified_cards if c.get("orcid_id")}
    for o in orcid_results:
        oid = o.get("orcid_id")
        if oid not in matched_orcids:
            card = {
                "name": o.get("name"),
                "scholar_id": None,
                "scholar_url": None,
                "citations": None,
                "affiliation": o.get("affiliation", ""),
                "interests": [],
                "photo_url": None,
                "orcid_id": oid,
                "orcid_url": o.get("profile_url"),
                "scopus_id": None,
                "scopus_url": None,
                "sources": ["ORCID"]
            }
            unified_cards.append(card)

    # 3. Add remaining Scopus records not matched
    matched_scopus = {c["scopus_id"] for c in unified_cards if c.get("scopus_id")}
    for sc in scopus_results:
        scid = sc.get("scopus_id")
        if scid not in matched_scopus:
            card = {
                "name": sc.get("name"),
                "scholar_id": None,
                "scholar_url": None,
                "citations": None,
                "affiliation": sc.get("affiliation", ""),
                "interests": sc.get("subject_areas", []),
                "photo_url": None,
                "orcid_id": None,
                "orcid_url": None,
                "scopus_id": scid,
                "scopus_url": sc.get("profile_url"),
                "sources": ["Scopus"]
            }
            unified_cards.append(card)

    return {
        "query": cleaned_query,
        "unified": unified_cards,
        "scholar": scholar_results,
        "orcid": orcid_results,
        "scopus": scopus_results,
        "scopus_status": {
            "configured": bool(scopus_api_key or scopus_engine.get_api_key()),
            "message": scopus_response.get("error") if not scopus_response.get("success") else "OK"
        }
    }


if __name__ == "__main__":
    print("Testing Profile Aggregator...")
    res = search_all_sources("Geoffrey Hinton")
    print(f"Total unified profiles found: {len(res['unified'])}")
    for p in res['unified']:
        print(f"  -> {p['name']} | Sources: {p['sources']} | ORCID: {p['orcid_id']} | Scholar: {p['scholar_id']}")
