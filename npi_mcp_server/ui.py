"""Register UI widgets for the NPI MCP server."""

from __future__ import annotations

from pathlib import Path

from fastmcp import FastMCP

MIME_TYPE = "text/html;profile=mcp-app"
WIDGETS_DIR = Path(__file__).resolve().parent.parent / "widgets"

WIDGET_URIS = {
    "provider_results": "ui://npi-mcp/provider-results.html",
    "org_roster": "ui://npi-mcp/org-roster.html",
    "taxonomy_autocomplete": "ui://npi-mcp/taxonomy-autocomplete.html",
    "verification_results": "ui://npi-mcp/verification-results.html",
    "nearby_providers": "ui://npi-mcp/nearby-providers.html",
}


def register_widgets(mcp: FastMCP) -> None:
    for key, uri in WIDGET_URIS.items():
        html_file = WIDGETS_DIR / f"{key.replace('-', '_')}.html"
        if not html_file.exists():
            # allow hyphen names if file stored with hyphen
            html_file = WIDGETS_DIR / f"{key}.html"
        if not html_file.exists():
            continue
        _register_widget(mcp, key, uri, html_file)


def _register_widget(mcp: FastMCP, name: str, uri: str, path: Path) -> None:
    @mcp.resource(
        uri,
        name=name.replace("_", " ").title(),
        description=f"UI widget for {name.replace('_', ' ')}",
        mime_type=MIME_TYPE,
    )
    def _read_widget() -> str:  # noqa: ANN001 - FastMCP signature requirements
        return path.read_text(encoding="utf-8")
