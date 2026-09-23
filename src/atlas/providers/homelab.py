from atlas.models.homelab import Homelab
from atlas.services.system import SystemService


class HomelabProvider:

    def build(self) -> Homelab:

        system = SystemService().get_info()

        return Homelab(
            system=system
        )
