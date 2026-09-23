from datetime import (
    UTC,
    datetime,
    timedelta,
)

from atlas.core.asset import (
    AssetPresence,
)

from atlas.storage.asset_repository import (
    AssetRepository,
)


class AssetReconciliationService:
    """
    Reconcile authoritative Discovery with persistent inventory.

    This service must only be called after a complete Discovery.

    It never deletes assets.

    Lifecycle:

        discovered -> ACTIVE

        missing ACTIVE
            -> STALE

        missing STALE and presence state older than retirement window
            -> RETIRED

        rediscovered STALE / RETIRED
            -> ACTIVE
    """

    def __init__(
        self,
        repository=None,
        retire_after=None,
        clock=None,
    ):

        self.repository = (
            repository
            or AssetRepository()
        )

        self.retire_after = (
            retire_after
            or timedelta(
                days=7
            )
        )

        self.clock = (
            clock
            or (
                lambda:
                    datetime.now(UTC)
            )
        )


    def reconcile(
        self,
        discovered_assets,
    ):

        now = self.clock()

        discovered_ids = {
            asset.id
            for asset
            in discovered_assets
        }

        persisted_assets = (
            self.repository
            .get_all_assets()
        )

        transitions = []


        for asset in persisted_assets:

            target = None
            reason = None


            #
            # Seen again.
            #
            if (
                asset.id
                in discovered_ids
            ):

                if (
                    asset.presence
                    != AssetPresence.ACTIVE
                ):

                    target = (
                        AssetPresence.ACTIVE
                    )

                    reason = (
                        "rediscovered in complete "
                        "inventory"
                    )


            #
            # Missing from a complete inventory.
            #
            else:

                if (
                    asset.presence
                    == AssetPresence.ACTIVE
                ):

                    target = (
                        AssetPresence.STALE
                    )

                    reason = (
                        "missing from complete "
                        "inventory"
                    )


                elif (
                    asset.presence
                    == AssetPresence.STALE
                ):

                    stale_since = (
                        asset.presence_changed_at
                    )

                    #
                    # The retirement grace period starts when ATLAS
                    # authoritatively marks the asset STALE, not from
                    # the asset's historical last_seen timestamp.
                    #
                    # presence_changed_at is populated by migrations
                    # and every presence transition. The fallback is
                    # conservative for malformed legacy rows: do not
                    # retire until a valid presence timestamp exists.
                    #
                    if stale_since is None:
                        continue

                    if (
                        stale_since.tzinfo
                        is None
                    ):

                        stale_since = (
                            stale_since.replace(
                                tzinfo=UTC
                            )
                        )

                    age = (
                        now
                        - stale_since
                    )

                    if (
                        age
                        >= self.retire_after
                    ):

                        target = (
                            AssetPresence.RETIRED
                        )

                        reason = (
                            "missing beyond retirement "
                            "window"
                        )


            if target is None:
                continue


            changed = (
                self.repository
                .set_presence(
                    asset.id,
                    target,
                    reason=reason,
                    changed_at=now,
                )
            )


            if changed:

                transitions.append(
                    {
                        "asset_id":
                            asset.id,

                        "from":
                            asset.presence.name,

                        "to":
                            target.name,

                        "reason":
                            reason,
                    }
                )


        final_assets = (
            self.repository
            .get_all_assets()
        )

        counts = {
            presence.name: 0
            for presence
            in AssetPresence
        }

        for asset in final_assets:

            counts[
                asset.presence.name
            ] += 1


        return {
            "discovered":
                len(discovered_ids),

            "persisted":
                len(final_assets),

            "counts":
                counts,

            "transitions":
                transitions,
        }
