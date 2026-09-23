from pathlib import Path

from atlas.services.telemetry import TelemetryService


def test_system_returns_cpu_and_memory():

    service = TelemetryService()

    result = service.system()

    assert "cpu" in result
    assert "memory" in result
    assert "logical_cores" in result["cpu"]
    assert "physical_cores" in result["cpu"]


def test_temperatures_returns_list():

    service = TelemetryService()

    result = service.temperatures()

    assert isinstance(
        result,
        list,
    )


def test_filesystems_returns_list():

    service = TelemetryService()

    result = service.filesystems()

    assert isinstance(
        result,
        list,
    )


def test_block_devices_returns_list():

    service = TelemetryService()

    result = service.block_devices()

    assert isinstance(
        result,
        list,
    )


def test_network_interfaces_returns_list():

    service = TelemetryService()

    result = service.network_interfaces()

    assert isinstance(
        result,
        list,
    )


def test_processes_returns_limited_list():

    service = TelemetryService()

    result = service.processes(
        limit=5
    )

    assert isinstance(
        result,
        list,
    )

    assert len(result) <= 5


def test_path_size(tmp_path: Path):

    test_file = (
        tmp_path /
        "test.bin"
    )

    test_file.write_bytes(
        b"x" * 1024
    )

    service = TelemetryService()

    result = service.path_size(
        str(test_file)
    )

    assert result["bytes"] == 1024
    assert result["mb"] > 0


def test_snapshot_contains_core_sections():

    service = TelemetryService()

    result = service.snapshot()

    assert "system" in result
    assert "temperatures" in result
    assert "filesystems" in result
    assert "block_devices" in result
    assert "smart" in result
    assert "network_interfaces" in result
    assert "processes" in result

def test_network_connections_returns_list():

    service = TelemetryService()

    result = service.network_connections(
        limit=5
    )

    assert isinstance(
        result,
        list,
    )

    assert len(result) <= 5


def test_prometheus_query_requires_expression():

    service = TelemetryService()

    try:
        service.prometheus_query("")
    except ValueError as exc:
        assert str(exc) == "expression is required"
    else:
        raise AssertionError(
            "expected ValueError"
        )


def test_snapshot_contains_network_connections():

    service = TelemetryService()

    result = service.snapshot()

    assert "network_connections" in result
    assert isinstance(
        result["network_connections"],
        list,
    )
