"""Business logic for NPI search tool."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

os.environ.setdefault("PGEOCODE_DATA_DIR", "/tmp/pgeocode-cache")

import pgeocode

from .client import NPIRegistryError, query_registry

NOMINATIM = pgeocode.Nominatim("us")

TAXONOMY_CATALOG: List[Dict[str, str]] = [
    {"code": "207RC0000X", "description": "Cardiovascular Disease (Cardiology)"},
    {"code": "207RE0101X", "description": "Interventional Cardiology"},
    {"code": "207RI0008X", "description": "Clinical Cardiac Electrophysiology"},
    {"code": "207Q00000X", "description": "Family Medicine"},
    {"code": "207R00000X", "description": "Internal Medicine"},
    {"code": "207RG0100X", "description": "Gastroenterology"},
    {"code": "207RN0300X", "description": "Nephrology"},
    {"code": "207RH0003X", "description": "Hematology & Oncology"},
    {"code": "207RS0010X", "description": "Sleep Medicine"},
    {"code": "2080P0201X", "description": "Pediatric Cardiology"},
    {"code": "2084N0400X", "description": "Neurology"},
    {"code": "2085R0202X", "description": "Reproductive Endocrinology"},
    {"code": "1223G0001X", "description": "General Practice Dentistry"},
    {"code": "163WP0218X", "description": "Pediatric Nurse Practitioner"},
    {"code": "363LF0000X", "description": "Family Nurse Practitioner"},
    {"code": "364SX0204X", "description": "Surgical Physician Assistant"},
    {"code": "385H0001X", "description": "Advance Practice Midwife"},
    {"code": "261QP2300X", "description": "Multi-Specialty Clinic/Group"},
    {"code": "251E00000X", "description": "Home Health Agency"},
    {"code": "332BX2000X", "description": "Durable Medical Equipment Supplier"},
]


def _normalize_address(entry: Dict[str, Any]) -> Dict[str, Any]:
    addresses: List[Dict[str, Any]] = entry.get("addresses") or []
    location = next((addr for addr in addresses if addr.get("address_purpose") == "LOCATION"), addresses[0] if addresses else {})
    return {
        "address_1": location.get("address_1"),
        "address_2": location.get("address_2"),
        "city": location.get("city"),
        "state": location.get("state"),
        "postal_code": location.get("postal_code"),
        "telephone_number": location.get("telephone_number"),
    }


def _normalize_taxonomies(entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    taxonomies: List[Dict[str, Any]] = entry.get("taxonomies") or []
    normalized: List[Dict[str, Any]] = []
    for tax in taxonomies:
        normalized.append(
            {
                "code": tax.get("code"),
                "description": tax.get("desc"),
                "state": tax.get("state"),
                "license": tax.get("license"),
                "primary": bool(tax.get("primary")),
            }
        )
    return normalized


def _normalize_basic(entry: Dict[str, Any]) -> Dict[str, Any]:
    basic = entry.get("basic") or {}
    return {
        "first_name": basic.get("first_name"),
        "last_name": basic.get("last_name"),
        "credential": basic.get("credential"),
        "sole_proprietor": basic.get("sole_proprietor"),
        "gender": basic.get("gender"),
        "enumeration_date": basic.get("enumeration_date"),
        "last_updated": basic.get("last_updated"),
    }


def search_npi(
    *,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    organization_name: Optional[str] = None,
    npi: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    postal_code: Optional[str] = None,
    specialty: Optional[str] = None,
    limit: Optional[int] = None,
    require_license: Optional[bool] = None,
    license_state: Optional[str] = None,
    sole_proprietor: Optional[bool] = None,
    gender: Optional[str] = None,
) -> Dict[str, Any]:
    """Search the registry and return normalized results."""

    params: Dict[str, Any] = {
        "first_name": first_name,
        "last_name": last_name,
        "organization_name": organization_name,
        "number": npi,
        "city": city,
        "state": state,
        "postal_code": postal_code,
        "taxonomy_description": specialty,
        "limit": limit,
    }

    data = query_registry(params)
    results = data.get("results") or []
    normalized: List[Dict[str, Any]] = []
    for entry in results:
        normalized.append(
            {
                "npi": entry.get("number"),
                "enumeration_type": entry.get("enumeration_type"),
                "basic": _normalize_basic(entry),
                "address": _normalize_address(entry),
                "taxonomies": _normalize_taxonomies(entry),
            }
        )

    filtered = _filter_providers(
        normalized,
        require_license=require_license,
        license_state=license_state,
        sole_proprietor=sole_proprietor,
        gender=gender,
        specialty=params.get("taxonomy_description"),
    )

    summary = {
        "result_count": len(filtered),
        "raw_result_count": data.get("result_count"),
        "last_updated": data.get("last_updated"),
    }

    return {"summary": summary, "providers": filtered}


def _filter_providers(
    providers: List[Dict[str, Any]],
    *,
    require_license: Optional[bool],
    license_state: Optional[str],
    sole_proprietor: Optional[bool],
    gender: Optional[str],
    specialty: Optional[str],
) -> List[Dict[str, Any]]:
    if not providers:
        return providers

    def matches(provider: Dict[str, Any]) -> bool:
        basic = provider.get("basic") or {}
        taxonomies = provider.get("taxonomies") or []
        if sole_proprietor is not None:
            value = (basic.get("sole_proprietor") or "").lower()
            if sole_proprietor and value != "yes":
                return False
            if sole_proprietor is False and value == "yes":
                return False
        if gender and (basic.get("gender") or "").lower() != gender.lower():
            return False
        if specialty:
            if not any(_taxonomy_matches(tax, specialty) for tax in taxonomies):
                return False
        if require_license:
            if not any((tax.get("license") or "").strip() for tax in taxonomies):
                return False
        if license_state:
            if not any((tax.get("state") or "").lower() == license_state.lower() for tax in taxonomies):
                return False
        return True

    return [prov for prov in providers if matches(prov)]


def _filter_by_specialty(
    providers: List[Dict[str, Any]], specialty: Optional[str]
) -> List[Dict[str, Any]]:
    if not specialty:
        return providers
    needle = specialty.strip().lower()
    filtered: List[Dict[str, Any]] = []
    for provider in providers:
        taxonomies = provider.get("taxonomies") or []
        for tax in taxonomies:
            description = (tax.get("description") or "").lower()
            code = (tax.get("code") or "").lower()
            if needle in description or needle == code:
                filtered.append(provider)
                break
    return filtered


def search_org_investigators(
    *,
    organization_name: str,
    specialty: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Search for individual providers associated with an organization."""

    data = search_npi(
        organization_name=organization_name,
        city=city,
        state=state,
        specialty=specialty,
        limit=limit,
    )
    providers = data.get("providers", [])
    filtered = _filter_by_specialty(providers, specialty)
    summary = {
        **(data.get("summary") or {}),
        "organization": organization_name,
        "requested_specialty": specialty,
        "matched_count": len(filtered),
    }
    return {"organization": organization_name, "providers": filtered, "summary": summary}


def organization_roster_snapshot(
    *,
    organization_name: str,
    specialty: Optional[str] = None,
    state: Optional[str] = None,
    city: Optional[str] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Provide a lightweight roster summary for an organization."""

    data = search_org_investigators(
        organization_name=organization_name,
        specialty=specialty,
        city=city,
        state=state,
        limit=limit,
    )
    providers = data.get("providers", [])
    roster = [
        {
            "npi": prov.get("npi"),
            "name": f"{(prov.get('basic') or {}).get('first_name','')} {(prov.get('basic') or {}).get('last_name','')}".strip(),
            "primary_taxonomy": next((tax.get("description") for tax in prov.get("taxonomies", []) if tax.get("primary")), None),
            "city": (prov.get("address") or {}).get("city"),
            "state": (prov.get("address") or {}).get("state"),
        }
        for prov in providers
    ]
    summary = {
        "organization": organization_name,
        "count": len(roster),
        "specialty": specialty,
        "state": state,
        "city": city,
    }
    return {"summary": summary, "roster": roster}


def autocomplete_taxonomy(query: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
    """Return taxonomy codes/descriptions matching the query."""

    if not query:
        matches = TAXONOMY_CATALOG[:limit]
    else:
        needle = query.lower()
        matches = [
            entry
            for entry in TAXONOMY_CATALOG
            if needle in entry["description"].lower() or needle in entry["code"].lower()
        ]
        matches = matches[:limit]
    return {"query": query, "matches": matches, "count": len(matches)}


def verify_npi_batch(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate NPIs or investigator names in batch form."""

    verified: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    for entry in entries:
        npi = str(entry.get("npi") or "").strip()
        if not npi:
            failures.append({**entry, "error": "Missing NPI"})
            continue
        try:
            result = search_npi(
                npi=npi,
                first_name=entry.get("first_name"),
                last_name=entry.get("last_name"),
                limit=1,
            )
        except NPIRegistryError as exc:
            failures.append({**entry, "error": str(exc)})
            continue
        providers = result.get("providers", [])
        if not providers:
            failures.append({**entry, "error": "Not found"})
            continue
        provider = providers[0]
        verified.append(
            {
                "input": entry,
                "provider": provider,
            }
        )
    summary = {"verified": len(verified), "failed": len(failures), "total": len(entries)}
    return {"summary": summary, "verified": verified, "failed": failures}


def nearby_providers(
    *,
    postal_code: str,
    specialty: Optional[str] = None,
    radius_miles: float = 50,
    limit: int = 20,
) -> Dict[str, Any]:
    """Find providers within a radius of a ZIP code."""

    base = search_npi(postal_code=postal_code, specialty=specialty, limit=max(limit * 3, 20))
    providers = []
    for provider in base.get("providers", []):
        provider_zip = ((provider.get("address") or {}).get("postal_code") or "").split("-")[0]
        distance = _zip_distance(postal_code, provider_zip)
        if distance is None:
            continue
        if distance <= radius_miles:
            provider_with_distance = dict(provider)
            provider_with_distance["distance_miles"] = round(distance, 1)
            providers.append(provider_with_distance)
    providers.sort(key=lambda item: item.get("distance_miles", 9999))
    providers = providers[:limit]
    summary = {
        "postal_code": postal_code,
        "specialty": specialty,
        "radius_miles": radius_miles,
        "count": len(providers),
    }
    return {"summary": summary, "providers": providers}


def _zip_distance(zip_a: str | None, zip_b: str | None) -> Optional[float]:
    if not zip_a or not zip_b:
        return None
    info_a = NOMINATIM.query_postal_code(zip_a)
    info_b = NOMINATIM.query_postal_code(zip_b)
    if info_a is None or info_b is None:
        return None
    if info_a.latitude is None or info_b.latitude is None:
        return None
    return float(
        ((info_a.latitude - info_b.latitude) ** 2 + (info_a.longitude - info_b.longitude) ** 2)
        ** 0.5
        * 69.0
    )


def _taxonomy_matches(taxonomy: Dict[str, Any], needle: str) -> bool:
    if not needle:
        return True
    description = (taxonomy.get("description") or "").lower()
    code = (taxonomy.get("code") or "").lower()
    needle = needle.lower()
    return needle in description or needle == code
