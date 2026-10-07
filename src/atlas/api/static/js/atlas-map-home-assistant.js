(() => {
    "use strict";

    const root =
        document.getElementById(
            "atlasPremiumHomeAssistant"
        );

    if (!root) {
        return;
    }

    const state = {
        payload: null,
        selected: null,
        network:
            window.atlasMapNetworkSnapshot
            || null,
    };

    const esc = value =>
        String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");

    function cssValue(value) {
        return String(
            value || ""
        )
            .toLowerCase()
            .replaceAll(" ", "-")
            .replaceAll("/", "-");
    }

    function iconFor(device) {
        switch (device.category) {
            case "Camera":
                return "◉";

            case "Zigbee":
                return "⌁";

            case "IoT":
                return "◆";

            case "Media":
                return "▣";

            case "Mobile":
                return "▯";

            case "Network":
                return "●";

            case "System":
                return "⚙";

            default:
                return "◇";
        }
    }

    function networkIp(device) {
        if (device.ip) {
            return device.ip;
        }

        const snapshot =
            state.network;

        if (
            !snapshot
            || !device.mac
        ) {
            return null;
        }

        const mac =
            device.mac.toLowerCase();

        const match =
            (
                snapshot.devices
                || []
            ).find(
                item =>
                    item.mac
                    && item.mac
                        .toLowerCase()
                    === mac
            );

        return (
            match?.ip
            || null
        );
    }

    function card(device) {
        const ip =
            networkIp(device);

        const status =
            String(
                device.status
                || "UNKNOWN"
            ).toLowerCase();

        const integrations =
            (
                device.integrations
                || []
            ).join(", ");

        return `
            <article
                class="
                    atlas-ha-device
                    ${esc(cssValue(device.category))}
                    ${esc(status)}
                "
                data-ha-device-id="${esc(device.id)}"
            >

                <div class="atlas-ha-device-head">

                    <div class="atlas-ha-device-icon">
                        ${esc(iconFor(device))}
                    </div>

                    <div class="atlas-ha-device-name">

                        <strong>
                            ${esc(device.name)}
                        </strong>

                        <small>
                            ${
                                esc(
                                    device.manufacturer
                                    || "Unknown manufacturer"
                                )
                            }
                            ${
                                device.model
                                    ? ` · ${esc(device.model)}`
                                    : ""
                            }
                        </small>

                    </div>

                    <span
                        class="atlas-ha-status ${esc(status)}"
                    ></span>

                </div>

                <div class="atlas-ha-badges">

                    <span class="atlas-ha-badge">
                        ${esc(device.protocol)}
                    </span>

                    <span class="atlas-ha-badge">
                        ${esc(device.category)}
                    </span>

                    ${
                        integrations
                            ? `
                                <span class="atlas-ha-badge">
                                    ${esc(integrations)}
                                </span>
                            `
                            : ""
                    }

                </div>

                <div class="atlas-ha-addresses">

                    ${
                        ip
                            ? `
                                <div class="atlas-ha-address">
                                    IP ${esc(ip)}
                                </div>
                            `
                            : ""
                    }

                    ${
                        device.mac
                            ? `
                                <div class="atlas-ha-address">
                                    MAC ${esc(device.mac)}
                                </div>
                            `
                            : ""
                    }

                    ${
                        device.ieee
                            ? `
                                <div class="atlas-ha-address ieee">
                                    IEEE ${esc(device.ieee)}
                                </div>
                            `
                            : ""
                    }

                </div>

                <div class="atlas-ha-device-foot">

                    <span>
                        ${esc(device.entity_count)}
                        entities
                    </span>

                    <span>
                        ${
                            device.unavailable_count
                                ? `${esc(device.unavailable_count)} unavailable`
                                : "healthy"
                        }
                    </span>

                </div>

            </article>
        `;
    }

    function groupPhysical(
        devices
    ) {
        const groups =
            new Map();

        for (const device of devices) {
            const area =
                device.area
                || "Unassigned";

            if (!groups.has(area)) {
                groups.set(
                    area,
                    []
                );
            }

            groups
                .get(area)
                .push(device);
        }

        return [
            ...groups.entries()
        ].sort(
            ([a], [b]) => {
                if (
                    a === "Unassigned"
                ) {
                    return 1;
                }

                if (
                    b === "Unassigned"
                ) {
                    return -1;
                }

                return a.localeCompare(
                    b
                );
            }
        );
    }

    function render() {
        if (!state.payload) {
            return;
        }

        const data =
            state.payload;

        const summary =
            data.summary
            || {};

        const physical =
            (
                data.devices
                || []
            ).filter(
                device =>
                    !device.system
            );

        const system =
            (
                data.devices
                || []
            ).filter(
                device =>
                    device.system
            );

        const groups =
            groupPhysical(
                physical
            );

        root.innerHTML = `
            <div class="atlas-ha-heading">

                <div class="atlas-ha-title">

                    <div class="atlas-ha-logo">
                        ⌂
                    </div>

                    <div>
                        <h3>
                            Home Assistant
                        </h3>

                        <p>
                            ${esc(
                                data.instance?.host
                                || "homeassistant"
                            )}
                            · devices, entities,
                            rooms and integrations
                        </p>
                    </div>

                </div>

                <div class="atlas-ha-summary">

                    <div>
                        <strong>
                            ${esc(summary.physical_devices ?? summary.devices ?? 0)}
                        </strong>
                        <small>Home devices</small>
                    </div>

                    <div>
                        <strong>
                            ${esc(summary.zigbee_devices ?? 0)}
                        </strong>
                        <small>Zigbee</small>
                    </div>

                    <div>
                        <strong>
                            ${esc(summary.camera_devices ?? 0)}
                        </strong>
                        <small>Cameras</small>
                    </div>

                    <div>
                        <strong>
                            ${esc(summary.areas ?? 0)}
                        </strong>
                        <small>Areas</small>
                    </div>

                </div>

            </div>

            ${
                groups
                    .map(
                        ([area, devices]) => `
                            <section class="atlas-ha-area">

                                <div class="atlas-ha-area-heading">
                                    <strong>
                                        ${esc(area)}
                                    </strong>

                                    <span>
                                        ${esc(devices.length)}
                                        devices
                                    </span>
                                </div>

                                <div class="atlas-ha-device-grid">
                                    ${
                                        devices
                                            .map(card)
                                            .join("")
                                    }
                                </div>

                            </section>
                        `
                    )
                    .join("")
            }

            <section class="atlas-ha-system">

                <div class="atlas-ha-system-heading">

                    <strong>
                        Home Assistant System
                    </strong>

                    <span>
                        ${esc(system.length)}
                        software / internal devices
                    </span>

                </div>

                <div class="atlas-ha-device-grid">
                    ${
                        system
                            .map(card)
                            .join("")
                    }
                </div>

            </section>

            <div
                class="atlas-ha-detail"
                id="atlasHADeviceDetail"
                hidden
            ></div>
        `;

        if (state.selected) {
            showDetail(
                state.selected
            );
        }
    }

    function showDetail(id) {
        const device =
            (
                state.payload
                ?.devices
                || []
            ).find(
                item =>
                    item.id === id
            );

        const detail =
            document.getElementById(
                "atlasHADeviceDetail"
            );

        if (
            !device
            || !detail
        ) {
            return;
        }

        state.selected =
            device.id;

        const ip =
            networkIp(device);

        detail.hidden =
            false;

        detail.innerHTML = `
            <h4>${esc(device.name)}</h4>

            <div class="atlas-ha-detail-grid">

                <div>
                    <small>Area</small>
                    <strong>
                        ${esc(device.area || "Unassigned")}
                    </strong>
                </div>

                <div>
                    <small>Status</small>
                    <strong>
                        ${esc(device.status)}
                    </strong>
                </div>

                <div>
                    <small>Protocol</small>
                    <strong>
                        ${esc(device.protocol)}
                    </strong>
                </div>

                <div>
                    <small>Integration</small>
                    <strong>
                        ${esc(
                            (
                                device.integrations
                                || []
                            ).join(", ")
                            || "—"
                        )}
                    </strong>
                </div>

                <div>
                    <small>Manufacturer</small>
                    <strong>
                        ${esc(
                            device.manufacturer
                            || "—"
                        )}
                    </strong>
                </div>

                <div>
                    <small>Model</small>
                    <strong>
                        ${esc(
                            device.model
                            || "—"
                        )}
                    </strong>
                </div>

                <div>
                    <small>IP</small>
                    <strong>
                        ${esc(ip || "—")}
                    </strong>
                </div>

                <div>
                    <small>MAC</small>
                    <strong>
                        ${esc(device.mac || "—")}
                    </strong>
                </div>

                <div>
                    <small>Zigbee IEEE</small>
                    <strong>
                        ${esc(device.ieee || "—")}
                    </strong>
                </div>

                <div>
                    <small>Entities</small>
                    <strong>
                        ${esc(device.entity_count)}
                    </strong>
                </div>

                <div>
                    <small>Live entities</small>
                    <strong>
                        ${esc(device.live_entity_count)}
                    </strong>
                </div>

                <div>
                    <small>Unavailable</small>
                    <strong>
                        ${esc(device.unavailable_count)}
                    </strong>
                </div>

            </div>
        `;

        detail.scrollIntoView(
            {
                behavior: "smooth",
                block: "nearest",
            }
        );
    }

    async function load() {
        root.innerHTML = `
            <div class="atlas-ha-loading">
                Reading Home Assistant
                device registry…
            </div>
        `;

        try {
            const response =
                await fetch(
                    "/api/topology/home-assistant",
                    {
                        headers: {
                            "Accept":
                                "application/json",
                        },
                    }
                );

            if (!response.ok) {
                throw new Error(
                    `HTTP ${response.status}`
                );
            }

            const payload =
                await response.json();

            if (
                payload.status
                !== "SUCCESS"
            ) {
                throw new Error(
                    payload.error
                    || payload.status
                );
            }

            state.payload =
                payload;

            render();
        }
        catch (error) {
            root.innerHTML = `
                <div class="atlas-ha-error">
                    Home Assistant topology unavailable:
                    ${esc(error.message)}
                </div>
            `;
        }
    }

    root.addEventListener(
        "click",
        event => {
            const card =
                event.target.closest(
                    "[data-ha-device-id]"
                );

            if (!card) {
                return;
            }

            showDetail(
                card.dataset
                    .haDeviceId
            );
        }
    );

    window.addEventListener(
        "atlas-map-network-ready",
        event => {
            state.network =
                event.detail;

            if (state.payload) {
                render();
            }
        }
    );

    const refresh =
        document.getElementById(
            "atlasPremiumRefresh"
        );

    if (refresh) {
        refresh.addEventListener(
            "click",
            load
        );
    }

    load();
})();
