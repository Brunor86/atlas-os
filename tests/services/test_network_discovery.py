from atlas.services.assets.network_discovery import (
    LocalNetworkDiscoveryService,
)


def test_network_snapshot_preserves_real_addresses(
    monkeypatch,
):
    service = (
        LocalNetworkDiscoveryService()
    )

    monkeypatch.setattr(
        service,
        "_network_context",
        lambda: {
            "interface": "ens18",
            "gateway": "192.168.1.1",
            "local_ip": "192.168.1.208",
            "local_mac": "aa:bb:cc:dd:ee:ff",
            "cidr": "192.168.1.208/24",
        },
    )

    monkeypatch.setattr(
        service,
        "_neighbor_rows",
        lambda interface: [
            {
                "dst": "192.168.1.1",
                "lladdr": "11:22:33:44:55:66",
                "state": ["REACHABLE"],
            },
            {
                "dst": "192.168.1.86",
                "lladdr": "22:33:44:55:66:77",
                "state": ["STALE"],
            },
            {
                "dst": "192.168.1.254",
                "state": ["FAILED"],
            },
        ],
    )

    monkeypatch.setattr(
        service,
        "_known_names",
        lambda context: {
            "192.168.1.1": "Starlink router",
            "192.168.1.86": "atlas · Proxmox",
        },
    )

    monkeypatch.setattr(
        service,
        "_reverse_name",
        lambda address: None,
    )

    result = service.snapshot(
        active_scan=False
    )

    assert result["status"] == "SUCCESS"

    assert (
        result["gateway"]["ip"]
        == "192.168.1.1"
    )

    ips = {
        item["ip"]
        for item
        in result["devices"]
    }

    assert "192.168.1.86" in ips
    assert "192.168.1.208" in ips
    assert "192.168.1.254" not in ips


def test_network_snapshot_is_read_only_when_scan_disabled(
    monkeypatch,
):
    service = (
        LocalNetworkDiscoveryService()
    )

    monkeypatch.setattr(
        service,
        "_network_context",
        lambda: {
            "interface": "ens18",
            "gateway": "192.168.1.1",
            "local_ip": "192.168.1.208",
            "local_mac": None,
            "cidr": "192.168.1.208/24",
        },
    )

    monkeypatch.setattr(
        service,
        "_neighbor_rows",
        lambda interface: [],
    )

    monkeypatch.setattr(
        service,
        "_known_names",
        lambda context: {},
    )

    called = []

    monkeypatch.setattr(
        service,
        "_probe_network",
        lambda *args: called.append(
            args
        ),
    )

    result = service.snapshot(
        active_scan=False
    )

    assert result["status"] == "SUCCESS"
    assert called == []
