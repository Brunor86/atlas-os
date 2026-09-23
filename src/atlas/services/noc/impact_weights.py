RELATION_WEIGHTS = {

    "RUNS": 20,

    "DEPENDS_ON": 30,

    "MONITORS": 10,

    "PROVIDES": 50,

    "HOSTS": 5,

}


ASSET_MULTIPLIERS = {

    "SERVER": 5,

    "VM": 4,

    "LXC": 3,

    "SERVICE": 2,

    "APPLICATION": 1,

    "STORAGE": 5,

    "DATABASE": 4,

    "NETWORK": 5,

}


def relationship_weight(name: str) -> int:

    return RELATION_WEIGHTS.get(
        name,
        1,
    )


def asset_multiplier(asset_type: str) -> int:

    return ASSET_MULTIPLIERS.get(
        asset_type,
        1,
    )
