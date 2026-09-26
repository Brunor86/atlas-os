from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from atlas.storage.asset_repository import (
    AssetRepository,
)


@dataclass(
    frozen=True
)
class OperationTargetResolution:
    status: str
    query: str
    resource_type: str | None = None
    target: str | None = None
    asset_id: str | None = None
    asset_name: str | None = None
    reason: str = ""
    candidates: tuple[str, ...] = ()


class OperationTargetResolver:
    """
    Resolve a human infrastructure name to one canonical
    executable ATLAS target.

    This component is deterministic.

    It does not use an LLM, does not execute infrastructure
    operations and does not grant authorization.

    Only ACTIVE assets are eligible.

    Resolution contract:

        human name
            ->
        Asset Registry
            ->
        exactly one supported ACTIVE asset
            ->
        canonical resource type + execution target

    Ambiguous or unknown names fail closed.
    """

    def __init__(
        self,
        repository=None,
    ):
        self.repository = (
            repository
            or AssetRepository()
        )


    @staticmethod
    def _normalize(
        value,
    ) -> str:

        normalized = (
            unicodedata.normalize(
                "NFKD",
                str(
                    value
                    or ""
                ).casefold(),
            )
        )

        normalized = "".join(
            character
            for character in normalized
            if not unicodedata.combining(
                character
            )
        )

        normalized = re.sub(
            r"[\s_]+",
            "-",
            normalized,
        )

        return normalized.strip(
            " -"
        )


    @staticmethod
    def _resource_type(
        asset,
    ) -> str | None:

        asset_type = str(
            getattr(
                getattr(
                    asset,
                    "type",
                    None,
                ),
                "name",
                "",
            )
            or ""
        ).upper()

        identity = getattr(
            asset,
            "identity",
            None,
        )

        vendor = str(
            getattr(
                identity,
                "vendor",
                "",
            )
            or ""
        ).casefold()

        model = str(
            getattr(
                identity,
                "model",
                "",
            )
            or ""
        ).casefold()


        if (
            asset_type == "APPLICATION"
            and vendor == "docker"
        ):
            return "container"


        if (
            asset_type == "SERVICE"
            and model == "systemd service"
        ):
            return "service"


        if (
            asset_type == "VM"
            and vendor == "proxmox"
        ):
            return "vm"


        if (
            asset_type == "LXC"
            and vendor == "proxmox"
        ):
            return "lxc"


        return None


    def _aliases(
        self,
        asset,
        resource_type,
    ) -> set[str]:

        identity = getattr(
            asset,
            "identity",
            None,
        )

        aliases = {
            self._normalize(
                getattr(
                    asset,
                    "name",
                    "",
                )
            ),
            self._normalize(
                getattr(
                    identity,
                    "serial",
                    "",
                )
            ),
        }

        aliases.discard(
            ""
        )


        if (
            resource_type == "service"
        ):

            name = self._normalize(
                getattr(
                    asset,
                    "name",
                    "",
                )
            )

            if name.endswith(
                ".service"
            ):
                aliases.add(
                    name[:-8]
                )


        return aliases


    @staticmethod
    def _canonical_target(
        asset,
        resource_type,
    ) -> str:

        identity = getattr(
            asset,
            "identity",
            None,
        )

        metadata = getattr(
            asset,
            "metadata",
            {},
        ) or {}


        if resource_type in (
            "vm",
            "lxc",
        ):

            return str(
                metadata.get(
                    "proxmox_vmid"
                )
                or getattr(
                    identity,
                    "serial",
                    "",
                )
                or ""
            ).strip()


        if resource_type == "container":

            return str(
                getattr(
                    identity,
                    "serial",
                    "",
                )
                or getattr(
                    asset,
                    "name",
                    "",
                )
                or ""
            ).strip()


        if resource_type == "service":

            return str(
                getattr(
                    asset,
                    "name",
                    "",
                )
                or ""
            ).strip()


        return ""


    def resolve(
        self,
        query,
        *,
        requested_resource_type=None,
    ) -> OperationTargetResolution:

        raw_query = str(
            query
            or ""
        ).strip()

        normalized_query = (
            self._normalize(
                raw_query
            )
        )

        requested_type = str(
            requested_resource_type
            or ""
        ).strip().lower() or None


        if not normalized_query:

            return OperationTargetResolution(
                status="NOT_FOUND",
                query=raw_query,
                reason="operation target is empty",
            )


        all_matches = []


        for asset in (
            self.repository
            .get_all_assets()
        ):

            presence = str(
                getattr(
                    getattr(
                        asset,
                        "presence",
                        None,
                    ),
                    "name",
                    "",
                )
                or ""
            ).upper()

            if presence != "ACTIVE":
                continue


            resource_type = (
                self._resource_type(
                    asset
                )
            )

            if resource_type is None:
                continue


            if (
                normalized_query
                not in self._aliases(
                    asset,
                    resource_type,
                )
            ):
                continue


            all_matches.append(
                (
                    asset,
                    resource_type,
                )
            )


        if not all_matches:

            return OperationTargetResolution(
                status="NOT_FOUND",
                query=raw_query,
                reason=(
                    "no active executable asset "
                    "matches target"
                ),
            )


        if requested_type:

            typed_matches = [
                item
                for item in all_matches
                if item[1]
                == requested_type
            ]

            if not typed_matches:

                actual_types = tuple(
                    sorted(
                        {
                            item[1]
                            for item
                            in all_matches
                        }
                    )
                )

                return OperationTargetResolution(
                    status="TYPE_MISMATCH",
                    query=raw_query,
                    reason=(
                        "target exists but does not "
                        "match requested resource type"
                    ),
                    candidates=actual_types,
                )

            all_matches = typed_matches


        unique = {}

        for asset, resource_type in all_matches:

            unique[
                str(
                    getattr(
                        asset,
                        "id",
                        "",
                    )
                )
            ] = (
                asset,
                resource_type,
            )


        matches = list(
            unique.values()
        )


        if len(matches) != 1:

            names = tuple(
                sorted(
                    str(
                        getattr(
                            asset,
                            "name",
                            "",
                        )
                    )
                    for asset, _
                    in matches
                )
            )

            return OperationTargetResolution(
                status="AMBIGUOUS",
                query=raw_query,
                reason=(
                    "operation target matches "
                    "multiple active assets"
                ),
                candidates=names,
            )


        asset, resource_type = (
            matches[0]
        )

        canonical_target = (
            self._canonical_target(
                asset,
                resource_type,
            )
        )


        if not canonical_target:

            return OperationTargetResolution(
                status="NOT_FOUND",
                query=raw_query,
                reason=(
                    "matched asset has no "
                    "canonical execution target"
                ),
            )


        return OperationTargetResolution(
            status="RESOLVED",
            query=raw_query,
            resource_type=resource_type,
            target=canonical_target,
            asset_id=str(
                getattr(
                    asset,
                    "id",
                    "",
                )
            ),
            asset_name=str(
                getattr(
                    asset,
                    "name",
                    "",
                )
            ),
            reason=(
                "resolved from active "
                "ATLAS asset registry"
            ),
        )
