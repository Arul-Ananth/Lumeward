# Enterprise packaging

Lumeward server mode uses PostgreSQL plus Qdrant. PostgreSQL remains customer-managed.
For a bundled Qdrant deployment, distribute a platform-specific Qdrant executable
next to the Lumeward server executable and use the server's lifecycle support.

## Runtime configuration

```env
QDRANT_MODE=bundled
QDRANT_URL=http://127.0.0.1:6333
QDRANT_API_KEY=generate-a-long-random-value
BUNDLED_QDRANT_BINARY=/opt/lumeward/qdrant/qdrant
BUNDLED_QDRANT_CONFIG_PATH=/opt/lumeward/qdrant/production.yaml
BUNDLED_QDRANT_STORAGE_DIR=/var/lib/lumeward/qdrant
```

On Windows, use absolute paths with forward slashes or escaped backslashes. The
bundled process binds only to loopback; only Lumeward should access it. The
service installer must run Lumeward under a dedicated non-administrator account
that has write access only to its data and log directories.

## Release inputs

- Pin a Qdrant release per target OS/architecture and verify its published checksum.
- Include its license notice and an SBOM in the installer.
- Install Lumeward as one service; it starts and stops the bundled Qdrant child.
- Keep PostgreSQL outside the application directory and back it up independently.
- Test install, upgrade, restart, and recovery against existing Qdrant storage.

## Desktop

Desktop installers do not bundle PostgreSQL or Qdrant for enterprise mode. The
user enters the enterprise server URL in Settings, restarts Lumeward, signs in,
and selects a workspace.
