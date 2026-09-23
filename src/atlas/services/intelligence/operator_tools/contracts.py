"""
Declarative contracts for ATLAS Intelligence tools.

Concrete tool names and result schemas belong to the tool layer.
AIService must consume these contracts generically.
"""

from copy import deepcopy


_EMPTY_PARAMETERS = {
    "type": "object",
    "properties": {},
    "required": [],
}


TOOL_PARAMETERS = {

    "find_asset": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Asset name or asset identifier."
                ),
            },
        },
        "required": [
            "query",
        ],
    },

    "get_asset_context": {
        "type": "object",
        "properties": {
            "asset_id": {
                "type": "string",
            },
        },
        "required": [
            "asset_id",
        ],
    },

    "list_assets": {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
            },
            "asset_type": {
                "type": "string",
            },
            "criticality": {
                "type": "string",
            },
            "role": {
                "type": "string",
            },
        },
        "required": [],
    },

    "inspect_asset": {
        "type": "object",
        "properties": {
            "asset_id": {
                "type": "string",
            },
        },
        "required": [
            "asset_id",
        ],
    },

    "telemetry_system":
        _EMPTY_PARAMETERS,

    "telemetry_temperatures":
        _EMPTY_PARAMETERS,

    "telemetry_filesystems":
        _EMPTY_PARAMETERS,

    "telemetry_smart": {
        "type": "object",
        "properties": {
            "device": {
                "type": "string",
                "description": (
                    "Optional physical disk device. "
                    "If omitted, inspect available "
                    "physical disks."
                ),
            },
        },
        "required": [],
    },

    "telemetry_proxmox_cpu_temperature":
        _EMPTY_PARAMETERS,

    "telemetry_proxmox_storage":
        _EMPTY_PARAMETERS,

    "telemetry_processes":
        _EMPTY_PARAMETERS,

    "telemetry_network":
        _EMPTY_PARAMETERS,

    "telemetry_path_size": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
            },
        },
        "required": [
            "path",
        ],
    },

    "telemetry_atlas_database_size": {
        "type": "object",
        "properties": {
            "database_path": {
                "type": "string",
                "default": "atlas.db",
            },
        },
        "required": [],
    },

    "atlas_find": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
            },
        },
        "required": [
            "query",
        ],
    },

    "atlas_get_asset": {
        "type": "object",
        "properties": {
            "asset_id": {
                "type": "string",
            },
        },
        "required": [
            "asset_id",
        ],
    },

    "atlas_list_assets": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
            },
            "status": {
                "type": "string",
            },
            "asset_type": {
                "type": "string",
            },
            "criticality": {
                "type": "string",
            },
            "role": {
                "type": "string",
            },
        },
        "required": [],
    },

    "atlas_get_infrastructure":
        _EMPTY_PARAMETERS,

    "atlas_get_topology": {
        "type": "object",
        "properties": {
            "asset_id": {
                "type": "string",
            },
            "direction": {
                "type": "string",
            },
            "depth": {
                "type": "integer",
                "minimum": 1,
            },
        },
        "required": [
            "asset_id",
        ],
    },

    "atlas_get_impact": {
        "type": "object",
        "properties": {
            "asset_id": {
                "type": "string",
            },
            "depth": {
                "type": "integer",
                "minimum": 1,
            },
        },
        "required": [
            "asset_id",
        ],
    },
}


def _compact_proxmox_storage(
    result: dict,
) -> dict:
    """
    Reduce Proxmox storage telemetry without embedding any
    environment-specific device names.
    """

    if not isinstance(
        result,
        dict,
    ):
        return result

    data = result.get(
        "data"
    )

    if not isinstance(
        data,
        dict,
    ):
        return result

    physical_disks = []

    for disk in (
        data.get(
            "physical_disks"
        )
        or []
    ):

        if not isinstance(
            disk,
            dict,
        ):
            continue

        physical_disks.append(
            {
                "device":
                    disk.get(
                        "device"
                    ),
                "size_gb":
                    disk.get(
                        "size_gb"
                    ),
                "model":
                    disk.get(
                        "model"
                    ),
            }
        )

    lvm = (
        data.get(
            "lvm"
        )
        or {}
    )

    thin_pool = (
        data.get(
            "thin_pool"
        )
        or {}
    )

    return {
        "tool":
            result.get(
                "tool"
            ),
        "success":
            result.get(
                "success",
                False,
            ),
        "data": {
            "host":
                data.get(
                    "host"
                ),
            "physical_disks":
                physical_disks,
            "lvm": {
                "physical_volume":
                    lvm.get(
                        "physical_volume"
                    ),
                "volume_group":
                    lvm.get(
                        "volume_group"
                    ),
                "size_gb":
                    lvm.get(
                        "size_gb"
                    ),
                "free_gb":
                    lvm.get(
                        "free_gb"
                    ),
            },
            "thin_pool": {
                "name":
                    thin_pool.get(
                        "name"
                    ),
                "size_gb":
                    thin_pool.get(
                        "size_gb"
                    ),
                "used_percent":
                    thin_pool.get(
                        "used_percent"
                    ),
                "free_gb":
                    thin_pool.get(
                        "free_gb"
                    ),
            },
        },
        "error":
            result.get(
                "error"
            ),
    }


def _compact_cpu_temperature(
    result: dict,
) -> dict:

    if not isinstance(
        result,
        dict,
    ):
        return result

    data = result.get(
        "data"
    )

    if not isinstance(
        data,
        dict,
    ):
        return result

    return {
        "tool":
            result.get(
                "tool"
            ),
        "success":
            result.get(
                "success",
                False,
            ),
        "data": {
            "host":
                data.get(
                    "host"
                ),
            "sensor":
                data.get(
                    "sensor"
                ),
            "temperature_c":
                data.get(
                    "temperature_c"
                ),
        },
        "error":
            result.get(
                "error"
            ),
    }


TOOL_RESULT_COMPACTORS = {

    "telemetry_proxmox_storage":
        _compact_proxmox_storage,

    "telemetry_proxmox_cpu_temperature":
        _compact_cpu_temperature,

}


def get_tool_parameters(
    tool_name: str,
) -> dict:

    return deepcopy(
        TOOL_PARAMETERS.get(
            tool_name,
            _EMPTY_PARAMETERS,
        )
    )


def get_tool_result_compactor(
    tool_name: str,
):

    return TOOL_RESULT_COMPACTORS.get(
        tool_name
    )
