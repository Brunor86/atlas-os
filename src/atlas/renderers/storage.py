from rich.table import Table

from atlas.models.storage import StorageInfo


class StorageRenderer:

    def render(self, disks: list[StorageInfo]) -> Table:

        table = Table(
            title="ATLAS STORAGE"
        )

        table.add_column(
            "Filesystem",
            style="cyan"
        )

        table.add_column(
            "Mountpoint",
            style="green"
        )

        table.add_column(
            "Total GB"
        )

        table.add_column(
            "Used GB"
        )

        table.add_column(
            "Free GB"
        )

        table.add_column(
            "Usage %"
        )

        for disk in disks:

            table.add_row(
                disk.filesystem,
                disk.mountpoint,
                str(disk.total_gb),
                str(disk.used_gb),
                str(disk.free_gb),
                f"{disk.usage_percent}%",
            )

        return table
