from atlas.services.snapshots.loader import SnapshotLoader


loader = SnapshotLoader()

infra = loader.load()


print(infra.system.hostname)

print(
    infra.docker.total,
    infra.docker.running
)

print(
    len(infra.proxmox.guests)
)

