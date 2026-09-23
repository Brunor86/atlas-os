import logging

from atlas.storage.asset_repository import AssetRepository


logger = logging.getLogger(__name__)


class AssetPersistenceService:

    def __init__(self):
        self.repository = AssetRepository()

        #
        # Observations already persisted by this service instance.
        #
        # Persistence of assets is idempotent.
        # Persistence of observations is append-only.
        #
        self._persisted_observations = set()


    def persist(self, asset):

        existing = self.repository.find_by_identity(
            asset.identity
        )

        if existing:
            asset.id = existing

        #
        # Persist asset with roles/capabilities/metadata
        #

        self.repository.save_asset(asset)


        #
        # Verify role persistence
        #

        if asset.asset_roles:

            logger.debug(
                "Asset roles persisted asset=%s roles=%s",
                asset.name,
                sorted(
                    role.name
                    for role
                    in asset.asset_roles
                ),
            )


        #
        # Observations
        #
        # Do not use asset.observations[-1:] here.
        #
        # A discovery cycle may call persist() more than once for the
        # same runtime asset. Asset state is idempotent, while
        # observations represent historical events and must be
        # appended only when they are genuinely new.
        #

        for observation in asset.observations:

            observation_key = (
                observation.asset_id,
                observation.type,
                observation.severity,
                observation.source,
                observation.timestamp.isoformat(),
                repr(observation.value),
            )

            if observation_key in self._persisted_observations:
                continue

            self.repository.save_observation(
                observation
            )

            self._persisted_observations.add(
                observation_key
            )
