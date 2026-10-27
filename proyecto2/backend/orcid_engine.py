#!/usr/bin/env python3
"""
ORCID Engine - Client for ORCID Public API v3.0 (pub.orcid.org).
Provides free, open researcher lookup, verified ORCID iD profiles, institutions, and works catalog with DOIs.
Does NOT require an API key or paid credentials.
"""

import urllib.request
import urllib.parse
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("orcid_engine")
logging.basicConfig(level=logging.INFO)

ORCID_BASE_URL = "https://pub.orcid.org/v3.0"
DEFAULT_USER_AGENT = "AcademicPaperStudio/2.0 (mailto:academic.studio@local)"


def _request_orcid_json(endpoint: str, params: Optional[Dict[str, Any]] = None, timeout: int = 12) -> Optional[Dict[str, Any]]:
    """Helper to perform GET request to ORCID Public API with proper headers."""
    url = f"{ORCID_BASE_URL}/{endpoint.lstrip('/')}"
    if params:
        query_str = urllib.parse.urlencode(params)
        url = f"{url}?{query_str}"

    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": DEFAULT_USER_AGENT
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.error(f"Error querying ORCID endpoint '{endpoint}': {e}")
    return None


def search_researchers(query: str, rows: int = 10) -> List[Dict[str, Any]]:
    """
    Search ORCID public registry for researchers matching query.
    Query can be a person's name (e.g. 'Yoshua Bengio'), an ORCID iD, or an institution.
    """
    cleaned_query = query.strip()
    if not cleaned_query:
        return []

    # If query is formatted like an ORCID ID (0000-0000-0000-0000)
    import re
    if re.match(r'^\d{4}-\d{4}-\d{4}-[\dX]{4}$', cleaned_query):
        rec = get_researcher_record(cleaned_query)
        return [rec] if rec.get("orcid_id") else []

    # Format text search or split first/last name
    parts = cleaned_query.split()
    if len(parts) >= 2:
        lucene_query = f"given-names:{parts[0]}* AND family-name:{parts[-1]}*"
    else:
        lucene_query = f"text:{cleaned_query}*"

    data = _request_orcid_json("expanded-search", {"q": lucene_query, "rows": rows})
    if not data:
        # Fallback to direct text search
        data = _request_orcid_json("expanded-search", {"q": f"text:{cleaned_query}", "rows": rows})

    if not data:
        return []

    results = []
    items = data.get("expanded-result", [])
    for it in items:
        orcid_id = it.get("orcid-id", "")
        given = it.get("given-names", "")
        family = it.get("family-names", "")
        full_name = f"{given} {family}".strip() or it.get("credit-name", "") or orcid_id

        institutions = it.get("institution-name", [])
        if isinstance(institutions, str):
            institutions = [institutions]

        results.append({
            "orcid_id": orcid_id,
            "name": full_name,
            "given_names": given,
            "family_names": family,
            "institutions": institutions,
            "affiliation": institutions[0] if institutions else "Sin afiliación pública",
            "profile_url": f"https://orcid.org/{orcid_id}",
            "source": "ORCID"
        })

    return results


def get_researcher_record(orcid_id: str) -> Dict[str, Any]:
    """
    Retrieve public biographical and employment details for an ORCID iD.
    """
    clean_id = orcid_id.strip()
    data = _request_orcid_json(f"{clean_id}/record")
    if not data:
        return {}

    person = data.get("person", {})
    activities = data.get("activities-summary", {})

    # Names
    name_obj = person.get("name", {})
    given = name_obj.get("given-names", {}).get("value", "") if name_obj.get("given-names") else ""
    family = name_obj.get("family-name", {}).get("value", "") if name_obj.get("family-name") else ""
    credit = name_obj.get("credit-name", {}).get("value", "") if name_obj.get("credit-name") else ""
    full_name = credit or f"{given} {family}".strip() or clean_id

    # Biography
    bio_obj = person.get("biography", {})
    bio = bio_obj.get("content", "") if bio_obj else ""

    # Affiliations (Employment & Education)
    affiliations = []
    employments = activities.get("employments", {}).get("affiliation-group", [])
    for eg in employments:
        for sum_item in eg.get("summaries", []):
            emp = sum_item.get("employment-summary", {})
            org = emp.get("organization", {}).get("name", "")
            role = emp.get("role-title", "")
            if org:
                affiliations.append(f"{role} en {org}" if role else org)

    # Keywords / research areas
    keywords = []
    for kw in person.get("keywords", {}).get("keyword", []):
        v = kw.get("content")
        if v:
            keywords.append(v)

    # External identifiers (Scopus Author ID, ResearcherID, etc.)
    external_identifiers = []
    for ext in person.get("external-identifiers", {}).get("external-identifier", []):
        t = ext.get("external-id-type")
        v = ext.get("external-id-value")
        u = ext.get("external-id-url", {}).get("value") if ext.get("external-id-url") else None
        if t and v:
            external_identifiers.append({"type": t, "value": v, "url": u})

    works_count = len(activities.get("works", {}).get("group", []))

    return {
        "orcid_id": clean_id,
        "name": full_name,
        "biography": bio,
        "affiliations": affiliations,
        "primary_affiliation": affiliations[0] if affiliations else "",
        "keywords": keywords,
        "external_identifiers": external_identifiers,
        "works_count": works_count,
        "profile_url": f"https://orcid.org/{clean_id}",
        "source": "ORCID"
    }


def get_researcher_works(orcid_id: str, limit: int = 30) -> List[Dict[str, Any]]:
    """
    Retrieve publications list for an ORCID iD, extracting Titles, DOIs, Years, and Journals.
    """
    clean_id = orcid_id.strip()
    data = _request_orcid_json(f"{clean_id}/works")
    if not data:
        return []

    works = []
    groups = data.get("group", [])
    for grp in groups[:limit]:
        summaries = grp.get("work-summary", [])
        if not summaries:
            continue
        ws = summaries[0]

        # Title
        title_obj = ws.get("title", {}).get("title", {})
        title = title_obj.get("value", "Sin título") if title_obj else "Sin título"

        # Year
        pub_date = ws.get("publication-date") or {}
        year = pub_date.get("year", {}).get("value", "") if pub_date.get("year") else ""

        # Journal / Journal Title
        journal_obj = ws.get("journal-title") or {}
        journal = journal_obj.get("value", "") if isinstance(journal_obj, dict) else ""

        # Type (journal-article, book, etc.)
        work_type = ws.get("type", "work")

        # External IDs (DOIs, etc.)
        doi = None
        ext_ids = ws.get("external-ids", {}).get("external-id", [])
        for eid in ext_ids:
            if eid.get("external-id-type", "").lower() == "doi":
                doi = eid.get("external-id-value")
                break

        url = ws.get("url", {}).get("value") if ws.get("url") else None
        if not url and doi:
            url = f"https://doi.org/{doi}"

        works.append({
            "title": title,
            "year": year,
            "journal": journal,
            "type": work_type,
            "doi": doi,
            "url": url,
            "source": "ORCID"
        })

    return works


if __name__ == "__main__":
    print("Testing ORCID Engine...")
    print("1. Searching for 'Yoshua Bengio'...")
    res = search_researchers("Yoshua Bengio", rows=2)
    for r in res:
        print(f"  -> {r['name']} ({r['orcid_id']}) - {r['affiliation']}")

    if res:
        oid = res[0]['orcid_id']
        print(f"\n2. Fetching works for {oid}...")
        wks = get_researcher_works(oid, limit=3)
        for w in wks:
            print(f"  -> [{w['year']}] {w['title'][:50]}... (DOI: {w['doi']})")
