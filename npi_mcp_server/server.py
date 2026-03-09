"""FastMCP server exposing CMS NPI registry search."""

from __future__ import annotations

import argparse
import logging
from typing import Any

from fastmcp import FastMCP

from .registry import NPIRegistryError, search_npi

server = FastMCP("npi-mcp-server")


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
) -> dict[str, Any]:
    try:
        return search_npi(
            first_name=first_name,
            last_name=last_name,
            organization_name=organization_name,
            npi=npi,
            city=city,
            state=state,
            postal_code=postal_code,
            specialty=specialty,
            limit=limit,
        )
    except NPIRegistryError as exc:
        raise ValueError(str(exc)) from exc


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
