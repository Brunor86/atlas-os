from atlas.core.docker_roles import DockerRole


class DockerRoleEngine:

    def detect(self, name: str, image: str):

        value = " ".join(
            part
            for part in (
                name,
                image,
            )
            if part
        ).lower()

        # Runtime/provider metadata should eventually populate
        # semantic roles. This engine intentionally performs no
        # application-name lookup.
        #
        # Generic semantic signals are used only when the image
        # itself exposes a meaningful category.

        categories = {
            "database": DockerRole.DATABASE,
            "postgresql": DockerRole.DATABASE,
            "mysql": DockerRole.DATABASE,
            "cache": DockerRole.UNKNOWN,
            "monitoring": DockerRole.MONITORING,
            "observability": DockerRole.MONITORING,
            "proxy": DockerRole.REVERSE_PROXY,
            "reverse-proxy": DockerRole.REVERSE_PROXY,
            "media": DockerRole.MEDIA_SERVER,
            "streaming": DockerRole.MEDIA_SERVER,
            "smart-home": DockerRole.SMART_HOME,
            "automation": DockerRole.SMART_HOME,
        }

        for token, role in categories.items():

            if token in value:
                return role

        return DockerRole.UNKNOWN
