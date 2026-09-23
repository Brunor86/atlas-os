# Changelog

## v1.0.0

First stable release of the ATLAS OS v1.0 infrastructure operating core.

### Stable release qualification

- Promoted from the clean-room-qualified `v1.0.0-rc2` runtime baseline.
- Fresh Debian 13 installation passed without Docker, Prometheus, Proxmox,
  Ollama or Git being required at runtime.
- Reboot persistence and same-release idempotent reinstall passed.
- Production regression baseline: 792 tests.
- SQLite integrity, systemd startup, API endpoints and dashboard verified.
- Optional Docker, Prometheus and Proxmox integrations remain non-blocking
  when not configured.
- Public release is licensed under Apache License 2.0.
- Private homelab network references were removed from public documentation.

## v1.0.0-rc2

Second release candidate focused on public clean-room installation.

### Clean-room hardening

- Docker is optional at runtime and no longer prevents ATLAS startup when
  neither the Docker CLI nor Docker socket is present.
- Docker provider connection is deferred to the collection boundary so
  configured-but-unavailable Docker remains an observable provider failure.
- Prometheus dashboard enrichment is optional and no longer causes the web
  console to fail when Prometheus is unavailable.
- Minimal Debian 13 installation requirements now document `python3-venv`.
- Public clean-room regression baseline: 792 tests.

## v1.0.0-rc1

First release candidate for the ATLAS OS v1.0 operating core.

### Infrastructure knowledge

- Asset Registry.
- Stable infrastructure identities.
- Discovery and topology.
- Knowledge and graph services.
- Snapshot persistence.
- Health evaluation.
- Event and incident lifecycle.
- Inventory reconciliation with incomplete-discovery protection.

### Intelligence

- Deterministic query paths.
- Local AI integration.
- Read-only investigation architecture.
- Explicit AI OFFLINE health behavior.
- Separation between AI reasoning and mutation authority.

### Operator

- SafeAction workflow.
- Policy and capability gates.
- Human approval requirement.
- Durable at-most-once execution claims.
- Explicit execution routes.
- Docker operations.
- systemd operations.
- Proxmox VM operations.
- Proxmox LXC restart.
- Independent post-execution verification.
- Recovery-required state.
- Manual re-verification.
- Verification history.
- Operator Control Center.

### Reliability

- Boot/readiness hardening.
- Real reboot qualification.
- SQLite backup and integrity validation.
- Docker provider failure isolation.
- Proxmox provider failure isolation.
- Snapshot schema v3 provider evidence.
- Incomplete discovery mutation guard.
- AI provider OFFLINE degradation.
- Release qualification baseline: 728 tests.

### Intentional limits

v1.0 does not include unrestricted autonomous mutation, arbitrary shell
execution, automatic destructive rollback, Home Assistant control,
ATLAS Science, Atlas Sky or generalized resource resizing.
