from .identity import AssetIdentity


def generate_asset_id(
    asset_type: str,
    identity: AssetIdentity
) -> str:

    fingerprint = identity.fingerprint()

    if fingerprint:
        return f"{asset_type.lower()}-{fingerprint}"

    return f"{asset_type.lower()}-unknown"
