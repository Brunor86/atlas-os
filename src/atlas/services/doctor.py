from atlas.models.doctor import CheckResult, DoctorReport
from atlas.services.system import SystemService
from atlas.services.docker import DockerService


class DoctorService:

    def run(self) -> DoctorReport:

        checks = []

        # System check

        system = SystemService().get_info()

        checks.append(
            CheckResult(
                name="Python",
                status="OK",
                message=system.python_version,
            )
        )

        checks.append(
            CheckResult(
                name="Architecture",
                status="OK",
                message=system.architecture,
            )
        )

        # Docker check

        docker = DockerService().get_info()

        checks.append(
            CheckResult(
                name="Docker",
                status="OK",
                message=docker.version,
            )
        )

        checks.append(
            CheckResult(
                name="Containers",
                status="OK",
                message=f"{docker.running}/{docker.total} running",
            )
        )

        # Detect stopped containers

        for container in docker.containers:

            if container.status != "running":

                checks.append(
                    CheckResult(
                        name=container.name,
                        status="WARN",
                        message=container.status,
                    )
                )

        return DoctorReport(
            checks=checks
        )
