# CloudVault

Windows-first secure file storage with a FastAPI backend, SQL Server databases, and a
Textual terminal interface.

## Run locally

1. Provision the backend from an elevated PowerShell:

    ```powershell
    .\cloud_backend\scripts\install.ps1
    ```

2. Start the backend as a normal user:

    ```powershell
    .\cloud_backend\scripts\start.ps1
    ```

3. Start the TUI:

    ```powershell
    uv run cloud
    ```

    Use `uv run cloud --admin` for the administrator dashboard.

## Cloudflare Tunnel deployment

The backend startup can run an existing Cloudflare Named Tunnel after the local
backend is healthy. The elevated installation script installs `cloudflared` with
Winget when it is missing:

```powershell
.\cloud_backend\scripts\install.ps1
```

Configure the Named Tunnel name once in `cloud_backend\.env`, then start the
backend normally:

```dotenv
CLOUDFLARE_TUNNEL_NAME=your-named-tunnel
```

```powershell
.\cloud_backend\scripts\start.ps1
```

`CLOUDFLARE_TUNNEL_NAME` can also be supplied as a PowerShell environment
variable or with `-TunnelName`; those values override `.env`. The tunnel must
already be authenticated and configured to route
`api-cloudvault.tech` to `http://127.0.0.1:8000`. Startup verifies both
`http://127.0.0.1:8000/health` and `https://api-cloudvault.tech/health` before
reporting success. Stop both processes with:

```powershell
.\cloud_backend\scripts\stop.ps1
```

The frontend defaults to `https://api-cloudvault.tech`. A client installation
only needs `cloud_frontend`; it does not need the backend, SQL Server, or the
host storage directory.

The first administrator must enroll TOTP before logging in. Run
`.\cloud_backend\scripts\setup-first-admin.ps1` after the backend is healthy.

## TUI behavior

- Access tokens stay in memory; rotating refresh tokens are stored in the Windows
  keyring for up to 30 days.
- `q` quits without logging out, so the next start can restore the session.
- `l` logs out, revokes the refresh-token session, clears the keyring, and requires
  login on the next start.
- User shortcuts: `u` upload, `d` focus download, `r` remove, `q` quit, `l` logout.
- Admin shortcuts: `b` back, `q` quit, `l` logout.

User uploads accept a local file path. Downloads accept either an existing directory
(the original filename is used) or an explicit target file path. Downloads are written
to a temporary `.part` file and are reported successful only after the byte count is
verified and the final file is created.

## Documentation

- [API design](docs/API.md)
- [CLI/TUI design](docs/DESIGN.md)
- [Database design](docs/DB.md)
- [Implementation roadmap](docs/ROADMAP.md)
