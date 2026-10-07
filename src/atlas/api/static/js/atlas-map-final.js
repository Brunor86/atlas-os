(() => {
    "use strict";

    const state = {
        identity: null,
        scheduled: false,
    };

    const lower = value =>
        String(value ?? "")
            .trim()
            .toLowerCase();

    function guestCards() {
        return [
            ...document.querySelectorAll(
                ".atlas-guest-card"
            ),
        ];
    }

    function guestCardFor(guest) {
        const name =
            lower(guest.name);

        const vmid =
            String(
                guest.vmid ?? ""
            );

        return guestCards().find(
            card => {
                const text =
                    lower(
                        card.textContent
                    );

                const nodeId =
                    lower(
                        card.dataset.nodeId
                        || ""
                    );

                if (
                    name
                    && text.includes(name)
                ) {
                    return true;
                }

                if (
                    vmid
                    && (
                        nodeId.includes(vmid)
                        || text.includes(
                            ` ${vmid} `
                        )
                    )
                ) {
                    return true;
                }

                return false;
            }
        );
    }

    function networkDeviceForGuest(
        guest
    ) {
        const devices =
            state.identity?.devices
            || [];

        const vmid =
            String(
                guest.vmid ?? ""
            );

        const name =
            lower(
                guest.name
            );

        let match =
            devices.find(
                device =>
                    String(
                        device.proxmox?.vmid
                        ?? ""
                    )
                    === vmid
            );

        if (match) {
            return match;
        }

        match =
            devices.find(
                device =>
                    lower(
                        device.name
                    )
                    === name
            );

        return match || null;
    }

    function ensureGuestNetworkState() {
        const guests =
            state.identity
                ?.proxmox_guests
            || [];

        for (
            const guest
            of guests
        ) {
            const card =
                guestCardFor(
                    guest
                );

            if (!card) {
                continue;
            }

            const running =
                lower(
                    guest.status
                )
                === "running";

            const existingIp =
                card.querySelector(
                    ".atlas-guest-network-ip"
                );

            let finalState =
                card.querySelector(
                    ".atlas-final-guest-state"
                );

            if (!running) {
                /*
                 * Critical correctness rule:
                 * stopped guests must never inherit
                 * the Proxmox host IP.
                 */
                if (existingIp) {
                    existingIp.remove();
                }

                card.classList.add(
                    "atlas-final-stopped"
                );

                if (!finalState) {
                    finalState =
                        document.createElement(
                            "div"
                        );

                    finalState.className =
                        "atlas-final-guest-state stopped";

                    card.appendChild(
                        finalState
                    );
                }

                if (
                    finalState.textContent
                    !== "STOPPED · IP —"
                ) {
                    finalState.textContent =
                        "STOPPED · IP —";
                }

                continue;
            }

            card.classList.remove(
                "atlas-final-stopped"
            );

            if (finalState) {
                finalState.remove();
            }

            const device =
                networkDeviceForGuest(
                    guest
                );

            const ip =
                device?.ip
                || guest.ip
                || null;

            if (!ip) {
                if (existingIp) {
                    existingIp.remove();
                }

                continue;
            }

            let badge =
                existingIp;

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

            if (
                badge.textContent
                !== ip
            ) {
                badge.textContent =
                    ip;
            }
        }
    }

    function ensureProxmoxHostIp() {
        const devices =
            state.identity?.devices
            || [];

        const proxmox =
            devices.find(
                device =>
                    device.kind
                    === "proxmox"
            )
            || devices.find(
                device =>
                    lower(
                        device.name
                    ).includes(
                        "proxmox"
                    )
            );

        if (
            !proxmox
            || !proxmox.ip
        ) {
            return;
        }

        const host =
            document.getElementById(
                "atlasPremiumHost"
            );

        if (!host) {
            return;
        }

        let badge =
            host.querySelector(
                ".atlas-final-host-ip"
            );

        if (!badge) {
            badge =
                document.createElement(
                    "div"
                );

            badge.className =
                "atlas-final-host-ip";

            host.appendChild(
                badge
            );
        }

        const text =
            `LAN ${proxmox.ip}`;

        if (
            badge.textContent
            !== text
        ) {
            badge.textContent =
                text;
        }
    }

    function ensureHaSystemCollapse() {
        const section =
            document.querySelector(
                ".atlas-ha-system"
            );

        if (
            !section
            || section.dataset
                .atlasFinalized
            === "1"
        ) {
            return;
        }

        const heading =
            section.querySelector(
                ".atlas-ha-system-heading"
            );

        const grid =
            section.querySelector(
                ".atlas-ha-device-grid"
            );

        if (
            !heading
            || !grid
        ) {
            return;
        }

        section.dataset
            .atlasFinalized =
            "1";

        section.classList.add(
            "is-collapsed"
        );

        const count =
            grid.querySelectorAll(
                ".atlas-ha-device"
            ).length;

        const button =
            document.createElement(
                "button"
            );

        button.type =
            "button";

        button.className =
            "atlas-ha-system-toggle";

        button.textContent =
            `Show ${count} internal devices`;

        button.addEventListener(
            "click",
            () => {
                const collapsed =
                    section.classList
                        .toggle(
                            "is-collapsed"
                        );

                button.textContent =
                    collapsed
                        ? `Show ${count} internal devices`
                        : "Hide internal devices";
            }
        );

        heading.appendChild(
            button
        );
    }

    function apply() {
        if (!state.identity) {
            return;
        }

        ensureProxmoxHostIp();
        ensureGuestNetworkState();
        ensureHaSystemCollapse();
    }

    function scheduleApply() {
        if (state.scheduled) {
            return;
        }

        state.scheduled = true;

        setTimeout(
            () => {
                state.scheduled =
                    false;

                apply();
            },
            80
        );
    }

    async function refreshIdentity() {
        try {
            const response =
                await fetch(
                    "/api/topology/identity?scan=false",
                    {
                        headers: {
                            "Accept":
                                "application/json",
                        },
                    }
                );

            if (!response.ok) {
                return;
            }

            const payload =
                await response.json();

            if (
                payload.status
                !== "SUCCESS"
            ) {
                return;
            }

            state.identity =
                payload;

            scheduleApply();
        }
        catch (_) {
            /*
             * This is an enhancement layer.
             * Base ATLAS Map remains functional
             * if reconciliation is temporarily
             * unavailable.
             */
        }
    }

    const observer =
        new MutationObserver(
            scheduleApply
        );

    observer.observe(
        document.documentElement,
        {
            childList: true,
            subtree: true,
        }
    );

    window.addEventListener(
        "atlas-map-network-ready",
        () => {
            setTimeout(
                refreshIdentity,
                150
            );
        }
    );

    const refresh =
        document.getElementById(
            "atlasPremiumRefresh"
        );

    if (refresh) {
        refresh.addEventListener(
            "click",
            () => {
                setTimeout(
                    refreshIdentity,
                    400
                );
            }
        );
    }

    refreshIdentity();
})();
