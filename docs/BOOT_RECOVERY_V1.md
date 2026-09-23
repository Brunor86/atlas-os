# ATLAS Boot / Recovery V1

## Status

Validated in production on 2026-09-20.

Production validation commit at closure:

`d5acd3e0bdca32537bd45f191c436ef38cf0f00f`

Boot / Recovery V1 prevents the ATLAS collector from starting its
authoritative operational cycle before required boot dependencies are
actually usable.

## Problem

During a real VM boot, `network-online.target` did not guarantee that
the Proxmox endpoint was already reachable.

The collector previously started while the network path to Proxmox was
still unavailable and its first operational cycle failed with:

`Network is unreachable`

## Runtime contract

The collector uses:

- `After=network-online.target docker.service`
- `Wants=network-online.target docker.service`
- `ExecStartPre=/usr/local/sbin/atlas-wait-ready`
- `TimeoutStartSec=150`

Docker is intentionally a `Wants`, not a `Requires`.

The readiness probe verifies:

1. Docker executable exists.
2. Docker socket exists.
3. `docker info` succeeds.
4. The configured Proxmox host and port accept a TCP connection.

`ATLAS_PROXMOX_URL` is authoritative when present.

Example Proxmox endpoint:

`https://proxmox.example:8006`

## Versioned assets

Repository:

- `ops/bin/atlas-wait-ready`
- `ops/systemd/atlas-collector.service.d/boot-hardening.conf`

Installed:

- `/usr/local/sbin/atlas-wait-ready`
- `/etc/systemd/system/atlas-collector.service.d/boot-hardening.conf`

Validated SHA256:

- `atlas-wait-ready`
  - `403fbda68e56748b91664072fbf091e35897a0e964f876c511315ef6ee9f0e2d`
- `boot-hardening.conf`
  - `ab8ce53b21132319d5df2fa6d60d92bb5012f6cf86115372988838d3c890fd98`

## Existing deployment prerequisites

This milestone does not own or replace:

- `/etc/systemd/system/atlas-collector.service`
- `/etc/systemd/system/atlas-collector.service.d/environment.conf`
- `/etc/systemd/system/atlas-collector.service.d/path.conf`
- `/etc/atlas/atlas.env`

The environment drop-in supplies the ATLAS environment.

The path drop-in supplies the operating-system PATH required by
Discovery and operational tooling.

## Installation

Validation only:

    sudo scripts/install-boot-hardening.sh --check

Install/update:

    sudo scripts/install-boot-hardening.sh --install

Installation:

- creates a backup under `/opt/atlas-backups`
- installs the versioned files
- runs `systemctl daemon-reload`
- validates the effective systemd contract
- executes the readiness probe
- does not restart ATLAS
- does not reboot the VM

## Production proof

The final reboot validation reproduced the original boot race:

1. Docker became available.
2. Proxmox was initially unreachable with `Network is unreachable`.
3. `atlas-wait-ready` kept the collector blocked.
4. Proxmox became reachable.
5. readiness returned PASS.
6. the collector started.
7. the first authoritative cycle completed successfully.
8. Discovery returned 71 assets and `complete=True`.
9. reconciliation returned 71 ACTIVE, 0 STALE, 10 RETIRED and 0 transitions.
10. Docker recovered 25/25 containers.
11. infrastructure health was `healthy`.
12. lifecycle delta was 0.
13. action delta was 0.
14. presence transition delta was 0.
15. validated API endpoints returned HTTP 200.

This proves that transient boot-time network unavailability is contained
before the collector mutation path starts.
