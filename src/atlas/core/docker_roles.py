
from enum import Enum


class DockerRole(str, Enum):

    UNKNOWN = "unknown"

    REVERSE_PROXY = "reverse_proxy"

    MEDIA_SERVER = "media_server"

    DATABASE = "database"

    MONITORING = "monitoring"

    AUTOMATION = "automation"

    DOWNLOAD = "download"

    CLOUD = "cloud"

    SMART_HOME = "smart_home"

    SECURITY = "security"
