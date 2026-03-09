# NPI MCP Server

FastMCP wrapper around the CMS NPI Registry (https://npiregistry.cms.hhs.gov/). The server exposes a
single tool `search_npi_registry` that lets downstream agents query individual providers by
name/organization/taxonomy and geographic filters (city, state, postal code) before validating NPIs.

## Local setup

```bash
cd npi-mcp-server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m npi_mcp_server.server --transport http --host 127.0.0.1 --port 8010
```

Then connect MCP Inspector:

```bash
npx @modelcontextprotocol/inspector --http http://127.0.0.1:8010/mcp
```

Example tool invocation body:

```json
{
  "method": "search_npi_registry",
  "params": {
    "city": "Chicago",
    "state": "IL",
    "specialty": "Cardiology",
    "limit": 5
  }
}
```

## Deploy to Vercel

```bash
cd npi-mcp-server
vercel
vercel deploy --prod
```

After deployment, hit the endpoint at `https://<deployment>.vercel.app/api/mcp.py` using the standard
MCP initialize + call flow (same headers/body as other FastMCP endpoints).
