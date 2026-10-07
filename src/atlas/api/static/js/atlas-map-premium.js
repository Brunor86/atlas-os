(() => {
    "use strict";

    const root =
        document.getElementById(
            "atlasPremiumMap"
        );

    if (!root) {
        return;
    }


    const searchInput =
        document.getElementById(
            "atlasPremiumSearch"
        );

    const servicesToggle =
        document.getElementById(
            "atlasPremiumServices"
        );

    const refreshButton =
        document.getElementById(
            "atlasPremiumRefresh"
        );

    const healthBox =
        document.getElementById(
            "atlasPremiumHealth"
        );

    const statsBox =
        document.getElementById(
            "atlasPremiumStats"
        );

    const remoteBox =
        document.getElementById(
            "atlasPremiumRemote"
        );

    const hostBox =
        document.getElementById(
            "atlasPremiumHost"
        );

    const guestsBox =
        document.getElementById(
            "atlasPremiumGuests"
        );

    const storageBox =
        document.getElementById(
            "atlasPremiumStorage"
        );

    const dockerBox =
        document.getElementById(
            "atlasPremiumDocker"
        );

    const homeBox =
        document.getElementById(
            "atlasPremiumHome"
        );

    const olivaBox =
        document.getElementById(
            "atlasPremiumOlivaSat"
        );

    const aiBox =
        document.getElementById(
            "atlasPremiumAI"
        );

    const systemServicesBox =
        document.getElementById(
            "atlasPremiumSystemServices"
        );

    const detailBox =
        document.getElementById(
            "atlasPremiumDetail"
        );

    const errorBox =
        document.getElementById(
            "atlasPremiumError"
        );


    const state = {
        payload: null,
        nodesById: new Map(),
        query: "",
        showServices: false,
    };


    function esc(value) {
        return String(
            value ?? ""
        )
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }


    function normalized(value) {
        return String(
            value ?? ""
        )
            .trim()
            .toUpperCase();
    }


    function nameOf(node) {
        return String(
            node?.name
            || node?.id
            || "Unknown"
        );
    }


    function statusOf(node) {
        return normalized(
            node?.status
        );
    }


    function statusClass(node) {
        const status =
            statusOf(node);

        if (
            status.includes("OFFLINE")
            || status.includes("FAILED")
            || status.includes("DOWN")
        ) {
            return "offline";
        }

        if (
            status.includes("DEGRADED")
            || status.includes("WARNING")
            || status.includes("STALE")
        ) {
            return "degraded";
        }

        return "online";
    }


    function typeOf(node) {
        return normalized(
            node?.type
        );
    }


    function isGuest(node) {
        const type =
            typeOf(node);

        return (
            type === "VIRTUAL_MACHINE"
            || type === "VM"
            || type.includes(
                "LINUX_CONTAINER"
            )
            || type === "LXC"
            || node?.id?.startsWith(
                "vm-"
            )
            || node?.id?.startsWith(
                "lxc-"
            )
        );
    }


    function isApplication(node) {
        return (
            typeOf(node)
            === "APPLICATION"
        );
    }


    function isService(node) {
        return (
            typeOf(node)
            === "SERVICE"
        );
    }


    function isStorage(node) {
        return (
            typeOf(node)
            === "STORAGE"
        );
    }


    function matchNode(
        node,
        query
    ) {
        if (!query) {
            return true;
        }

        const haystack = [
            node?.id,
            node?.name,
            node?.type,
            node?.status,
            node?.criticality,
            ...(node?.roles || []),
            node?.identity?.vendor,
            node?.identity?.model,
            ...Object.values(
                node?.network || {}
            ),
        ]
            .join(" ")
            .toLowerCase();

        return haystack.includes(
            query.toLowerCase()
        );
    }


    function networkValue(node) {
        const network =
            node?.network || {};

        return (
            network.ip
            || network.ip_address
            || network.hostname
            || network.host
            || ""
        );
    }


    function vmidValue(node) {
        const network =
            node?.network || {};

        return (
            network.vmid
            || (
                node?.id
                    ?.match(
                        /(?:vm|lxc)[^\d]*(\d+)/i
                    )
                    ?.[1]
            )
            || ""
        );
    }


    function prettyType(node) {
        const type =
            typeOf(node);

        if (
            type === "VIRTUAL_MACHINE"
            || type === "VM"
        ) {
            return "VM";
        }

        if (
            type.includes(
                "LINUX_CONTAINER"
            )
            || type === "LXC"
        ) {
            return "LXC";
        }

        if (
            type.includes(
                "VIRTUALIZATION"
            )
        ) {
            return "HOST";
        }

        return (
            type
                .replaceAll("_", " ")
                || "ASSET"
        );
    }


    function roleLabel(node) {
        const roles =
            node?.roles || [];

        if (roles.length) {
            return roles
                .slice(0, 2)
                .map(
                    role =>
                        role
                            .replaceAll(
                                "_",
                                " "
                            )
                            .toLowerCase()
                )
                .join(" · ");
        }

        const vendor =
            node?.identity?.vendor;

        return (
            vendor
            || prettyType(node)
        );
    }


    function glyph(node) {
        const name =
            nameOf(node)
                .toLowerCase();

        if (
            name.includes("home assistant")
            || name.includes("haos")
        ) {
            return "⌂";
        }

        if (
            name.includes("oliva")
            || name.includes("sat")
        ) {
            return "◌";
        }

        if (
            name.includes("atlas-ai")
            || name.includes("ai")
        ) {
            return "✣";
        }

        if (
            name.includes("windows")
        ) {
            return "⊞";
        }

        if (
            name.includes("db-aceite")
            || name.includes("maria")
            || name.includes("postgres")
        ) {
            return "▰";
        }

        if (
            name.includes("grafana")
        ) {
            return "◉";
        }

        if (
            name.includes("prometheus")
        ) {
            return "▲";
        }

        if (
            name.includes("adguard")
        ) {
            return "◆";
        }

        if (
            name.includes("immich")
        ) {
            return "✦";
        }

        if (
            name.includes("jellyfin")
        ) {
            return "△";
        }

        if (
            name.includes("portainer")
        ) {
            return "▥";
        }

        if (
            name.includes("syncthing")
        ) {
            return "◎";
        }

        if (
            name.includes("filebrowser")
        ) {
            return "▤";
        }

        if (
            name.includes("debian")
            || name.includes("docker")
        ) {
            return "◇";
        }

        return "●";
    }


    function relationshipsFor(id) {
        const edges =
            state.payload?.edges || [];

        return edges.filter(
            edge =>
                edge.source === id
                || edge.target === id
        );
    }


    function directChildren(id) {
        const edges =
            state.payload?.edges || [];

        const childIds =
            edges
                .filter(
                    edge =>
                        edge.source === id
                        && [
                            "HOSTS",
                            "RUNS",
                            "CONTAINS",
                        ].includes(
                            normalized(
                                edge.type
                            )
                        )
                )
                .map(
                    edge =>
                        edge.target
                );

        return childIds
            .map(
                childId =>
                    state.nodesById.get(
                        childId
                    )
            )
            .filter(Boolean);
    }


    function findNode(
        matcher
    ) {
        return (
            state.payload?.nodes || []
        ).find(matcher);
    }


    function guestBy(
        pattern,
        fallbackNumber
    ) {
        const guests =
            (
                state.payload?.nodes
                || []
            ).filter(isGuest);

        return guests.find(
            node =>
                pattern.test(
                    nameOf(node)
                )
        )
        || guests.find(
            node =>
                String(
                    vmidValue(node)
                )
                === String(
                    fallbackNumber
                )
        )
        || null;
    }


    function mainHost() {
        const roots =
            state.payload?.root_ids
            || [];

        for (
            const rootId
            of roots
        ) {
            const node =
                state.nodesById.get(
                    rootId
                );

            if (
                node
                && !isApplication(node)
                && !isService(node)
            ) {
                return node;
            }
        }

        return findNode(
            node =>
                /proxmox|atlas/i.test(
                    nameOf(node)
                )
                && !isGuest(node)
        )
        || findNode(
            node =>
                typeOf(node)
                    .includes(
                        "SERVER"
                    )
        )
        || null;
    }


    function guestCards() {
        const host =
            mainHost();

        let guests =
            host
                ? directChildren(
                    host.id
                ).filter(isGuest)
                : [];

        if (!guests.length) {
            guests =
                (
                    state.payload?.nodes
                    || []
                ).filter(isGuest);
        }

        const seen =
            new Set();

        return guests
            .filter(
                node => {
                    if (
                        seen.has(
                            node.id
                        )
                    ) {
                        return false;
                    }

                    seen.add(
                        node.id
                    );

                    return true;
                }
            )
            .sort(
                (a, b) => {
                    const av =
                        Number(
                            vmidValue(a)
                            || 99999
                        );

                    const bv =
                        Number(
                            vmidValue(b)
                            || 99999
                        );

                    return (
                        av - bv
                        || nameOf(a)
                            .localeCompare(
                                nameOf(b)
                            )
                    );
                }
            );
    }


    function renderHealth() {
        const summary =
            state.payload?.summary
            || {};

        const byStatus =
            summary.by_status
            || {};

        const offline =
            Object.entries(
                byStatus
            )
                .filter(
                    ([key]) =>
                        /OFFLINE|FAILED|DOWN/i
                            .test(key)
                )
                .reduce(
                    (total, [, value]) =>
                        total
                        + Number(
                            value || 0
                        ),
                    0
                );

        const degraded =
            Object.entries(
                byStatus
            )
                .filter(
                    ([key]) =>
                        /DEGRADED|WARNING|STALE/i
                            .test(key)
                )
                .reduce(
                    (total, [, value]) =>
                        total
                        + Number(
                            value || 0
                        ),
                    0
                );

        healthBox.classList.remove(
            "degraded",
            "offline"
        );

        let title =
            "All systems operational";

        if (offline > 0) {
            healthBox.classList.add(
                "offline"
            );

            title =
                `${offline} asset`
                + (
                    offline === 1
                        ? ""
                        : "s"
                )
                + " offline";
        }
        else if (degraded > 0) {
            healthBox.classList.add(
                "degraded"
            );

            title =
                `${degraded} asset`
                + (
                    degraded === 1
                        ? ""
                        : "s"
                )
                + " degraded";
        }

        healthBox.innerHTML = `
            <i></i>
            <div>
                <strong>${esc(title)}</strong>
                <small>
                    ${esc(
                        state.payload
                            ?.generated_at
                            || ""
                    )}
                </small>
            </div>
        `;
    }


    function renderStats() {
        const summary =
            state.payload?.summary
            || {};

        const online =
            Object.entries(
                summary.by_status
                || {}
            )
                .filter(
                    ([key]) =>
                        /ONLINE|HEALTHY|RUNNING/i
                            .test(key)
                )
                .reduce(
                    (total, [, value]) =>
                        total
                        + Number(
                            value || 0
                        ),
                    0
                );

        statsBox.innerHTML = `
            <div class="atlas-premium-panel-title">
                Topology snapshot
            </div>

            <div class="atlas-stat-grid">
                <div>
                    <strong>${esc(summary.nodes ?? 0)}</strong>
                    <small>Assets</small>
                </div>

                <div>
                    <strong>${esc(summary.edges ?? 0)}</strong>
                    <small>Relations</small>
                </div>

                <div>
                    <strong>${esc(online)}</strong>
                    <small>Online</small>
                </div>

                <div>
                    <strong>${esc(summary.connected_nodes ?? 0)}</strong>
                    <small>Connected</small>
                </div>
            </div>
        `;
    }


    function renderRemote() {
        const tailscale =
            findNode(
                node =>
                    /tailscale/i.test(
                        nameOf(node)
                    )
            );

        if (!tailscale) {
            remoteBox.innerHTML = `
                <span class="atlas-remote-icon">◉</span>
                <div>
                    <strong>Remote access</strong>
                    <small>Tailscale not exposed in map</small>
                </div>
            `;

            return;
        }

        remoteBox.innerHTML = `
            <span class="atlas-remote-icon">◉</span>

            <div>
                <strong>Tailscale</strong>
                <small>
                    ${esc(statusOf(tailscale))}
                    ·
                    ${esc(
                        networkValue(
                            tailscale
                        )
                        || "remote access"
                    )}
                </small>
            </div>
        `;

        remoteBox.dataset.nodeId =
            tailscale.id;
    }


    function renderHost() {
        const host =
            mainHost();

        if (!host) {
            hostBox.innerHTML = `
                <div class="atlas-card-loading">
                    No virtualization host identified.
                </div>
            `;

            return;
        }

        const children =
            directChildren(
                host.id
            );

        const guests =
            children.filter(
                isGuest
            );

        const net =
            networkValue(host);

        const model =
            host?.identity?.model
            || "Proxmox VE";

        hostBox.dataset.nodeId =
            host.id;

        hostBox.innerHTML = `
            <div class="atlas-host-heading">

                <div class="atlas-proxmox-brand">
                    <div class="atlas-proxmox-mark">
                        X
                    </div>

                    <div>
                        <h3>${esc(nameOf(host))}</h3>
                        <p>
                            ${esc(model)}
                            ${net ? ` · ${esc(net)}` : ""}
                        </p>
                    </div>
                </div>

                <span
                    class="atlas-live-dot ${esc(statusClass(host))}"
                    title="${esc(statusOf(host))}"
                ></span>

            </div>

            <div class="atlas-host-facts">

                <div class="atlas-host-fact">
                    <small>Health</small>
                    <strong>${esc(host.health)}%</strong>
                </div>

                <div class="atlas-host-fact">
                    <small>Guests</small>
                    <strong>${esc(guests.length)}</strong>
                </div>

                <div class="atlas-host-fact">
                    <small>Criticality</small>
                    <strong>${esc(host.criticality)}</strong>
                </div>

                <div class="atlas-host-fact">
                    <small>Presence</small>
                    <strong>${esc(host.presence)}</strong>
                </div>

            </div>
        `;
    }


    function guestDescription(
        node
    ) {
        const name =
            nameOf(node)
                .toLowerCase();

        if (
            name.includes(
                "debian-docker"
            )
        ) {
            return "Docker & core services";
        }

        if (
            name.includes(
                "home assistant"
            )
            || name.includes(
                "haos"
            )
        ) {
            return "Smart home platform";
        }

        if (
            name.includes(
                "atlas-ai"
            )
        ) {
            return "AI / LLM workloads";
        }

        if (
            name.includes(
                "db-aceite"
            )
        ) {
            return "Database & data";
        }

        if (
            name.includes(
                "oliva"
            )
        ) {
            return "Satellite & agriculture";
        }

        if (
            name.includes(
                "windows"
            )
        ) {
            return "Windows workload";
        }

        return roleLabel(node);
    }


    function renderGuests() {
        const guests =
            guestCards();

        const query =
            state.query;

        guestsBox.innerHTML =
            guests
                .map(
                    node => {
                        const filtered =
                            !matchNode(
                                node,
                                query
                            );

                        const vmid =
                            vmidValue(
                                node
                            );

                        const ip =
                            networkValue(
                                node
                            );

                        const children =
                            directChildren(
                                node.id
                            );

                        const type =
                            prettyType(
                                node
                            );

                        return `
                            <article
                                class="atlas-guest-card ${filtered ? "is-filtered" : ""}"
                                data-node-id="${esc(node.id)}"
                            >

                                <div class="atlas-guest-card-top">

                                    <span
                                        class="atlas-type-chip ${type === "LXC" ? "lxc" : ""}"
                                    >
                                        ${esc(type)}
                                        ${vmid ? ` ${esc(vmid)}` : ""}
                                    </span>

                                    <span
                                        class="atlas-card-dot ${esc(statusClass(node))}"
                                    ></span>

                                </div>

                                <div class="atlas-guest-icon">
                                    ${esc(glyph(node))}
                                </div>

                                <h4>${esc(nameOf(node))}</h4>

                                <p>
                                    ${esc(guestDescription(node))}
                                </p>

                                <div class="atlas-guest-meta">
                                    <span>
                                        Health
                                        <b>${esc(node.health)}%</b>
                                    </span>

                                    <span>
                                        Hosted assets
                                        <b>${esc(children.length)}</b>
                                    </span>

                                    ${
                                        ip
                                            ? `
                                                <span>
                                                    Network
                                                    <b>${esc(ip)}</b>
                                                </span>
                                            `
                                            : ""
                                    }
                                </div>

                            </article>
                        `;
                    }
                )
                .join("");
    }


    function renderDomainTitle(
        symbol,
        title,
        subtitle,
        status = "online"
    ) {
        return `
            <div class="atlas-domain-title">

                <div>
                    <span class="atlas-domain-symbol">
                        ${esc(symbol)}
                    </span>

                    <div>
                        <strong>${esc(title)}</strong>
                        <small>${esc(subtitle)}</small>
                    </div>
                </div>

                <span
                    class="atlas-card-dot ${esc(status)}"
                ></span>

            </div>
        `;
    }


    function renderStorage() {
        const nodes =
            (
                state.payload?.nodes
                || []
            )
                .filter(isStorage)
                .filter(
                    node =>
                        matchNode(
                            node,
                            state.query
                        )
                );

        storageBox.innerHTML =
            renderDomainTitle(
                "▱",
                "Storage",
                `${nodes.length} discovered`
            )
            + `
                <div class="atlas-storage-list">

                    ${
                        nodes.length
                            ? nodes
                                .slice(0, 8)
                                .map(
                                    node => `
                                        <div
                                            class="atlas-storage-tile"
                                            data-node-id="${esc(node.id)}"
                                        >
                                            <strong>${esc(nameOf(node))}</strong>
                                            <small>
                                                ${esc(roleLabel(node))}
                                                · health ${esc(node.health)}%
                                            </small>
                                        </div>
                                    `
                                )
                                .join("")
                            : `
                                <div class="atlas-domain-more">
                                    No storage matches current filter.
                                </div>
                            `
                    }

                </div>
            `;
    }


    function renderDocker() {
        const apps =
            (
                state.payload?.nodes
                || []
            )
                .filter(isApplication)
                .filter(
                    node => {
                        const vendor =
                            String(
                                node?.identity
                                    ?.vendor
                                || ""
                            );

                        return (
                            /docker/i.test(
                                vendor
                            )
                            || node.id
                                .startsWith(
                                    "application-docker-"
                                )
                        );
                    }
                )
                .filter(
                    node =>
                        matchNode(
                            node,
                            state.query
                        )
                )
                .sort(
                    (a, b) =>
                        nameOf(a)
                            .localeCompare(
                                nameOf(b)
                            )
                );

        const visible =
            apps.slice(
                0,
                state.query
                    ? 24
                    : 12
            );

        dockerBox.innerHTML =
            renderDomainTitle(
                "◆",
                "Docker Services",
                `${apps.length} active applications`
            )
            + `
                <div class="atlas-app-grid">

                    ${
                        visible
                            .map(
                                node => `
                                    <div
                                        class="atlas-app-tile"
                                        data-node-id="${esc(node.id)}"
                                    >

                                        <div class="atlas-app-tile-head">

                                            <span class="atlas-app-glyph">
                                                ${esc(glyph(node))}
                                            </span>

                                            <div>
                                                <strong>${esc(nameOf(node))}</strong>
                                                <small>
                                                    ${esc(roleLabel(node))}
                                                </small>
                                            </div>

                                        </div>

                                    </div>
                                `
                            )
                            .join("")
                    }

                </div>

                ${
                    apps.length
                    > visible.length
                        ? `
                            <div class="atlas-domain-more">
                                +${apps.length - visible.length}
                                additional applications
                            </div>
                        `
                        : ""
                }
            `;
    }


    function hostedServices(
        guest
    ) {
        if (!guest) {
            return [];
        }

        return directChildren(
            guest.id
        )
            .filter(isService)
            .sort(
                (a, b) =>
                    nameOf(a)
                        .localeCompare(
                            nameOf(b)
                        )
            );
    }


    function renderSpecialDomain(
        box,
        {
            symbol,
            title,
            guest,
            emptyText,
            limit = 6,
        }
    ) {
        if (!guest) {
            box.innerHTML =
                renderDomainTitle(
                    symbol,
                    title,
                    "No matching asset",
                    "degraded"
                )
                + `
                    <div class="atlas-domain-more">
                        ${esc(emptyText)}
                    </div>
                `;

            return;
        }

        const services =
            hostedServices(
                guest
            )
                .filter(
                    node =>
                        matchNode(
                            node,
                            state.query
                        )
                );

        const ip =
            networkValue(
                guest
            );

        box.innerHTML =
            renderDomainTitle(
                symbol,
                title,
                prettyType(guest),
                statusClass(
                    guest
                )
            )
            + `
                <div
                    class="atlas-domain-feature"
                    data-node-id="${esc(guest.id)}"
                >
                    <h4>${esc(nameOf(guest))}</h4>
                    <p>
                        ${esc(guestDescription(guest))}
                        ${ip ? ` · ${esc(ip)}` : ""}
                    </p>
                </div>

                <div class="atlas-domain-list">

                    ${
                        services.length
                            ? services
                                .slice(
                                    0,
                                    limit
                                )
                                .map(
                                    node => `
                                        <div
                                            class="atlas-domain-node"
                                            data-node-id="${esc(node.id)}"
                                        >
                                            <strong>${esc(nameOf(node))}</strong>
                                            <small>
                                                ${esc(statusOf(node))}
                                                · ${esc(roleLabel(node))}
                                            </small>
                                        </div>
                                    `
                                )
                                .join("")
                            : `
                                <div class="atlas-domain-more">
                                    No hosted services exposed
                                    in current topology.
                                </div>
                            `
                    }

                </div>
            `;
    }


    function renderDomains() {
        renderStorage();
        renderDocker();

        renderSpecialDomain(
            homeBox,
            {
                symbol: "⌂",
                title: "Smart Home",
                guest:
                    guestBy(/home assistant|haos/i),
                emptyText:
                    "Home Assistant asset not found.",
                limit: 5,
            }
        );

        renderSpecialDomain(
            olivaBox,
            {
                symbol: "◌",
                title: "OlivaSat",
                guest:
                    guestBy(/oliva/i),
                emptyText:
                    "OlivaSat asset not found.",
                limit: 6,
            }
        );

        renderSpecialDomain(
            aiBox,
            {
                symbol: "✣",
                title: "ATLAS AI",
                guest:
                    guestBy(/atlas-ai/i),
                emptyText:
                    "ATLAS AI asset not found.",
                limit: 5,
            }
        );
    }


    function renderSystemServices() {
        const services =
            (
                state.payload?.nodes
                || []
            )
                .filter(isService)
                .filter(
                    node =>
                        matchNode(
                            node,
                            state.query
                        )
                )
                .sort(
                    (a, b) =>
                        nameOf(a)
                            .localeCompare(
                                nameOf(b)
                            )
                );

        systemServicesBox.hidden =
            !state.showServices;

        if (
            !state.showServices
        ) {
            return;
        }

        systemServicesBox.innerHTML = `
            ${renderDomainTitle(
                "≡",
                "System services",
                `${services.length} active service assets`
            )}

            <div class="atlas-services-grid">

                ${
                    services
                        .map(
                            node => `
                                <div
                                    class="atlas-domain-node"
                                    data-node-id="${esc(node.id)}"
                                >
                                    <strong>${esc(nameOf(node))}</strong>
                                    <small>
                                        ${esc(statusOf(node))}
                                        · health ${esc(node.health)}%
                                    </small>
                                </div>
                            `
                        )
                        .join("")
                }

            </div>
        `;
    }


    function renderDetail(
        node
    ) {
        if (!node) {
            detailBox.hidden =
                true;

            return;
        }

        const relationships =
            relationshipsFor(
                node.id
            );

        const network =
            node.network || {};

        detailBox.hidden =
            false;

        detailBox.innerHTML = `
            <div class="atlas-detail-header">

                <div>
                    <h3>${esc(nameOf(node))}</h3>
                    <p>
                        ${esc(prettyType(node))}
                        · ${esc(statusOf(node))}
                        · ${esc(node.criticality)}
                    </p>
                </div>

                <button
                    class="atlas-detail-close"
                    type="button"
                    aria-label="Close asset details"
                >
                    ×
                </button>

            </div>

            <div class="atlas-detail-grid">

                <div>
                    <small>Health</small>
                    <strong>${esc(node.health)}%</strong>
                </div>

                <div>
                    <small>Presence</small>
                    <strong>${esc(node.presence)}</strong>
                </div>

                <div>
                    <small>Relationships</small>
                    <strong>${esc(relationships.length)}</strong>
                </div>

                <div>
                    <small>Roles</small>
                    <strong>
                        ${esc(
                            (node.roles || [])
                                .join(", ")
                                || "—"
                        )}
                    </strong>
                </div>

                <div>
                    <small>Vendor</small>
                    <strong>
                        ${esc(
                            node.identity?.vendor
                            || "—"
                        )}
                    </strong>
                </div>

                <div>
                    <small>Model</small>
                    <strong>
                        ${esc(
                            node.identity?.model
                            || "—"
                        )}
                    </strong>
                </div>

                <div>
                    <small>Network</small>
                    <strong>
                        ${esc(
                            Object.values(
                                network
                            )
                                .filter(Boolean)
                                .join(" · ")
                                || "—"
                        )}
                    </strong>
                </div>

                <div>
                    <small>Asset ID</small>
                    <strong>${esc(node.id)}</strong>
                </div>

            </div>
        `;
    }


    function render() {
        if (!state.payload) {
            return;
        }

        renderHealth();
        renderStats();
        renderRemote();
        renderHost();
        renderGuests();
        renderDomains();
        renderSystemServices();
    }


    async function load() {
        refreshButton.disabled =
            true;

        errorBox.hidden =
            true;

        try {
            const response =
                await fetch(
                    "/api/topology/map",
                    {
                        headers: {
                            "Accept":
                                "application/json",
                        },
                    }
                );

            if (!response.ok) {
                throw new Error(
                    `Topology API returned HTTP ${response.status}`
                );
            }

            const payload =
                await response.json();

            state.payload =
                payload;

            state.nodesById =
                new Map(
                    (
                        payload.nodes
                        || []
                    ).map(
                        node => [
                            node.id,
                            node,
                        ]
                    )
                );

            render();
        }
        catch (error) {
            errorBox.hidden =
                false;

            errorBox.textContent =
                `ATLAS Map could not load: ${error.message}`;
        }
        finally {
            refreshButton.disabled =
                false;
        }
    }


    root.addEventListener(
        "click",
        event => {
            const close =
                event.target.closest(
                    ".atlas-detail-close"
                );

            if (close) {
                detailBox.hidden =
                    true;
                return;
            }

            const target =
                event.target.closest(
                    "[data-node-id]"
                );

            if (!target) {
                return;
            }

            const id =
                target.dataset.nodeId;

            const node =
                state.nodesById.get(
                    id
                );

            if (node) {
                renderDetail(
                    node
                );
            }
        }
    );


    searchInput.addEventListener(
        "input",
        () => {
            state.query =
                searchInput.value
                    .trim();

            render();
        }
    );


    servicesToggle.addEventListener(
        "change",
        () => {
            state.showServices =
                servicesToggle.checked;

            renderSystemServices();
        }
    );


    refreshButton.addEventListener(
        "click",
        load
    );


    load();
})();
