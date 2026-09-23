from atlas.core.observation import Observation


obs = Observation(
    type="temperature",
    value=40,
    severity="WARNING",
    source="smart",
)


print(obs)

