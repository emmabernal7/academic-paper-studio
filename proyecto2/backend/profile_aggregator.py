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
    scopus_results = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_scholar = executor.submit(scholar_engine.search_authors, cleaned_query, limit=5)
        future_orcid = executor.submit(orcid_engine.search_researchers, cleaned_query, rows=6)
        future_scopus = executor.submit(scopus_engine.search_authors, cleaned_query, api_key=scopus_api_key, limit=5)

        try:
            scholar_results = future_scholar.result(timeout=15)
        except Exception as e:
            logger.error(f"Scholar search failed: {e}")

        try:
            orcid_results = future_orcid.result(timeout=15)
        except Exception as e:
            logger.error(f"ORCID search failed: {e}")

        try:
            scopus_res = future_scopus.result(timeout=15)
            scopus_results = scopus_res.get("results", [])
        except Exception as e:
            logger.error(f"Scopus search failed: {e}")

    # Synthesize unified cards
    unified_cards = []
    seen_names = set()

    # 1. Primary pass from Google Scholar (rich in citation metrics)
    for s in scholar_results:
        s_name = s.get("name", "")
        card = {
            "name": s_name,
            "scholar_id": s.get("scholar_id"),
            "scholar_url": s.get("profile_url"),
            "citations": s.get("citations", 0),
            "h_index": s.get("h_index", 0),
            "i10_index": s.get("i10_index", 0),
            "affiliation": s.get("affiliation", ""),
            "interests": s.get("interests", []),
            "photo_url": s.get("photo_url"),
            "orcid_id": None,
            "orcid_url": None,
            "scopus_id": None,
            "scopus_url": None,
            "sources": ["Google Scholar"]
        }

        s_tokens = set(s_name.lower().split())

        # Match with ORCID
        for o in orcid_results:
            o_tokens = set(o.get("name", "").lower().split())
            if len(s_tokens.intersection(o_tokens)) >= 1:
                card["orcid_id"] = o.get("orcid_id")
                card["orcid_url"] = o.get("profile_url")
                if "ORCID" not in card["sources"]:
                    card["sources"].append("ORCID")
                if not card["affiliation"] and o.get("affiliation"):
                    card["affiliation"] = o.get("affiliation")
                break

        # Match with Scopus
        for sc in scopus_results:
            sc_tokens = set(sc.get("name", "").lower().split())
            if len(s_tokens.intersection(sc_tokens)) >= 1:
                card["scopus_id"] = sc.get("scopus_id")
                card["scopus_url"] = sc.get("profile_url")
                if "Scopus" not in card["sources"]:
                    card["sources"].append("Scopus")
                break

        unified_cards.append(card)
        seen_names.add(s_name.lower())

    # 2. Add ORCID records not matched
    matched_orcids = {c["orcid_id"] for c in unified_cards if c.get("orcid_id")}
    for o in orcid_results:
        oid = o.get("orcid_id")
        o_name = o.get("name", "")
        if oid not in matched_orcids and o_name.lower() not in seen_names:
            card = {
                "name": o_name,
                "scholar_id": None,
                "scholar_url": None,
                "citations": None,
                "h_index": None,
                "i10_index": None,
                "affiliation": o.get("affiliation", ""),
                "interests": [],
                "photo_url": None,
                "orcid_id": oid,
                "orcid_url": o.get("profile_url"),
                "scopus_id": None,
                "scopus_url": None,
                "sources": ["ORCID"]
            }
            # Check if any Scopus matches this ORCID
            o_tokens = set(o_name.lower().split())
            for sc in scopus_results:
                sc_tokens = set(sc.get("name", "").lower().split())
                if len(o_tokens.intersection(sc_tokens)) >= 1:
                    card["scopus_id"] = sc.get("scopus_id")
                    card["scopus_url"] = sc.get("profile_url")
                    card["sources"].append("Scopus")
                    break

            unified_cards.append(card)
            seen_names.add(o_name.lower())

    # 3. Add Scopus records not matched
    matched_scopus = {c["scopus_id"] for c in unified_cards if c.get("scopus_id")}
    for sc in scopus_results:
        scid = sc.get("scopus_id")
        sc_name = sc.get("name", "")
        if scid not in matched_scopus and sc_name.lower() not in seen_names:
            card = {
                "name": sc_name,
                "scholar_id": None,
                "scholar_url": None,
                "citations": None,
                "h_index": None,
                "i10_index": None,
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
            seen_names.add(sc_name.lower())

    return {
        "query": cleaned_query,
        "unified": unified_cards,
        "scholar": scholar_results,
        "orcid": orcid_results,
        "scopus": scopus_results,
        "scopus_status": {
            "configured": bool(scopus_api_key or scopus_engine.get_api_key()),
            "mode": "official" if bool(scopus_api_key or scopus_engine.get_api_key()) else "open_index"
        }
    }


if __name__ == "__main__":
    print("Testing Multi-Source Aggregator...")
    res = search_all_sources("Geoffrey Hinton")
    print(f"Total unified: {len(res['unified'])}")
    print(f"Scholar found: {len(res['scholar'])}")
    print(f"ORCID found: {len(res['orcid'])}")
    print(f"Scopus found: {len(res['scopus'])}")
    for p in res['unified']:
        print(f"  -> {p['name']} | Sources: {p['sources']} | ORCID: {p['orcid_id']} | Scopus: {p['scopus_id']} | Citas: {p['citations']}")
