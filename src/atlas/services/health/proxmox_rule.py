from atlas.models.alert import Alert
from atlas.services.health.base import HealthRule


class ProxmoxRule(
    HealthRule
):

    def evaluate(
        self,
        infra,
        health,
        assets=None,
    ):

        proxmox = (
            getattr(
                infra,
                "proxmox",
                None,
            )
            if infra
            else None
        )


        if proxmox is None:
            return


        if (
            getattr(
                proxmox,
                "available",
                True,
            )
            is not False
        ):
            return


        if health.status == "healthy":
            health.status = "warning"


        health.alerts.append(
            Alert(
                severity="warning",
                source="proxmox",
                title="Proxmox unavailable",
                message=(
                    getattr(
                        proxmox,
                        "error",
                        None,
                    )
                    or (
                        "Proxmox provider "
                        "is unavailable"
                    )
                ),
                affected_assets=[],
            )
        )
