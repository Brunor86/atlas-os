from rich.table import Table

from atlas.models.docker import DockerInfo


class DockerRenderer:

    def render(self, info: DockerInfo) -> Table:

        table = Table(
            title="ATLAS DOCKER"
        )

        table.add_column(
            "Name",
            style="cyan"
        )

        table.add_column(
            "Status",
            style="green"
        )

        table.add_column(
            "Image"
        )

        for container in info.containers:

            table.add_row(
                container.name,
                container.status,
                container.image,
            )

        return table
