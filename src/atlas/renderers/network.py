from rich.table import Table

from atlas.models.network import NetworkInfo


class NetworkRenderer:

    def render(self, info: NetworkInfo):

        table = Table(
            title="ATLAS NETWORK"
        )

        table.add_column(
            "Interface",
            style="cyan"
        )

        table.add_column(
            "Address"
        )

        table.add_column(
            "Status",
            style="green"
        )


        for interface in info.interfaces:

            table.add_row(
                interface.name,
                interface.address,
                interface.status,
            )


        return table
