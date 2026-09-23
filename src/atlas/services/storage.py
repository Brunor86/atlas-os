import psutil

from atlas.models.storage import StorageInfo


class StorageService:

    def get_info(self) -> list[StorageInfo]:

        disks = []

        ignored = {
            "/proc",
            "/sys",
            "/dev",
            "/run",
                "/boot/efi",
        }

        partitions = psutil.disk_partitions(
            all=False
        )

        for partition in partitions:

            mountpoint = partition.mountpoint

            if mountpoint in ignored:
                continue

            try:
                usage = psutil.disk_usage(
                    mountpoint
                )

            except PermissionError:
                continue

            total_gb = usage.total / (1024 ** 3)
            used_gb = usage.used / (1024 ** 3)
            free_gb = usage.free / (1024 ** 3)

            percent = (
                usage.used / usage.total * 100
                if usage.total > 0
                else 0
            )

            disks.append(
                StorageInfo(
                    filesystem=partition.device,
                    mountpoint=mountpoint,
                    total_gb=round(total_gb, 2),
                    used_gb=round(used_gb, 2),
                    free_gb=round(free_gb, 2),
                    usage_percent=round(percent, 2),
                )
            )

        return disks
