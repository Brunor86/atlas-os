# ATLAS OS

ATLAS OS is a personal infrastructure intelligence and governed-operations
platform for homelabs.

It discovers infrastructure, maintains an Asset Registry and topology,
collects operational evidence, correlates events and incidents, supports
read-only AI-assisted investigation, and exposes a controlled Operator for
explicitly approved infrastructure actions.

## Release

Current stable release:

`v1.0.0`

ATLAS v1.0 is deliberately conservative. Its objective is not unrestricted
autonomy. Its objective is trustworthy infrastructure knowledge and safe,
auditable operation.

## v1.0 operating contract

ATLAS v1.0 can:

- discover and persist infrastructure assets;
- maintain stable identities, capabilities, criticality and relationships;
- collect infrastructure snapshots;
- evaluate health and degradation;
- correlate events and persistent incidents;
- investigate infrastructure using deterministic tools and local AI;
- create governed operational proposals;
- require explicit human approval before mutation;
- reserve approvals durably for at-most-one execution attempt;
- execute only explicit routed and allowlisted actions;
- independently verify real post-execution state;
- preserve verification and recovery history;
- degrade explicitly when Docker, Proxmox or AI is unavailable;
- keep optional Prometheus metric enrichment non-blocking;
- prevent incomplete discovery from causing destructive reconciliation;
- recover automatically after a normal host reboot.

## Architecture

    Infrastructure
        |
        v
    Providers / Discovery
        |
        +--> Asset Registry
        |       |
        |       +--> Knowledge / Graph
        |
        +--> Snapshots / Health
                |
                +--> Events
                        |
                        +--> Incidents / NOC
                                |
                                +--> Investigation
                                |
                                +--> SafeAction
                                        |
                                        +--> Policy
                                                |
                                                +--> Human Approval
                                                        |
                                                        +--> Execution Claim
                                                                |
                                                                +--> Executor
                                                                        |
                                                                        +--> Verification

The AI layer does not own infrastructure authority.

Policy, Asset Registry truth, persisted approvals, execution claims, handlers
and independent verification remain authoritative.

## Operator V1

Supported execution vocabulary:

Docker containers:
- start
- stop
- restart

systemd services:
- start
- stop
- restart

Proxmox QEMU VM:
- start
- stop
- restart

Proxmox LXC:
- restart

Execution support does not imply policy permission.

Handler allowlists, capabilities, asset presence, importance and criticality
remain independent safety gates.

There is no arbitrary shell execution path in the Operator UI.

## Safety boundaries

ATLAS v1.0 intentionally does not provide:

- unrestricted autonomous execution;
- arbitrary shell mutation;
- automatic destructive rollback;
- automatic retry of uncertain actions;
- direct LLM infrastructure mutation;
- bypass of protected HIGH/CRITICAL assets;
- mutation based on incomplete discovery.

A successful remote command is not considered proof of infrastructure
success. ATLAS independently verifies the resulting state.

An uncertain result becomes a recovery problem, not an automatic retry.

## Provider failure semantics

Docker unavailable:

    docker.available = false
    health = warning

Proxmox unavailable:

    proxmox.available = false
    health = warning

An unavailable provider is not treated as an authoritative empty inventory.

Incomplete discovery:

    DiscoveryResult.complete = false

causes authoritative inventory reconciliation and mutating NOC processing to
be skipped.

AI provider unavailable:

    status = OFFLINE
    provider_available = false

does not grant or remove infrastructure authority.

Local system, storage and network truth remains fail-closed.

## Runtime

Main production services:

    atlas-web.service
    atlas-collector.service

Persistent operational state is stored in SQLite.

Production uses WAL mode.

## Release qualification

The v1.0 release line has been validated with:

- 792 automated tests;
- SQLite integrity_check and quick_check;
- consistent online database backup;
- controlled ATLAS service restart;
- real VM reboot;
- automatic service recovery;
- 25/25 Docker workload recovery;
- storage remount after boot;
- runtime secret restoration;
- Proxmox recovery;
- Operator API recovery;
- Docker provider failure isolation;
- Proxmox provider failure isolation;
- simultaneous external-provider degradation;
- local-host fail-closed behavior;
- incomplete-discovery mutation guard;
- AI provider OFFLINE behavior;
- snapshot schema v3 degradation evidence.

## Documentation

See:

- `docs/RELEASE_CONTRACT_V1.md`
- `docs/BACKUP_RESTORE_V1.md`
- `docs/BOOT_RECOVERY_V1.md`
- `docs/OPERATOR_SINGLE_EXECUTION.md`

## Development validation

From the repository root:

    export PYTHONPATH="$PWD/src"
    /opt/atlas/.venv/bin/python -m pytest -q

A release is accepted only with a clean full suite.

## Versioning

Runtime version information is derived from Git tags.

Package metadata uses PEP 440:

    1.0.0

Git release tag:

    v1.0.0

## Beyond v1.0

Home Assistant control, ATLAS Science, Atlas Sky, broader autonomous
operation, generalized infrastructure mutation and domain-specific systems
belong after the v1.0 stability boundary.

ATLAS OS v1.0 establishes the infrastructure operating core those systems
can build upon.
