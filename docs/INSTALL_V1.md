# ATLAS OS v1 Installation

ATLAS OS v1 is installed from a release wheel and the accompanying
release-bundle installer.

A Git checkout is not required by the installed runtime.

## Supported baseline

The v1 installer targets a Debian system using systemd and Python 3.13+.

On a minimal Debian 13 installation, become root and install the
bootstrap prerequisites before downloading and running ATLAS:

    su -
    apt-get update
    apt-get install -y ca-certificates wget python3-venv

The public Quick Start deliberately does not assume that `sudo` or `curl`
is installed.

The release wheel contains ATLAS itself. Python package dependencies are
resolved by pip during installation, so network access to the configured
Python package index is required unless those dependencies have already
been provisioned locally.

The installer must run as root because ATLAS v1 integrates with host
infrastructure controls including systemd and Docker.

## Filesystem contract

    /opt/atlas/venv
        ATLAS Python virtual environment and installed wheel.

    /etc/atlas/atlas.env
        Core runtime configuration.

    /etc/atlas/atlas-web.env
        Operator authorization and execution allowlists.

    /var/lib/atlas/atlas.db
        Default persistent SQLite database.

    /var/backups/atlas
        Installation and operational backups.

    /usr/local/sbin/atlas-wait-ready
        Boot readiness probe.

    /etc/systemd/system/atlas-web.service
        Web console service.

    /etc/systemd/system/atlas-collector.service
        Infrastructure collector service.

## Install

Build or obtain the ATLAS wheel, then run:

    scripts/install-atlas.sh \
        --wheel /path/to/atlasctl-1.0.1-py3-none-any.whl

The installer:

1. validates Python and systemd prerequisites;
2. creates the standard ATLAS filesystem layout;
3. preserves existing configuration;
4. creates a Python virtual environment;
5. installs the supplied wheel;
6. creates a random Operator bearer token on first install;
7. keeps all Operator execution allowlists empty by default;
8. initializes and validates SQLite;
9. installs systemd units and the readiness probe;
10. enables and starts ATLAS;
11. verifies the local web health endpoint.

Use `--no-start` to install and enable the services without starting them.

## Network exposure

The default web bind address is:

    127.0.0.1:8091

This is intentional.

To expose ATLAS on a trusted LAN or overlay network, edit:

    /etc/atlas/atlas.env

and explicitly change `ATLAS_WEB_HOST`, then restart `atlas-web.service`.

## Optional providers

Docker is optional.

Proxmox is optional.

Ollama is optional.

Prometheus metric enrichment is optional.

Provider absence must degrade explicitly and must not prevent the ATLAS
core from starting when that provider is not configured.

## Operator safety

A fresh installation is fail-closed.

The installer generates an Operator token but configures no executable
systemd services, QEMU VMIDs, or LXC VMIDs.

Infrastructure mutation remains unavailable until an administrator
explicitly configures allowlists.

## Release bundle

Official ATLAS OS v1 installation media is assembled as a release bundle.

From a clean source tree:

    scripts/build-release-bundle.sh

The resulting archive contains:

- the versioned `atlasctl` wheel;
- `scripts/install-atlas.sh`;
- the boot readiness probe;
- public systemd units;
- public configuration examples;
- installation documentation;
- `RELEASE_MANIFEST.txt`;
- `SHA256SUMS`.

The bundle contains no Git metadata and the installed ATLAS runtime does
not require a repository checkout.

Before packaging, the builder requires a clean source worktree and audits
the public bundle for private RFC1918 network defaults.
