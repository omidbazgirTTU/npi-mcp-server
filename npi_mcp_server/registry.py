"""Business logic for NPI search tool."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .client import NPIRegistryError, query_registry


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

    summary = {
        "result_count": len(normalized),
        "raw_result_count": data.get("result_count"),
        "last_updated": data.get("last_updated"),
    }

    return {"summary": summary, "providers": normalized}
