# Obsidian Layer

Obsidian is a local-first memory and audit workspace. NeuroAgent keeps the Python adapter under
`app/obsidian` and mounts a real vault into the Docker Compose `obsidian` service.

## Docker Service

`docker-compose.yml` defines an `obsidian` service based on the LinuxServer Obsidian image.

- Web UI: `http://127.0.0.1:3000`
- Optional HTTPS UI: `https://127.0.0.1:3001`
- Local REST plugin port: `http://127.0.0.1:27123`
- Mounted vault: `app/obsidian/vaults/NeuroAgentVault`
- Mounted Obsidian releases metadata repo: `app/obsidian/obsidian-releases`

The official Obsidian source application is not open-source. The local repository under
`app/obsidian/obsidian-releases` tracks Obsidian release and community plugin metadata that can feed
plugin/catalog workflows.

## Vault

The default vault path is `app/obsidian/vaults/NeuroAgentVault`. It includes:

- `00_Inbox`
- `01_Research/Literature`
- `01_Research/Hypotheses`
- `01_Research/Experiments`
- `01_Research/Paper_Drafts`
- `02_Domains/Cybersecurity`
- `03_Agent_Runs/Daily`
- `04_Decisions`
- `05_Evaluations`
- `07_Artifacts`

## Configuration

- `OBSIDIAN_ENABLED=false`
- `OBSIDIAN_BASE_URL=http://obsidian:27123`
- `OBSIDIAN_API_KEY=`
- `OBSIDIAN_VAULT_NAME=NeuroAgentVault`
- `OBSIDIAN_WEB_URL=http://obsidian:3000`
- `OBSIDIAN_VAULT_PATH=/app/app/obsidian/vaults/NeuroAgentVault`

## Adapter Status

When `OBSIDIAN_ENABLED=false`, API note operations return deterministic payloads for tests and
offline development.

When `OBSIDIAN_ENABLED=true`, the local adapter writes Markdown notes directly to
`OBSIDIAN_VAULT_PATH` and searches Markdown files in that vault. REST-backed read/write/search can be
enabled later by installing and configuring the Obsidian Local REST API plugin inside the Docker
Obsidian app.
