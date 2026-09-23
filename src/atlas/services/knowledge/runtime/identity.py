from dataclasses import dataclass


@dataclass(slots=True)
class RuntimeIdentity:

    container_id: str | None = None

    image: str | None = None

    service_name: str | None = None


    def canonical(self):

        if self.service_name:

            return (
                self.service_name
                .lower()
                .strip()
            )


        if self.image:

            image = (
                self.image
                .split("/")[-1]
                .split(":")[0]
            )

            return (
                image
                .lower()
                .strip()
            )


        if self.container_id:

            return (
                self.container_id
                .lower()
                .strip()
            )


        return None
