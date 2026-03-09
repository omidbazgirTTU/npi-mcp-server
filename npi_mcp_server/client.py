"""HTTP client for the CMS NPI Registry API."""

from __future__ import annotations

from typing import Any, Dict

import httpx

API_URL = "https://npiregistry.cms.hhs.gov/api/"
DEFAULT_VERSION = "2.1"
MAX_LIMIT = 200


class NPIRegistryError(RuntimeError):
    """Raised when the CMS registry returns an error payload."""


def _build_payload(params: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"version": DEFAULT_VERSION, "enumeration_type": "NPI-1"}
    payload.update({k: v for k, v in params.items() if v is not None})
    return payload


def query_registry(params: Dict[str, Any]) -> Dict[str, Any]:
    """Call the CMS API and return the JSON payload."""

    limit = params.get("limit")
    if limit is not None:
        limit = max(1, min(int(limit), MAX_LIMIT))
    else:
        limit = 10

    payload = _build_payload({**params, "limit": limit})

    with httpx.Client(timeout=20) as client:
        response = client.get(API_URL, params=payload)
    response.raise_for_status()
    data = response.json()
    if data.get("errors"):
        raise NPIRegistryError("; ".join(err.get("description", "Unknown error") for err in data["errors"]))
    return data
