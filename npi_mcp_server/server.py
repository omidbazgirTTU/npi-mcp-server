"""FastMCP server exposing CMS NPI registry search."""

from __future__ import annotations

import argparse
import logging
from typing import Any

from fastmcp import FastMCP

from .registry import (
    NPIRegistryError,
    autocomplete_taxonomy,
    nearby_providers,
    organization_roster_snapshot,
    search_npi,
    search_org_investigators,
    verify_npi_batch,
)
from .ui import WIDGET_URIS, register_widgets

server = FastMCP("npi-mcp-server")
register_widgets(server)


@server.tool(description="Search the CMS NPI Registry by taxonomy, geography, and identifiers.")
def search_npi_registry(
    first_name: str | None = None,
    last_name: str | None = None,
    organization_name: str | None = None,
    npi: str | None = None,
    city: str | None = None,
    state: str | None = None,
    postal_code: str | None = None,
    specialty: str | None = None,
    limit: int | None = 10,
    require_license: bool | None = None,
    license_state: str | None = None,
    sole_proprietor: bool | None = None,
    gender: str | None = None,
) -> dict[str, Any]:
    try:
        result = search_npi(
            first_name=first_name,
            last_name=last_name,
            organization_name=organization_name,
            npi=npi,
            city=city,
            state=state,
            postal_code=postal_code,
            specialty=specialty,
            limit=limit,
            require_license=require_license,
            license_state=license_state,
            sole_proprietor=sole_proprietor,
            gender=gender,
        )
    except NPIRegistryError as exc:
        raise ValueError(str(exc)) from exc
    result["ui"] = {
        "widgetUri": WIDGET_URIS.get("provider_results"),
        "data": {"providers": result.get("providers", []), "summary": result.get("summary", {})},
    }
    return result


@server.tool(
    description=(
        "List principal investigators (individual NPIs) within an organization, "
        "optionally filtered by taxonomy/specialty and geography."
    )
)
def list_org_investigators(
    organization_name: str,
    specialty: str | None = None,
    city: str | None = None,
    state: str | None = None,
    limit: int | None = 25,
) -> dict[str, Any]:
    try:
        result = search_org_investigators(
            organization_name=organization_name,
            specialty=specialty,
            city=city,
            state=state,
            limit=limit,
        )
    except NPIRegistryError as exc:
        raise ValueError(str(exc)) from exc
    roster = [
        {
            "npi": prov.get("npi"),
            "name": " ".join(filter(None, [(prov.get("basic") or {}).get("first_name"), (prov.get("basic") or {}).get("last_name")])),
            "primary_taxonomy": next(
                (tax.get("description") for tax in prov.get("taxonomies", []) if tax.get("primary")), None
            ),
            "city": (prov.get("address") or {}).get("city"),
            "state": (prov.get("address") or {}).get("state"),
        }
        for prov in result.get("providers", [])
    ]
    result["roster"] = roster
    result["ui"] = {
        "widgetUri": WIDGET_URIS.get("org_roster"),
        "data": {"roster": roster, "summary": result.get("summary", {})},
    }
    return result


@server.tool(description="Autocomplete provider taxonomy codes/descriptions.")
def autocomplete_provider_taxonomy(query: str | None = None, limit: int = 20) -> dict[str, Any]:
    result = autocomplete_taxonomy(query=query, limit=limit)
    result["ui"] = {
        "widgetUri": WIDGET_URIS.get("taxonomy_autocomplete"),
        "data": result,
    }
    return result


@server.tool(description="Verify a batch of NPIs or investigator identities.")
def verify_npi_roster(entries: list[dict[str, Any]]) -> dict[str, Any]:
    result = verify_npi_batch(entries)
    result["ui"] = {
        "widgetUri": WIDGET_URIS.get("verification_results"),
        "data": result,
    }
    return result


@server.tool(description="Generate an organization roster snapshot grouped by specialty/state.")
def get_org_roster_snapshot(
    organization_name: str,
    specialty: str | None = None,
    state: str | None = None,
    city: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    result = organization_roster_snapshot(
        organization_name=organization_name,
        specialty=specialty,
        state=state,
        city=city,
        limit=limit,
    )
    result["ui"] = {
        "widgetUri": WIDGET_URIS.get("org_roster"),
        "data": result,
    }
    return result


@server.tool(description="Rank providers near a ZIP code by distance.")
def find_nearby_providers(
    postal_code: str,
    specialty: str | None = None,
    radius_miles: float = 50,
    limit: int = 20,
) -> dict[str, Any]:
    result = nearby_providers(
        postal_code=postal_code,
        specialty=specialty,
        radius_miles=radius_miles,
        limit=limit,
    )
    result["ui"] = {
        "widgetUri": WIDGET_URIS.get("nearby_providers"),
        "data": result,
    }
    return result


def run_http(host: str, port: int) -> None:
    server.run(transport="http", host=host, port=port)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the NPI MCP server.")
    parser.add_argument("--transport", default="http", help="Transport to use (http, stdio).")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP host")
    parser.add_argument("--port", type=int, default=8001, help="HTTP port")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.transport == "http":
        run_http(args.host, args.port)
    else:
        server.run(transport=args.transport)


def get_asgi_app():
    app = server.http_app()

    async def wrapped(scope, receive, send):
        if scope.get("type") in {"http", "websocket"}:
            path = scope.get("path", "")
            if path.startswith("/api/mcp.py"):
                new_scope = dict(scope)
                suffix = path[len("/api/mcp.py") :]
                new_scope["path"] = "/mcp" + suffix
                new_scope.setdefault("root_path", "")
                scope = new_scope
            elif path.startswith("/api/mcp"):
                new_scope = dict(scope)
                suffix = path[len("/api/mcp") :]
                new_scope["path"] = "/mcp" + suffix
                new_scope.setdefault("root_path", "")
                scope = new_scope
        await app(scope, receive, send)

    return wrapped


if __name__ == "__main__":
    main()
