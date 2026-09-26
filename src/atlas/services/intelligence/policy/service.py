from atlas.core.asset import (
    AssetPresence,
    AssetType,
    Capability,
    Criticality,
    ServiceImportance,
)


_ACTION_CAPABILITIES = {
    "start container":
        Capability.START,

    "stop container":
        Capability.STOP,

    "restart container":
        Capability.RESTART,

    "start service":
        Capability.START,

    "stop service":
        Capability.STOP,

    "restart service":
        Capability.RESTART,

    "start vm":
        Capability.START,

    "stop vm":
        Capability.STOP,

    "restart vm":
        Capability.RESTART,

    "start lxc":
        Capability.START,

    "stop lxc":
        Capability.STOP,

    "restart lxc":
        Capability.RESTART,
}


_ACTION_ASSET_TYPES = {
    "start container": {
        AssetType.APPLICATION,
        AssetType.CONTAINER,
    },

    "stop container": {
        AssetType.APPLICATION,
        AssetType.CONTAINER,
    },

    "restart container": {
        AssetType.APPLICATION,
        AssetType.CONTAINER,
    },

    "start service": {
        AssetType.SERVICE,
    },

    "stop service": {
        AssetType.SERVICE,
    },

    "restart service": {
        AssetType.SERVICE,
    },

    "start vm": {
        AssetType.VM,
    },

    "stop vm": {
        AssetType.VM,
    },

    "restart vm": {
        AssetType.VM,
    },

    "start lxc": {
        AssetType.LXC,
    },

    "stop lxc": {
        AssetType.LXC,
    },

    "restart lxc": {
        AssetType.LXC,
    },
}


_DISRUPTIVE_ACTIONS = {
    "stop container",
    "restart container",

    "stop service",
    "restart service",

    "stop vm",
    "restart vm",

    "stop lxc",
    "restart lxc",
}


_PROTECTED_CRITICALITY = {
    Criticality.HIGH,
    Criticality.CRITICAL,
}


_PROTECTED_IMPORTANCE = {
    ServiceImportance.IMPORTANT,
    ServiceImportance.CRITICAL,
}


class ActionPolicyService:

    def evaluate(
        self,
        safe_action,
        asset,
    ) -> dict:

        action = str(
            getattr(
                safe_action,
                "action",
                "",
            )
            or ""
        ).strip().lower()

        target = str(
            getattr(
                safe_action,
                "target",
                "",
            )
            or ""
        ).strip()


        if asset is None:

            return {
                "status":
                    "BLOCKED",

                "reason":
                    (
                        "target is not registered "
                        "in ATLAS asset registry"
                    ),

                "action":
                    action,

                "target":
                    target,
            }


        #
        # Historical inventory is never an operational target.
        #
        # STALE means ATLAS no longer has authoritative evidence
        # that the asset is currently present. RETIRED is retained
        # only for history/audit.
        #
        presence = getattr(
            asset,
            "presence",
            AssetPresence.ACTIVE,
        )

        if (
            presence
            != AssetPresence.ACTIVE
        ):

            return {
                "status":
                    "BLOCKED",

                "reason":
                    (
                        "asset is not active "
                        "in ATLAS inventory"
                    ),

                "action":
                    action,

                "target":
                    target,

                "asset_id":
                    asset.id,

                "presence":
                    presence.name,
            }


        required_capability = (
            _ACTION_CAPABILITIES.get(
                action
            )
        )


        if required_capability is None:

            return {
                "status":
                    "BLOCKED",

                "reason":
                    (
                        "action is not supported "
                        "by operator policy"
                    ),

                "action":
                    action,

                "target":
                    target,

                "asset_id":
                    asset.id,
            }


        expected_types = (
            _ACTION_ASSET_TYPES.get(
                action,
                set(),
            )
        )


        if (
            expected_types
            and asset.type
            not in expected_types
        ):

            return {
                "status":
                    "BLOCKED",

                "reason":
                    (
                        "action does not match "
                        "registered asset type"
                    ),

                "action":
                    action,

                "target":
                    target,

                "asset_id":
                    asset.id,

                "asset_type":
                    asset.type.name,
            }


        if not asset.can(
            required_capability
        ):

            return {
                "status":
                    "BLOCKED",

                "reason":
                    (
                        "asset does not expose "
                        f"{required_capability.name} "
                        "capability"
                    ),

                "action":
                    action,

                "target":
                    target,

                "asset_id":
                    asset.id,

                "required_capability":
                    required_capability.name,
            }


        protected = (
            asset.criticality
            in _PROTECTED_CRITICALITY

            or

            asset.service_importance
            in _PROTECTED_IMPORTANCE
        )


        if (
            action
            in _DISRUPTIVE_ACTIONS
            and protected
        ):

            return {
                "status":
                    "BLOCKED",

                "reason":
                    (
                        "disruptive action is blocked "
                        "for protected asset"
                    ),

                "action":
                    action,

                "target":
                    target,

                "asset_id":
                    asset.id,

                "criticality":
                    asset.criticality.name,

                "service_importance":
                    asset.service_importance.name,

                "required_capability":
                    required_capability.name,
            }


        return {
            "status":
                "ALLOWED",

            "action":
                action,

            "target":
                target,

            "asset_id":
                asset.id,

            "criticality":
                asset.criticality.name,

            "service_importance":
                asset.service_importance.name,

            "required_capability":
                required_capability.name,
        }
