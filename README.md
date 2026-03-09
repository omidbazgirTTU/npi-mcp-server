# NPI MCP Server

FastMCP wrapper around the CMS NPI Registry (https://npiregistry.cms.hhs.gov/). Available tools:

- `search_npi_registry` – flexible provider lookups across names, NPIs, organizations, taxonomies, geography, license filters, and gender/sole-proprietor flags.
- `list_org_investigators` – list principal investigators (individual NPIs) within an organization, optionally narrowed by specialty/taxonomy and city/state.
- `get_org_roster_snapshot` – condensed roster view (NPI + primary taxonomy + city/state) for quick exports.
- `list_organizations_by_geo` – discover distinct organization names (NPI-2) in a target ZIP/city/state to help seed PI lookups.
- `autocomplete_provider_taxonomy` – lightweight taxonomy/keyword autocomplete to help users select valid specialties.
- `verify_npi_roster` – batch validator for NPIs or investigator rosters; flags mismatches or missing records.
- `find_nearby_providers` – ranks providers near a reference ZIP code using USPS centroids and approximate distance calculations.

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

To list cardiology PIs within UCSF's system:

To list cardiology PIs within UCSF's system:

```json
{
  "method": "list_org_investigators",
  "params": {
    "organization_name": "UCSF Medical Center",
    "specialty": "Cardiology",
    "state": "CA",
    "limit": 20
  }
}

Fetch nearby cardiologists within 25 miles of ZIP 94143:

```json
{
  "method": "find_nearby_providers",
  "params": {
    "postal_code": "94143",
    "specialty": "Cardiology",
    "radius_miles": 25,
    "limit": 15
  }
}
```

Autocomplete a taxonomy query:

```json
{
  "method": "autocomplete_provider_taxonomy",
  "params": { "query": "nephro" }
}
```

Batch-verify NPIs:

```json
{
  "method": "verify_npi_roster",
  "params": {
    "entries": [
      { "npi": "1234567890", "first_name": "JANE", "last_name": "DOE" },
      { "npi": "1098765432", "organization_name": "UCSF Medical Center" }
    ]
  }
}

Discover organizations in San Francisco ZIP 94143:

```json
{
  "method": "list_organizations_by_geo",
  "params": {
    "postal_code": "94143",
    "state": "CA",
    "specialty": "Cardiology",
    "limit": 20
  }
}
```
```
```
```

## Deploy to Vercel

```bash
cd npi-mcp-server
vercel
vercel deploy --prod
```

After deployment, use the cleaner endpoint `https://<deployment>.vercel.app/mcp` with MCP Inspector or ChatGPT MCP apps. (The legacy `/api/mcp.py` path still works via rewrite, but `/mcp` is the canonical URL.)

All tool responses also include `ui` payloads wired to lightweight HTML widgets (rendered automatically in clients that support `io.modelcontextprotocol/ui`), providing tables/lists for provider search, organization rosters, taxonomy suggestions, verification batches, and nearby matches.
