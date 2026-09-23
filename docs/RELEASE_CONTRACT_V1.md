# ATLAS OS v1.0 Release Contract

## Stable release

`v1.0.0`

Clean-room-qualified release-candidate baseline:

`v1.0.0-rc2`

`24168ab898c33efdb91d275e5958105be96851d1`

Qualification date:

`2026-09-23`

## Definition of v1.0

ATLAS OS v1.0 is considered release-ready when it can:

1. discover and persist infrastructure knowledge;
2. maintain stable Asset Registry identity;
3. maintain infrastructure relationships and topology;
4. collect snapshots and health evidence;
5. correlate operational events and incidents;
6. investigate without granting the LLM direct mutation authority;
7. create governed operation proposals;
8. enforce policy and explicit authorization;
9. guarantee at-most-one supervised execution attempt per approval;
10. verify the real post-execution state independently;
11. preserve recovery and verification history;
12. degrade explicitly when external providers are unavailable;
13. avoid destructive interpretation of incomplete discovery;
14. survive a normal host reboot and restore its operating state.

## Authoritative action chain

    Request
      -> supported action
      -> deterministic target validation
      -> Asset Registry
      -> capability
      -> policy / criticality
      -> SafeAction
      -> PENDING_APPROVAL
      -> explicit human approval
      -> durable execution claim
      -> explicit execution route
      -> handler allowlist
      -> action
      -> independent verification
      -> VERIFIED | RECOVERY_REQUIRED | EXECUTION_FAILED

No stage may be bypassed merely because another layer believes the operation
is safe.

## At-most-once approval execution

An approved operation must acquire a persisted execution claim before an
infrastructure handler is invoked.

The claim is durable and atomic.

A consumed approval is not automatically reusable after:

- handler failure;
- process interruption;
- uncertain remote state;
- persistence failure after the attempt.

A new attempt requires a new proposal and a new approval.

## Verification

Remote command success and infrastructure success are different concepts.

After handler completion, ATLAS independently observes the target.

Recovery verification does not silently execute the original operation again.

## Provider degradation

Docker and Proxmox are external providers.

Their unavailability is explicitly represented by:

    available = false
    error = bounded diagnostic evidence

An unavailable provider is never represented as authoritative proof of an
empty inventory.

Health becomes warning/degraded while the remainder of ATLAS stays available.

Prometheus is optional dashboard metric enrichment. Its absence must not
prevent the ATLAS web console from rendering.

## Discovery authority

Discovery errors produce:

    complete = false

When discovery is incomplete:

- inventory reconciliation is skipped;
- missing assets are not interpreted as disappearance;
- mutating NOC generation is skipped;
- authoritative recovery transitions requiring negative evidence are skipped.

## Local host truth

System, storage and network collection remain fail-closed.

ATLAS must not fabricate a healthy local host if those sources fail.

## AI boundary

The local AI runtime is intelligence, not infrastructure authority.

When unavailable:

    status = OFFLINE
    provider_available = false

The LLM has no arbitrary command execution capability.

## Operator execution vocabulary

Docker:
- start container
- stop container
- restart container

systemd:
- start service
- stop service
- restart service

Proxmox QEMU:
- start vm
- stop vm
- restart vm

Proxmox LXC:
- restart lxc

Execution routing does not bypass policy or handler allowlists.

## Out of scope for v1.0

Not v1.0 release blockers:

- unrestricted autonomous mutation;
- arbitrary shell execution;
- automatic destructive rollback;
- generic VM/LXC resource resizing;
- unrestricted service execution;
- Home Assistant control;
- ATLAS Science;
- Atlas Sky;
- OlivaSat domain functionality;
- generalized Git rollback;
- self-modifying infrastructure policy.

## Release Readiness Gate 1

Passed on 2026-09-22.

Validated:

- production Git baseline;
- enabled and active systemd services;
- SQLite integrity;
- online SQLite backup;
- runtime secret presence;
- Docker control plane;
- Proxmox control plane;
- HTTP baseline;
- controlled collector restart;
- controlled web restart;
- post-cycle DB integrity;
- zero relevant service warnings.

## Release Readiness Gate 2

Passed on 2026-09-22.

A real reboot of the ATLAS VM was performed.

Validated:

- boot ID changed;
- release code survived reboot;
- data storage remounted;
- Docker recovered;
- atlas-web recovered;
- atlas-collector recovered;
- 25/25 Docker containers recovered;
- HTTP/API recovered;
- DB integrity remained OK;
- WAL mode remained active;
- runtime secrets restored;
- Proxmox access restored;
- Operator API restored;
- zero failed systemd units;
- zero ATLAS boot warnings.

## Release Readiness Gate 3

Passed on 2026-09-22.

Failures were injected only inside isolated processes.

Validated:

- Docker failure isolation;
- Proxmox failure isolation;
- simultaneous provider degradation;
- local-host fail-closed behavior;
- incomplete-discovery mutation guard;
- AI provider OFFLINE behavior;
- snapshot schema v3 failure evidence;
- production remained healthy after testing.

## Automated regression baseline

    792 passed

The release documentation change must preserve that full result.

## Stable acceptance

`v1.0.0` may be tagged only when:

- the repository worktree is clean;
- the full regression suite passes;
- SQLite integrity passes;
- a verified production backup exists;
- atlas-web is active;
- atlas-collector is active;
- the clean-room installation contract remains satisfied;
- reboot persistence remains satisfied;
- idempotent reinstall remains satisfied;
- optional providers remain non-blocking when not configured;
- configured production providers remain healthy;
- the stable release bundle, wheel, manifest and checksums are verified;
- public documentation contains no private infrastructure defaults;
- Apache License 2.0 is included in the repository and release bundle;
- release documentation is committed before the stable tag is created.

Final `v1.0.0` requires no unresolved release-candidate defect violating this
contract.
