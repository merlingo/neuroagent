# Security

Unknown tools are blocked unless registered. Forbidden tools are denied. High-risk and critical
tools create approval requests instead of executing in governed agent runs.

## API Key Authentication

API key authentication is disabled by default for local development. Enable it with:

```env
API_AUTH_ENABLED=true
API_KEYS=tenant-a-key:tenant-a,tenant-b-key:tenant-b
ADMIN_API_KEYS=admin-key
```

Clients send `X-API-Key`. Tenant keys can access only their own tenant-scoped runs, documents,
RAG searches, approvals, and evals. Admin keys can access all tenants and protected admin endpoints
such as `/admin/db/seed-contracts`.

Do not store API keys in artifacts, Obsidian notes, logs, or audit payloads. Rotate keys through
environment configuration.

## Tool Execution

- Every tool contract must have an explicit registry handler.
- Registry execution never falls back to a generic handler for unknown tools.
- `shell.execute`, `file.delete_file`, and GitHub write tools are high-risk or approval-required.
- The `/tools/{tool_id}/test` endpoint is a development surface and should not be exposed as a
  production write surface.

## GitHub Tokens

GitHub tools use `GITHUB_TOKEN` for REST API calls. Prefer a fine-grained personal access token and
grant only the minimum repository permissions required:

- Metadata read for repository lookup.
- Issues read for issue lookup/listing.
- Issues write for creating issues or comments.
- Contents read for reading repository files.
- Contents write for updating repository files.

Tokens must be configured through environment variables and must not be persisted in the database,
artifacts, Obsidian notes, logs, or audit payloads.
