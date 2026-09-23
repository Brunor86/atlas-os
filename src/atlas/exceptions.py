class AtlasError(Exception):
    """Excepción base del proyecto."""


class ServiceError(AtlasError):
    """Error de un servicio."""


class DockerError(ServiceError):
    """Errores relacionados con Docker."""
