from dataclasses import dataclass


@dataclass(slots=True)
class AssetIdentity:
    """
    Stable identity of an infrastructure asset.

    This data should not change during the asset lifetime.
    """

    serial: str | None = None
    model: str | None = None
    vendor: str | None = None
    firmware: str | None = None
    device: str | None = None


    def __post_init__(self) -> None:
        """Normalize identity values at the domain boundary.

        Providers such as Proxmox may return numeric or otherwise
        non-string values for fields that form part of an asset identity.
        Normalize them once so all downstream identity operations can
        safely assume strings or None.
        """

        for field_name in (
            "serial",
            "model",
            "vendor",
            "firmware",
            "device",
        ):
            value = getattr(self, field_name)

            if value is not None:
                setattr(
                    self,
                    field_name,
                    str(value),
                )


    def fingerprint(self) -> str:
        """
        Generate stable fingerprint for asset matching.
        """


        parts = []


        vendor = (
            self.vendor.strip()
            if self.vendor
            else None
        )


        model = (
            self.model.strip()
            if self.model
            else None
        )


        serial = (
            self.serial.strip()
            if self.serial
            else None
        )


        if vendor:
            parts.append(vendor)


        if model:

            if (
                vendor
                and model.lower().startswith(
                    vendor.lower()
                )
            ):
                model = model[
                    len(vendor):
                ].strip()


            parts.append(model)


        if serial:
            parts.append(serial)


        normalized_parts = []


        for part in parts:

            value = (
                part
                .lower()
                .strip()
                .replace(" ", "_")
                .replace("/", "_")
            )


            while "__" in value:

                value = value.replace(
                    "__",
                    "_"
                )


            value = value.strip("_")


            if value:
                normalized_parts.append(
                    value
                )


        return "-".join(
            normalized_parts
        )
