from atlas.core.asset import (
    Asset,
    AssetType,
    AssetStatus,
    Criticality,
    Capability,
    ServiceRole,
    ServiceImportance,
    AssetRole,
    health_from_status,
)

from atlas.core.identity import AssetIdentity
from atlas.core.observation import Observation
from atlas.core.identity_resolver import generate_asset_id

from atlas.services.knowledge.runtime.identity import RuntimeIdentity

from atlas.services.assets.service_classifier import (
    ServiceClassifier,
)


class AssetBuilder:


    def __init__(self):

        self.service_classifier = ServiceClassifier()


    def _apply_infrastructure_roles(
        self,
        asset,
    ):
        """
        Apply roles proven directly by the builder's discovery
        context.

        Never infer operational roles from asset names.
        Higher-level RoleInference derives workload roles from
        metadata, observations and topology.
        """

        if asset.type == AssetType.SERVER:

            asset.asset_roles.add(
                AssetRole.HYPERVISOR
            )

        return asset


    def _status_from_proxmox(
        self,
        status,
    ):

        normalized = (
            status or "unknown"
        ).lower()

        if normalized in (
            "running",
            "online",
        ):

            return AssetStatus.ONLINE

        if normalized in (
            "stopped",
            "offline",
        ):

            return AssetStatus.OFFLINE

        return AssetStatus.UNKNOWN



    def _add_proxmox_observation(
        self,
        asset,
        telemetry,
    ):
        """Attach the latest Proxmox runtime telemetry to an asset."""

        if not telemetry:
            return asset

        cpu = telemetry.get("cpu")
        max_cpu = telemetry.get("max_cpu")
        memory = telemetry.get("memory")
        max_memory = telemetry.get("max_memory")
        disk = telemetry.get("disk")
        max_disk = telemetry.get("max_disk")
        net_in = telemetry.get("net_in")
        net_out = telemetry.get("net_out")
        uptime = telemetry.get("uptime")

        memory_percent = None

        if max_memory:
            memory_percent = round(
                (memory / max_memory) * 100,
                2,
            )

        severity = "info"

        if memory_percent is not None:

            if memory_percent >= 95:
                severity = "critical"

            elif memory_percent >= 85:
                severity = "warning"

        observation = Observation(
            asset_id=asset.id,
            type="proxmox_telemetry",
            value={
                "cpu": cpu,
                "max_cpu": max_cpu,
                "memory": memory,
                "max_memory": max_memory,
                "memory_percent": memory_percent,
                "disk": disk,
                "max_disk": max_disk,
                "net_in": net_in,
                "net_out": net_out,
                "uptime": uptime,
            },
            severity=severity,
            source="proxmox_api",
        )

        asset.add_observation(
            observation
        )

        asset.metadata.update(
            {
                "proxmox_vmid": telemetry.get("vmid"),
                "proxmox_type": telemetry.get("type"),
                "proxmox_status": telemetry.get("status"),
                "proxmox_cpu": cpu,
                "proxmox_max_cpu": max_cpu,
                "proxmox_memory": memory,
                "proxmox_max_memory": max_memory,
                "proxmox_memory_percent": memory_percent,
                "proxmox_disk": disk,
                "proxmox_max_disk": max_disk,
                "proxmox_net_in": net_in,
                "proxmox_net_out": net_out,
                "proxmox_uptime": uptime,
            }
        )

        return asset


    def from_smart(self, smart):

        if smart.model and "QEMU" in smart.model.upper():
            return None

        identity = AssetIdentity(
            model=smart.model,
            serial=smart.serial,
            vendor=smart.vendor,
            firmware=smart.firmware,
            device=smart.device,
        )

        return Asset(
            id=generate_asset_id("storage", identity),
            name=(
                smart.model
                if smart.model
                and (
                    not smart.vendor
                    or smart.model.startswith(smart.vendor)
                )
                else f"{smart.vendor} {smart.model}"
                if smart.vendor and smart.model
                else smart.model or "Unknown Storage"
            ),
            type=AssetType.STORAGE,
            identity=identity,
            status=AssetStatus.ONLINE,
            health=health_from_status(AssetStatus.ONLINE),
            criticality=Criticality.MEDIUM,
            capabilities={
                Capability.SMART,
                Capability.TEMPERATURE,
            },
        )


    def from_proxmox_host(self, host):

        identity = AssetIdentity(
            serial=host["hostname"],
            model="Virtualization Host",
            vendor=host["vendor"],
        )

        status_map = {
            "online": AssetStatus.ONLINE,
            "offline": AssetStatus.OFFLINE,
        }

        status = status_map.get(
            str(host.get("status", "")).lower(),
            AssetStatus.UNKNOWN,
        )

        asset = Asset(
            id=generate_asset_id("server", identity),
            name=host["hostname"],
            type=AssetType.SERVER,
            identity=identity,
            status=status,
            health=health_from_status(status),
            criticality=Criticality.HIGH,
            capabilities={
                Capability.LOGS,
                Capability.SNAPSHOT,
                Capability.BACKUP,
            },
        )

        asset = self._apply_infrastructure_roles(
            asset
        )

        return self._add_proxmox_observation(
            asset,
            host,
        )

    def from_proxmox_vm(self, vm):

        identity = AssetIdentity(
            serial=vm["vmid"],
            model="Virtual Machine",
            vendor="Proxmox",
        )

        status_map = {
            "running": AssetStatus.ONLINE,
            "stopped": AssetStatus.OFFLINE,
            "paused": AssetStatus.DEGRADED,
        }

        status = status_map.get(
            str(vm.get("status", "")).lower(),
            AssetStatus.UNKNOWN,
        )

        asset = Asset(
            id=generate_asset_id("vm", identity),
            name=vm["hostname"],
            type=AssetType.VM,
            identity=identity,
            status=status,
            health=health_from_status(status),
            criticality=Criticality.HIGH,
            capabilities={
                Capability.START,
                Capability.STOP,
                Capability.RESTART,
                Capability.SNAPSHOT,
            },
        )

        asset = self._apply_infrastructure_roles(
            asset
        )

        return self._add_proxmox_observation(
            asset,
            vm,
        )

    def from_proxmox_lxc(self, lxc):

        identity = AssetIdentity(
            serial=lxc["vmid"],
            model="Linux Container",
            vendor="Proxmox",
        )

        status_map = {
            "running": AssetStatus.ONLINE,
            "stopped": AssetStatus.OFFLINE,
            "paused": AssetStatus.DEGRADED,
        }

        status = status_map.get(
            str(lxc.get("status", "")).lower(),
            AssetStatus.UNKNOWN,
        )

        asset = Asset(
            id=generate_asset_id("lxc", identity),
            name=lxc["hostname"],
            type=AssetType.LXC,
            identity=identity,
            status=status,
            health=health_from_status(status),
            criticality=Criticality.HIGH,
            capabilities={
                Capability.START,
                Capability.STOP,
                Capability.RESTART,
                Capability.SNAPSHOT,
            },
        )

        return self._add_proxmox_observation(
            asset,
            lxc,
        )

    def from_docker_service(self, service):

        if service.state == "running":

            status = AssetStatus.ONLINE

        elif service.state == "exited":

            status = AssetStatus.OFFLINE

        else:

            status = AssetStatus.DEGRADED


        identity = AssetIdentity(

            serial=service.name,

            vendor="Docker",

        )


        runtime_identity = RuntimeIdentity(

            container_id=service.id,

        )


        return Asset(

            id=generate_asset_id(
                "application",
                identity
            ),

            name=service.name,

            type=AssetType.APPLICATION,

            identity=identity,

            status=status,

            metadata={

                "container_id": service.id,

                "image": service.image,

                "docker_status": service.status,

                "state": service.state,

                "ports": service.ports,

            },

            health=health_from_status(status),

            criticality=Criticality.MEDIUM,

            service_role=ServiceRole.UNKNOWN,

            capabilities={

                Capability.LOGS,

                Capability.START,

                Capability.STOP,

                Capability.RESTART,

            },

        )



    def infer_asset_roles(
        self,
        role,
    ):

        if role == ServiceRole.CONTAINER_RUNTIME:
            return set()


        if role == ServiceRole.DATABASE:
            return {
                AssetRole.DATABASE_SERVER
            }


        if role == ServiceRole.MONITORING:
            return {
                AssetRole.MONITORING_NODE
            }


        if role == ServiceRole.STORAGE:
            return {
                AssetRole.STORAGE_NODE
            }


        if role == ServiceRole.SECURITY:
            return {
                AssetRole.SECURITY_NODE
            }


        return set()



    def from_system_service(self, service):

        identity = AssetIdentity(

            serial=f"{service.hostname}:{service.name}",

            model="Systemd Service",

            vendor="Linux",

        )


        status = AssetStatus.ONLINE


        if service.status != "active":

            status = AssetStatus.OFFLINE


        classification = self.service_classifier.classify(
            service.name
        )



        return Asset(

            id=generate_asset_id(
                "service",
                identity
            ),

            name=service.name,

            type=AssetType.SERVICE,

            identity=identity,

            status=status,

            metadata={
                "hostname": service.hostname,
                "classification_reason": classification.reason,
            },

            health=health_from_status(status),

            criticality=Criticality.MEDIUM,

            service_role=classification.role,

            service_importance=classification.importance,

            asset_roles=self.infer_asset_roles(
                classification.role
            ),


            capabilities={

                Capability.START,

                Capability.STOP,

                Capability.RESTART,

                Capability.LOGS,

            },

        )

