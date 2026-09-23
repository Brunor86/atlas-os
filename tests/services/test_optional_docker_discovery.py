import pytest


@pytest.mark.parametrize(
    (
        "docker_cli",
        "socket_present",
        "expected",
    ),
    [
        (
            None,
            False,
            False,
        ),
        (
            "/usr/bin/docker",
            False,
            True,
        ),
        (
            None,
            True,
            True,
        ),
        (
            "/usr/bin/docker",
            True,
            True,
        ),
    ],
)
def test_docker_provider_configuration_detection(
    monkeypatch,
    docker_cli,
    socket_present,
    expected,
):

    import atlas.providers.docker as module


    monkeypatch.setattr(
        module.shutil,
        "which",
        lambda name:
            docker_cli,
    )

    monkeypatch.setattr(
        module.os.path,
        "exists",
        lambda path:
            socket_present,
    )


    assert (
        module.DockerAssetProvider
        .is_configured()
        is expected
    )


def test_docker_provider_constructor_does_not_connect(
    monkeypatch,
):

    import atlas.providers.docker as module


    def unavailable():

        raise RuntimeError(
            "synthetic Docker connection"
        )


    monkeypatch.setattr(
        module,
        "DockerService",
        unavailable,
    )


    provider = (
        module.DockerAssetProvider()
    )


    assert provider.service is None


    with pytest.raises(
        RuntimeError,
        match="synthetic Docker connection",
    ):

        provider.collect()


def test_discovery_kernel_omits_unconfigured_docker(
    monkeypatch,
):

    import atlas.services.discovery.kernel as module


    monkeypatch.setattr(
        module.DockerAssetProvider,
        "is_configured",
        staticmethod(
            lambda:
                False
        ),
    )


    kernel = (
        module.DiscoveryKernel()
    )


    assert not any(
        isinstance(
            provider,
            module.DockerAssetProvider,
        )

        for provider
        in kernel.providers
    )


def test_discovery_kernel_keeps_configured_docker_lazy(
    monkeypatch,
):

    import atlas.services.discovery.kernel as module


    monkeypatch.setattr(
        module.DockerAssetProvider,
        "is_configured",
        staticmethod(
            lambda:
                True
        ),
    )


    kernel = (
        module.DiscoveryKernel()
    )


    docker_providers = [
        provider
        for provider
        in kernel.providers
        if isinstance(
            provider,
            module.DockerAssetProvider,
        )
    ]


    assert len(
        docker_providers
    ) == 1

    assert (
        docker_providers[0].service
        is None
    )


def test_discovery_kernel_skips_unconfigured_proxmox(
    monkeypatch,
):

    import atlas.services.discovery.kernel as module

    monkeypatch.setattr(
        module,
        "is_proxmox_configured",
        lambda:
            False,
        raising=False,
    )

    kernel = module.DiscoveryKernel()

    kernel.providers = []

    monkeypatch.setattr(
        kernel,
        "_discover_proxmox",
        lambda:
            (_ for _ in ()).throw(
                AssertionError(
                    "unconfigured Proxmox must be skipped"
                )
            ),
    )

    monkeypatch.setattr(
        kernel,
        "_discover_host_services",
        lambda:
            [],
    )

    monkeypatch.setattr(
        kernel.role_inference,
        "infer",
        lambda assets:
            assets,
    )

    monkeypatch.setattr(
        kernel.graph_builder,
        "build",
        lambda assets:
            [],
    )

    monkeypatch.setattr(
        kernel.dependency_builder,
        "build",
        lambda assets:
            [],
    )

    monkeypatch.setattr(
        kernel.graph_service,
        "persist",
        lambda relationships:
            None,
    )

    result = kernel.discover()

    assert result.complete is True
    assert result.errors == []
