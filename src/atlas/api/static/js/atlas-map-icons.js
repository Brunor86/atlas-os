(() => {
    "use strict";

    const definitions = [
        {
            key: "proxmox",
            label: "PVE",
            rx: /\bproxmox\b|atlas · proxmox/i,
        },
        {
            key: "homeassistant",
            label: "HA",
            rx: /home assistant|haos-18\.1/i,
        },
        {
            key: "tailscale",
            label: "TS",
            rx: /\btailscale\b/i,
        },
        {
            key: "docker",
            label: "DK",
            rx: /\bdocker\b|containerd/i,
        },
        {
            key: "debian",
            label: "DE",
            rx: /\bdebian\b|debian-docker/i,
        },
        {
            key: "windows",
            label: "WIN",
            rx: /atlas-windows|\bwindows\b/i,
        },
        {
            key: "grafana",
            label: "GF",
            rx: /\bgrafana\b/i,
        },
        {
            key: "prometheus",
            label: "PR",
            rx: /\bprometheus\b/i,
        },
        {
            key: "prometheus",
            label: "AM",
            rx: /\balertmanager\b/i,
        },
        {
            key: "monitoring",
            label: "CA",
            rx: /\bcadvisor\b|node-exporter/i,
        },
        {
            key: "adguard",
            label: "AG",
            rx: /adguard/i,
        },
        {
            key: "immich",
            label: "IM",
            rx: /\bimmich/i,
        },
        {
            key: "jellyfin",
            label: "JF",
            rx: /\bjellyfin\b/i,
        },
        {
            key: "postgresql",
            label: "PG",
            rx: /\bpostgres(?:ql)?\b/i,
        },
        {
            key: "redis",
            label: "RD",
            rx: /\bredis\b/i,
        },
        {
            key: "mariadb",
            label: "DB",
            rx: /\bmariadb\b|db-aceite/i,
        },
        {
            key: "network",
            label: "PT",
            rx: /\bportainer\b/i,
        },
        {
            key: "network",
            label: "SY",
            rx: /\bsyncthing\b/i,
        },
        {
            key: "media",
            label: "BZ",
            rx: /\bbazarr\b/i,
        },
        {
            key: "media",
            label: "RD",
            rx: /\bradarr\b/i,
        },
        {
            key: "media",
            label: "SN",
            rx: /\bsonarr\b/i,
        },
        {
            key: "system",
            label: "FB",
            rx: /\bfilebrowser\b|file editor/i,
        },
        {
            key: "system",
            label: "FS",
            rx: /\bflaresolverr\b/i,
        },
        {
            key: "network",
            label: "IPD",
            rx: /\bipad-dash\b/i,
        },
        {
            key: "satellite",
            label: "OS",
            rx: /\bolivasat\b/i,
        },
        {
            key: "ai",
            label: "AI",
            rx: /\batlas-ai\b|ollama|machine[_ -]?learning/i,
        },
        {
            key: "satellite",
            label: "SAT",
            rx: /\bstarlink\b|\binternet\b/i,
        },
        {
            key: "camera",
            label: "CAM",
            rx: /ezviz|\bh3c\b|\bh8c\b|camera/i,
        },
        {
            key: "zigbee",
            label: "ZB",
            rx: /zigbee|\bzha\b|zbdongle|monitor homelab/i,
        },
        {
            key: "iot",
            label: "SNF",
            rx: /sonoff|reflector|riego|bomba pres tanque|ewelink/i,
        },
        {
            key: "media",
            label: "TV",
            rx: /crystal uhd|samsungtv|\btelevision\b/i,
        },
        {
            key: "media",
            label: "CAST",
            rx: /chromecast|\bcast\b|comedor/i,
        },
        {
            key: "mobile",
            label: "IOS",
            rx: /iphone|\bapple\b/i,
        },
        {
            key: "mqtt",
            label: "MQ",
            rx: /mosquitto|\bmqtt\b/i,
        },
        {
            key: "backup",
            label: "BK",
            rx: /\bbackup\b/i,
        },
        {
            key: "storage",
            label: "HDD",
            rx: /\bstorage\b|wdc|hard disk|disk/i,
        },
        {
            key: "network",
            label: "NET",
            rx: /local network|lan device|router/i,
        },
        {
            key: "system",
            label: "HC",
            rx: /\bhacs\b/i,
        },
        {
            key: "system",
            label: "SSH",
            rx: /terminal.*ssh|\bssh\b/i,
        },
    ];

    function resolve(
        text
    ) {
        const value =
            String(
                text || ""
            ).trim();

        return (
            definitions.find(
                definition =>
                    definition.rx.test(
                        value
                    )
            )
            || null
        );
    }

    function fallbackForHa(
        card
    ) {
        const category =
            String(
                card.dataset.category
                || card.textContent
                || ""
            ).toLowerCase();

        if (
            category.includes(
                "camera"
            )
        ) {
            return {
                key: "camera",
                label: "CAM",
            };
        }

        if (
            category.includes(
                "zigbee"
            )
        ) {
            return {
                key: "zigbee",
                label: "ZB",
            };
        }

        if (
            category.includes(
                "mobile"
            )
        ) {
            return {
                key: "mobile",
                label: "MOB",
            };
        }

        if (
            category.includes(
                "media"
            )
        ) {
            return {
                key: "media",
                label: "AV",
            };
        }

        if (
            category.includes(
                "network"
            )
        ) {
            return {
                key: "network",
                label: "NET",
            };
        }

        if (
            category.includes(
                "system"
            )
        ) {
            return {
                key: "system",
                label: "SYS",
            };
        }

        return {
            key: "iot",
            label: "DEV",
        };
    }

    function createBadge(
        definition,
        device = false
    ) {
        const badge =
            document.createElement(
                "span"
            );

        badge.className =
            "atlas-service-icon";

        if (device) {
            badge.classList.add(
                "atlas-service-icon--device"
            );
        }

        if (
            String(
                definition.label
            ).length >= 3
        ) {
            badge.classList.add(
                "atlas-service-icon--wide"
            );
        }

        badge.dataset.atlasIcon =
            definition.key;

        badge.textContent =
            definition.label;

        badge.setAttribute(
            "aria-hidden",
            "true"
        );

        return badge;
    }

    function decorateHaDevices() {
        document
            .querySelectorAll(
                ".atlas-ha-device"
            )
            .forEach(
                card => {
                    if (
                        card.dataset
                            .atlasIconified
                        === "1"
                    ) {
                        return;
                    }

                    const holder =
                        card.querySelector(
                            ".atlas-ha-device-icon"
                        );

                    if (!holder) {
                        return;
                    }

                    const definition =
                        resolve(
                            card.textContent
                        )
                        || fallbackForHa(
                            card
                        );

                    holder.textContent =
                        "";

                    holder.appendChild(
                        createBadge(
                            definition,
                            true
                        )
                    );

                    card.dataset
                        .atlasIconified =
                        "1";
                }
            );
    }

    function decorateKnownTitles() {
        document
            .querySelectorAll(
                "strong, h3, h4"
            )
            .forEach(
                title => {
                    if (
                        title.dataset
                            .atlasIconified
                        === "1"
                    ) {
                        return;
                    }

                    /*
                     * Home Assistant physical cards have
                     * their dedicated icon holder.
                     */
                    if (
                        title.closest(
                            ".atlas-ha-device"
                        )
                    ) {
                        return;
                    }

                    const definition =
                        resolve(
                            title.textContent
                        );

                    if (!definition) {
                        return;
                    }

                    title.insertBefore(
                        createBadge(
                            definition
                        ),
                        title.firstChild
                    );

                    title.classList.add(
                        "atlas-service-icon-title"
                    );

                    title.dataset
                        .atlasIconified =
                        "1";
                }
            );
    }

    function decorateNetworkCards() {
        document
            .querySelectorAll(
                ".atlas-network-device"
            )
            .forEach(
                card => {
                    if (
                        card.dataset
                            .atlasNetworkIconified
                        === "1"
                    ) {
                        return;
                    }

                    const title =
                        card.querySelector(
                            "strong"
                        );

                    if (!title) {
                        return;
                    }

                    if (
                        title.dataset
                            .atlasIconified
                        !== "1"
                    ) {
                        const definition =
                            resolve(
                                card.textContent
                            )
                            || {
                                key: "network",
                                label: "LAN",
                            };

                        title.insertBefore(
                            createBadge(
                                definition
                            ),
                            title.firstChild
                        );

                        title.dataset
                            .atlasIconified =
                            "1";
                    }

                    card.dataset
                        .atlasNetworkIconified =
                        "1";
                }
            );
    }

    let scheduled = false;

    function decorate() {
        scheduled = false;

        decorateHaDevices();
        decorateNetworkCards();
        decorateKnownTitles();
    }

    function schedule() {
        if (scheduled) {
            return;
        }

        scheduled = true;

        window.requestAnimationFrame(
            decorate
        );
    }

    const observer =
        new MutationObserver(
            schedule
        );

    observer.observe(
        document.documentElement,
        {
            subtree: true,
            childList: true,
        }
    );

    schedule();
})();
