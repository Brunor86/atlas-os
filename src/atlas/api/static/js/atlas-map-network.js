(() => {
    "use strict";

    const root =
        document.getElementById(
            "atlasPremiumNetwork"
        );

    if (!root) {
        return;
    }

    const esc = value =>
        String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");

    function iconFor(device) {
        switch (device.kind) {
            case "proxmox":
                return "X";

            case "atlas_ai":
                return "✣";

            case "home_assistant":
                return "⌂";

            case "atlas_observer":
                return "◇";

            default:
                return "●";
        }
    }

    function classFor(device) {
        const classes = [];

        if (
            device.kind
            && device.kind
            !== "lan_device"
        ) {
            classes.push("known");
        }

        if (
            device.kind
            === "home_assistant"
        ) {
            classes.push(
                "home-assistant"
            );
        }

        if (
            device.kind
            === "proxmox"
        ) {
            classes.push(
                "proxmox"
            );
        }

        if (
            device.kind
            === "atlas_ai"
        ) {
            classes.push(
                "atlas-ai"
            );
        }

        return classes.join(" ");
    }

    function decorateGuestCards(
        devices
    ) {
        const cards =
            document.querySelectorAll(
                ".atlas-guest-card"
            );

        for (
            const device
            of devices
        ) {
            const vmid =
                device.proxmox?.vmid;

            const deviceName =
                String(
                    device.name || ""
                )
                .trim()
                .toLowerCase();

            for (
                const card
                of cards
            ) {
                const text =
                    card.textContent
                        .trim()
                        .toLowerCase();

                const nodeId =
                    String(
                        card.dataset.nodeId
                        || ""
                    )
                    .toLowerCase();

                const vmidMatch =
                    vmid
                    && (
                        nodeId.includes(
                            String(vmid)
                        )
                    );

                const exactNameMatch =
                    deviceName
                    && (
                        text.includes(
                            deviceName
                        )
                    );

                if (
                    !vmidMatch
                    && !exactNameMatch
                ) {
                    continue;
                }

                /*
                 * Never assign a LAN address to a stopped
                 * Proxmox guest.
                 */
                if (
                    device.proxmox
                    && String(
                        device.proxmox.status
                        || ""
                    ).toLowerCase()
                    !== "running"
                ) {
                    continue;
                }

                if (!device.ip) {
                    continue;
                }

                let badge =
                    card.querySelector(
                        ".atlas-guest-network-ip"
                    );

                if (!badge) {
                    badge =
                        document.createElement(
                            "div"
                        );

                    badge.className =
                        "atlas-guest-network-ip";

                    card.appendChild(
                        badge
                    );
                }

                badge.textContent =
                    device.ip;
            }
        }
    }

    function render(data) {
        const gateway =
            data.gateway || {};

        const devices =
            data.devices || [];

        const summary =
            data.summary || {};

        root.innerHTML = `
            <div class="atlas-network-heading">

                <div>
                    <h3>
                        Local Network
                    </h3>

                    <p>
                        Starlink gateway →
                        observed IPv4 clients
                        on ${esc(
                            data.local?.cidr
                            || "local LAN"
                        )}
                    </p>
                </div>

                <div class="atlas-network-count">

                    <div>
                        <strong>
                            ${esc(
                                summary.observed_devices
                                ?? devices.length
                            )}
                        </strong>
                        <small>Observed</small>
                    </div>

                    <div>
                        <strong>
                            ${esc(
                                summary.identified_devices ?? summary.named_devices ?? 0
                            )}
                        </strong>
                        <small>Identified</small>
                    </div>

                    <div>
                        <strong>
                            ${esc(
                                summary.unknown_devices
                                ?? 0
                            )}
                        </strong>
                        <small>Unknown</small>
                    </div>

                </div>

            </div>

            <div class="atlas-network-tree">

                <article class="atlas-router-card">

                    <div class="atlas-router-top">

                        <div class="atlas-router-icon">
                            ◉
                        </div>

                        <div>
                            <strong>
                                ${esc(
                                    gateway.name
                                    || "Starlink router"
                                )}
                            </strong>

                            <small>
                                Default gateway ·
                                ${esc(
                                    gateway.state
                                    || gateway.status
                                    || "observed"
                                )}
                            </small>
                        </div>

                    </div>

                    <div class="atlas-router-address">

                        <div>
                            <span>IP</span>
                            <b>
                                ${esc(
                                    gateway.ip
                                    || "—"
                                )}
                            </b>
                        </div>

                        <div>
                            <span>MAC</span>
                            <b>
                                ${esc(
                                    gateway.mac
                                    || "—"
                                )}
                            </b>
                        </div>

                    </div>

                </article>

                <div class="atlas-network-trunk"></div>
                <div class="atlas-network-bus"></div>

                <div class="atlas-network-clients">

                    ${
                        devices
                            .map(
                                device => `
                                    <article
                                        class="
                                            atlas-network-device
                                            ${esc(
                                                classFor(
                                                    device
                                                )
                                            )}
                                            ${esc(
                                                device.kind
                                                || ""
                                            )}
                                        "
                                    >
                                        <div class="atlas-network-device-top">

                                            <div class="atlas-network-device-icon">
                                                ${esc(
                                                    iconFor(
                                                        device
                                                    )
                                                )}
                                            </div>

                                            <div class="atlas-network-device-name">

                                                <strong>
                                                    ${esc(
                                                        device.name
                                                    )}
                                                </strong>

                                                <small>
                                                    ${esc(
                                                        device.home_assistant?.manufacturer
                                                        || device.kind
                                                        || "LAN device"
                                                    )}
                                                    ·
                                                    ${esc(
                                                        device.home_assistant?.model
                                                        || device.state
                                                        || "observed"
                                                    )}
                                                </small>

                                            </div>

                                        </div>

                                        <div class="atlas-network-ip">
                                            ${esc(device.ip)}
                                        </div>

                                        <div class="atlas-network-mac">
                                            ${esc(
                                                device.mac
                                                || "MAC unavailable"
                                            )}
                                        </div>


                                        ${
                                            device.proxmox
                                                ? `
                                                    <div class="atlas-network-origin">
                                                        <span>
                                                            ${esc(
                                                                device.proxmox.guest_type
                                                            )}
                                                            ${esc(
                                                                device.proxmox.vmid
                                                            )}
                                                        </span>
                                                        <span>
                                                            ${esc(
                                                                device.proxmox.status
                                                            )}
                                                        </span>
                                                    </div>
                                                `
                                                : ""
                                        }

                                        ${
                                            device.home_assistant
                                                ? `
                                                    <div class="atlas-network-origin">
                                                        <span>
                                                            Home Assistant
                                                        </span>
                                                        ${
                                                            device.home_assistant.area
                                                                ? `
                                                                    <span>
                                                                        ${esc(
                                                                            device.home_assistant.area
                                                                        )}
                                                                    </span>
                                                                `
                                                                : ""
                                                        }
                                                    </div>
                                                `
                                                : ""
                                        }

                                    </article>
                                `
                            )
                            .join("")
                    }

                </div>

            </div>

            <div class="atlas-network-mode">
                Discovery mode:
                ${esc(
                    data.mode
                    || "unknown"
                )}
            </div>
        `;

        // The premium renderer is asynchronous too.
        // Give it a moment to create the VM/LXC cards,
        // then add IP badges where identities match.
        setTimeout(
            () => {
                decorateGuestCards(
                    devices
                );
            },
            350
        );
    }

    async function load(
        scan = true
    ) {
        try {
            root.innerHTML = `
                <div class="atlas-network-loading">
                    ${
                        scan
                            ? "Scanning local network…"
                            : "Loading network snapshot…"
                    }
                </div>
            `;

            const response =
                await fetch(
                    `/api/topology/identity?scan=${
                        scan
                            ? "true"
                            : "false"
                    }`,
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

            const data =
                await response.json();

            if (
                data.status
                !== "SUCCESS"
            ) {
                throw new Error(
                    data.error
                    || "network discovery failed"
                );
            }

            window.atlasMapNetworkSnapshot = data;

            window.dispatchEvent(
                new CustomEvent(
                    "atlas-map-network-ready",
                    {
                        detail: data,
                    }
                )
            );

            render(data);
        }
        catch (error) {
            root.innerHTML = `
                <div class="atlas-network-loading">
                    Network discovery unavailable:
                    ${esc(error.message)}
                </div>
            `;
        }
    }

    const refresh =
        document.getElementById(
            "atlasPremiumRefresh"
        );

    if (refresh) {
        refresh.addEventListener(
            "click",
            () => load(true)
        );
    }

    load(true);
})();
