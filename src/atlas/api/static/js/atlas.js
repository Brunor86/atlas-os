document.addEventListener("DOMContentLoaded", () => {

    if (
        document.documentElement.dataset
            .atlasAskInitialized === "true"
    ) {
        return;
    }

    document.documentElement.dataset
        .atlasAskInitialized = "true";


    const form =
        document.getElementById("atlasAskForm");

    const input =
        document.getElementById("atlasAskInput");

    const response =
        document.getElementById("atlasAskResponse");


    if (!form || !input || !response) {
        return;
    }


    document
        .querySelectorAll(
            ".os-ask-suggestions button"
        )
        .forEach((button) => {

            button.addEventListener(
                "click",
                () => {

                    input.value =
                        button.textContent.trim();

                    input.focus();

                }
            );

        });


    let source = null;

    let operatorProposalActive = false;


    function closeSource() {

        if (source) {
            source.close();
            source = null;
        }

    }


    function createActivity() {

        operatorProposalActive = false;

        response.hidden = false;
        response.innerHTML = `
            <div class="atlas-live">

                <div class="atlas-live-header">
                    <div>
                        <span class="os-thinking-dot"></span>
                        <strong>ATLAS is working</strong>
                    </div>

                    <span
                        class="atlas-live-mode"
                        id="atlasLiveMode"
                    >
                        Live
                    </span>
                </div>

                <div
                    class="atlas-live-timeline"
                    id="atlasLiveTimeline"
                ></div>

                <div
                    class="atlas-live-answer"
                    id="atlasLiveAnswer"
                    hidden
                ></div>

                <div
                    class="os-atlas-meta"
                    id="atlasLiveMeta"
                ></div>

            </div>
        `;
    }


    function eventId(
        key
    ) {
        return (
            "atlas-event-"
            + key.replace(
                /[^a-zA-Z0-9_-]/g,
                "-"
            )
        );
    }


    function updateEvent(
        key,
        title,
        detail = "",
        state = "done"
    ) {

        const timeline =
            document.getElementById(
                "atlasLiveTimeline"
            );

        if (!timeline) {
            return;
        }


        const id =
            eventId(key);


        let item =
            document.getElementById(id);


        if (!item) {

            item =
                document.createElement("div");

            item.id = id;

            item.innerHTML = `
                <span class="atlas-live-indicator"></span>
                <div>
                    <strong></strong>
                    <small></small>
                </div>
            `;

            timeline.appendChild(
                item
            );

        }


        item.className =
            `atlas-live-event ${state}`;


        item.querySelector(
            "strong"
        ).textContent = title;


        const small =
            item.querySelector(
                "small"
            );

        small.textContent =
            detail;

        small.hidden =
            !detail;
    }


    function addMeta(
        value
    ) {

        if (!value) {
            return;
        }

        const meta =
            document.getElementById(
                "atlasLiveMeta"
            );

        if (!meta) {
            return;
        }

        const existing = [
            ...meta.querySelectorAll(
                "span"
            )
        ].some(
            item =>
                item.textContent === value
        );

        if (existing) {
            return;
        }

        const chip =
            document.createElement("span");

        chip.textContent =
            value;

        meta.appendChild(
            chip
        );
    }


    function setMode(
        value
    ) {

        const mode =
            document.getElementById(
                "atlasLiveMode"
            );

        if (mode) {
            mode.textContent = value;
        }
    }


    function parse(
        event
    ) {

        try {
            return JSON.parse(
                event.data
            );
        }
        catch (_) {
            return {};
        }
    }


    function startAsk(
        question
    ) {

        closeSource();

        createActivity();


        source = new EventSource(
            "/api/ai/ask/stream?question="
            + encodeURIComponent(
                question
            )
        );


        source.addEventListener(
            "started",
            event => {

                const data =
                    parse(event);

                updateEvent(
                    "request",
                    "Request received",
                    data.message,
                    "done"
                );

            }
        );


        source.addEventListener(
            "semantic_started",
            () => {

                updateEvent(
                    "semantic",
                    "Semantic knowledge",
                    "Resolving infrastructure",
                    "working"
                );

            }
        );


        source.addEventListener(
            "semantic_completed",
            event => {

                const data =
                    parse(event);

                if (
                    data.status === "SUCCESS"
                ) {

                    updateEvent(
                        "semantic",
                        "Semantic knowledge",
                        "Verified answer path found",
                        "done"
                    );

                }
                else {

                    updateEvent(
                        "semantic",
                        "Semantic knowledge",
                        "Escalating to deeper investigation",
                        "neutral"
                    );

                }

            }
        );


        source.addEventListener(
            "tool_preflight_started",
            () => {

                updateEvent(
                    "tool-preflight",
                    "Knowledge routing",
                    "Checking deterministic tools",
                    "working"
                );

            }
        );


        source.addEventListener(
            "tool_preflight_completed",
            event => {

                const data =
                    parse(event);

                updateEvent(
                    "tool-preflight",
                    "Knowledge routing",
                    (
                        data.status === "SUCCESS"
                        ? "Deterministic tool selected"
                        : "No direct tool answer"
                    ),
                    (
                        data.status === "SUCCESS"
                        ? "done"
                        : "neutral"
                    )
                );

            }
        );


        source.addEventListener(
            "planner_started",
            event => {

                const data =
                    parse(event);

                updateEvent(
                    `planner-${data.call || 1}`,
                    `Local AI · planner ${data.call || 1}`,
                    "Planning next knowledge step",
                    "working"
                );

                setMode(
                    "Local AI"
                );

            }
        );


        source.addEventListener(
            "planner_completed",
            event => {

                const data =
                    parse(event);

                const latency =
                    Number(
                        data.latency_ms
                        || 0
                    );

                const detail = [
                    data.model,
                    latency
                        ? `${(latency / 1000).toFixed(2)} s`
                        : null,
                ]
                    .filter(Boolean)
                    .join(" · ");


                updateEvent(
                    `planner-${data.call || 1}`,
                    `Local AI · planner ${data.call || 1}`,
                    detail || "Planning completed",
                    "done"
                );

            }
        );


        source.addEventListener(
            "planner_failed",
            event => {

                const data =
                    parse(event);

                updateEvent(
                    `planner-${data.call || 1}`,
                    "Local AI",
                    data.error || "Planner failed",
                    "error"
                );

            }
        );


        source.addEventListener(
            "tool_started",
            event => {

                const data =
                    parse(event);

                updateEvent(
                    `tool-${data.step}-${data.tool}`,
                    data.tool || "ATLAS tool",
                    "Querying verified knowledge",
                    "working"
                );

            }
        );


        source.addEventListener(
            "tool_completed",
            event => {

                const data =
                    parse(event);

                const latency =
                    Number(
                        data.latency_ms
                        || 0
                    );

                updateEvent(
                    `tool-${data.step}-${data.tool}`,
                    data.tool || "ATLAS tool",
                    [
                        data.status,
                        latency
                            ? `${latency.toFixed(1)} ms`
                            : null,
                    ]
                        .filter(Boolean)
                        .join(" · "),
                    (
                        data.status === "SUCCESS"
                        ? "done"
                        : "error"
                    )
                );

                addMeta(
                    data.tool
                );

            }
        );


        source.addEventListener(
            "answer_ready",
            () => {

                updateEvent(
                    "answer-ready",
                    "Knowledge ready",
                    "Verified investigation completed",
                    "done"
                );

            }
        );


        source.addEventListener(
            "execution",
            event => {

                const data =
                    parse(event);


                if (
                    !operatorProposalActive
                ) {

                    if (data.deterministic) {

                        setMode(
                            "Deterministic"
                        );

                    }
                    else if (
                        data.mcp_agent
                    ) {

                        setMode(
                            "Knowledge Agent"
                        );

                    }
                    else if (
                        data.llm_used
                    ) {

                        setMode(
                            "Local AI"
                        );

                    }

                }


                (
                    data.tools_used
                    || []
                ).forEach(
                    addMeta
                );


                if (
                    data.planner_calls
                ) {

                    addMeta(
                        `${data.planner_calls} planner call${
                            data.planner_calls === 1
                                ? ""
                                : "s"
                        }`
                    );

                }

            }
        );


        source.addEventListener(
            "operation_proposed",
            event => {

                const data =
                    parse(event);

                operatorProposalActive =
                    true;

                setMode(
                    "Operator"
                );


                updateEvent(
                    "operation-plan",
                    "Operation plan",
                    (
                        data.plan
                        ? `${
                            data.plan.action
                        } · ${
                            data.plan.target
                        }`
                        : "Typed operation proposal"
                    ),
                    "done"
                );


                updateEvent(
                    "approval",
                    "Human approval",
                    "Waiting for your decision",
                    "working"
                );


                const title =
                    document.querySelector(
                        ".atlas-live-header strong"
                    );

                if (title) {

                    title.textContent =
                        "ATLAS operation awaiting approval";
                }


                addMeta(
                    "PydanticAI"
                );

                addMeta(
                    "atlas-operator MCP"
                );

                addMeta(
                    "SafeAction"
                );


                renderOperatorCard(
                    data
                );

            }
        );


        source.addEventListener(
            "operation_blocked",
            event => {

                const data =
                    parse(event);

                operatorProposalActive =
                    true;

                setMode(
                    "Operator"
                );


                updateEvent(
                    "operation-plan",
                    "Operation blocked",
                    (
                        data.message
                        || "ATLAS safety policy blocked the operation"
                    ),
                    "error"
                );

            }
        );


        source.addEventListener(
            "answer",
            event => {

                const data =
                    parse(event);

                if (
                    operatorProposalActive
                ) {
                    return;
                }

                const answer =
                    document.getElementById(
                        "atlasLiveAnswer"
                    );

                if (!answer) {
                    return;
                }

                answer.hidden = false;

                answer.textContent =
                    data.content
                    || "ATLAS returned no answer.";


                const latency =
                    Number(
                        data.latency_ms
                        || 0
                    );

                if (latency) {

                    addMeta(
                        `${latency.toFixed(1)} ms`
                    );

                }


                if (
                    data.model
                    && data.model
                    !== "atlas-semantic"
                ) {

                    addMeta(
                        data.model
                    );

                }

            }
        );


        source.addEventListener(
            "completed",
            () => {

                const dot =
                    document.querySelector(
                        ".atlas-live-header "
                        + ".os-thinking-dot"
                    );

                if (dot) {

                    dot.classList.add(
                        "is-complete"
                    );

                }

                closeSource();

            }
        );


        source.addEventListener(
            "error",
            event => {

                let message =
                    "ATLAS connection interrupted.";

                if (event.data) {

                    const data =
                        parse(event);

                    message =
                        data.message
                        || message;

                }

                updateEvent(
                    "error",
                    "Error",
                    message,
                    "error"
                );

                closeSource();

            }
        );

    }



    // ============================================================
    // ATLAS OPERATOR v0.1
    //
    // Deterministic operational intent routing.
    //
    // This is UI routing only. Security is enforced by the
    // backend SafeAction / Approval / Executor pipeline.
    // ============================================================

    function normalizeOperatorText(
        value
    ) {

        return String(
            value || ""
        )
            .normalize("NFD")
            .replace(
                /[\u0300-\u036f]/g,
                ""
            )
            .trim()
            .toLowerCase();
    }


    function parseOperatorCommand(
        question
    ) {

        const value =
            normalizeOperatorText(
                question
            );


        let match = null;


        // --------------------------------------------------------
        // systemd
        // --------------------------------------------------------

        match = value.match(
            /^(?:arranca|inicia|start)\s+(?:el\s+)?(?:servicio|service)\s+([a-z0-9][a-z0-9_.@:-]{0,127}\.service)$/
        );

        if (match) {
            return {
                action: "start service",
                target: match[1],
            };
        }


        match = value.match(
            /^(?:reinicia|restart)\s+(?:el\s+)?(?:servicio|service)\s+([a-z0-9][a-z0-9_.@:-]{0,127}\.service)$/
        );

        if (match) {
            return {
                action: "restart service",
                target: match[1],
            };
        }


        match = value.match(
            /^(?:deten|detiene|para|stop)\s+(?:el\s+)?(?:servicio|service)\s+([a-z0-9][a-z0-9_.@:-]{0,127}\.service)$/
        );

        if (match) {
            return {
                action: "stop service",
                target: match[1],
            };
        }


        // --------------------------------------------------------
        // Proxmox VM
        // --------------------------------------------------------

        match = value.match(
            /^(?:arranca|inicia|start)\s+(?:la\s+|el\s+)?(?:vm|maquina virtual)\s+([1-9][0-9]{0,8})$/
        );

        if (match) {
            return {
                action: "start vm",
                target: match[1],
            };
        }


        match = value.match(
            /^(?:reinicia|restart)\s+(?:la\s+|el\s+)?(?:vm|maquina virtual)\s+([1-9][0-9]{0,8})$/
        );

        if (match) {
            return {
                action: "restart vm",
                target: match[1],
            };
        }


        match = value.match(
            /^(?:deten|detiene|para|stop)\s+(?:la\s+|el\s+)?(?:vm|maquina virtual)\s+([1-9][0-9]{0,8})$/
        );

        if (match) {
            return {
                action: "stop vm",
                target: match[1],
            };
        }


        // --------------------------------------------------------
        // Proxmox LXC
        // --------------------------------------------------------

        match = value.match(
            /^(?:reinicia|restart)\s+(?:el\s+)?lxc\s+([1-9][0-9]{0,8})$/
        );

        if (match) {
            return {
                action: "restart lxc",
                target: match[1],
            };
        }


        // --------------------------------------------------------
        // Docker
        // --------------------------------------------------------

        match = value.match(
            /^(?:arranca|inicia|start)\s+(?:el\s+)?(?:contenedor\s+|container\s+)?([a-z0-9][a-z0-9_.-]{0,127})$/
        );

        if (match) {
            return {
                action: "start container",
                target: match[1],
            };
        }


        match = value.match(
            /^(?:reinicia|restart)\s+(?:el\s+)?(?:contenedor\s+|container\s+)?([a-z0-9][a-z0-9_.-]{0,127})$/
        );

        if (match) {
            return {
                action: "restart container",
                target: match[1],
            };
        }


        match = value.match(
            /^(?:deten|detiene|para|stop)\s+(?:el\s+)?(?:contenedor\s+|container\s+)?([a-z0-9][a-z0-9_.-]{0,127})$/
        );

        if (match) {
            return {
                action: "stop container",
                target: match[1],
            };
        }


        return null;
    }


    function escapeOperatorHTML(
        value
    ) {

        return String(
            value ?? ""
        )
            .replaceAll(
                "&",
                "&amp;"
            )
            .replaceAll(
                "<",
                "&lt;"
            )
            .replaceAll(
                ">",
                "&gt;"
            )
            .replaceAll(
                '"',
                "&quot;"
            )
            .replaceAll(
                "'",
                "&#039;"
            );
    }


    function completeOperatorHeader() {

        const dot =
            document.querySelector(
                ".atlas-live-header "
                + ".os-thinking-dot"
            );

        if (dot) {

            dot.classList.add(
                "is-complete"
            );
        }


        const title =
            document.querySelector(
                ".atlas-live-header strong"
            );

        if (title) {

            title.textContent =
                "ATLAS operation complete";
        }
    }


    function operatorError(
        detail
    ) {

        updateEvent(
            "operator-error",
            "Operation blocked",
            detail || "Operator request failed",
            "error"
        );

        completeOperatorHeader();
    }


    const OPERATOR_TOKEN_KEY =
        "atlas.operator.token";


    function clearOperatorToken() {

        sessionStorage.removeItem(
            OPERATOR_TOKEN_KEY
        );
    }


    function getStoredOperatorToken() {

        return String(
            sessionStorage.getItem(
                OPERATOR_TOKEN_KEY
            )
            || ""
        ).trim();
    }


    function setOperatorToken(
        token
    ) {

        const normalized =
            String(
                token
                || ""
            ).trim();


        if (!normalized) {

            throw new Error(
                "Operator authentication required"
            );
        }


        sessionStorage.setItem(
            OPERATOR_TOKEN_KEY,
            normalized
        );


        return normalized;
    }


    function getOperatorToken() {

        const token =
            getStoredOperatorToken();


        if (!token) {

            throw new Error(
                "Operator authentication required"
            );
        }


        return token;
    }


    async function operatorFetch(
        url,
        options = {}
    ) {

        const token =
            getOperatorToken();

        const headers =
            new Headers(
                options.headers
                || {}
            );

        headers.set(
            "Authorization",
            `Bearer ${token}`
        );


        const response =
            await fetch(
                url,
                {
                    ...options,
                    headers,
                }
            );


        if (
            response.status === 401
        ) {

            clearOperatorToken();

            if (
                typeof lockOperatorControlCenter
                === "function"
            ) {

                lockOperatorControlCenter(
                    "Operator authentication expired. Unlock again."
                );
            }
        }


        return response;
    }


    async function fetchOperatorActionState(
        actionId
    ) {

        const response =
            await operatorFetch(
                `/api/operator/actions/${
                    encodeURIComponent(actionId)
                }`
            );

        if (!response.ok) {
            return null;
        }

        return await response.json();
    }


    async function fetchOperatorExecutionState(
        actionId
    ) {

        const payload =
            await fetchOperatorActionState(
                actionId
            );

        return (
            payload?.execution_state
            || null
        );
    }


    function renderOperatorVerifiedRecovery(
        statusNode,
        resultNode,
        actionsNode,
        payload
    ) {

        const state =
            payload.execution_state
            || {};

        const verification =
            payload.verification
            || state.verification
            || {};

        const history =
            payload.verification_history
            || [];

        const observed =
            escapeOperatorHTML(
                verification.observed_state
                || "verified"
            );

        const expected =
            escapeOperatorHTML(
                verification.expected_state
                || "expected state"
            );


        statusNode.textContent =
            "VERIFIED";

        statusNode.className =
            "atlas-operator-status success";

        actionsNode.hidden = true;
        actionsNode.innerHTML = "";

        resultNode.hidden = false;

        resultNode.className =
            "atlas-operator-result";

        resultNode.innerHTML = `
            <strong>
                ✓ Recovery verified
            </strong>

            <span>
                ATLAS independently observed the
                expected infrastructure state.
            </span>

            <div class="atlas-operator-recovery-grid">

                <div>
                    <small>Expected</small>
                    <strong>${expected}</strong>
                </div>

                <div>
                    <small>Observed</small>
                    <strong>${observed}</strong>
                </div>

                <div>
                    <small>Verification attempts</small>
                    <strong>${history.length}</strong>
                </div>

            </div>
        `;
    }


    function renderOperatorRecoveryRequired(
        statusNode,
        resultNode,
        actionsNode,
        actionId,
        executionState,
        verificationHistory = []
    ) {

        const state =
            executionState
            || {};

        const verification =
            state.verification
            || {};

        const expected =
            escapeOperatorHTML(
                verification.expected_state
                || "unknown"
            );

        const observed =
            escapeOperatorHTML(
                verification.observed_state
                || "unknown"
            );

        const detail =
            escapeOperatorHTML(
                verification.detail
                || (
                    "Execution completed but "
                    + "post-action verification "
                    + "did not confirm the "
                    + "expected state."
                )
            );

        const history =
            Array.isArray(
                verificationHistory
            )
                ? verificationHistory
                : [];

        const attempts =
            history.length
            || (
                verification.status
                ? 1
                : 0
            );


        statusNode.textContent =
            "RECOVERY REQUIRED";

        statusNode.className =
            "atlas-operator-status recovery";

        resultNode.hidden = false;

        resultNode.className =
            "atlas-operator-result recovery";

        resultNode.innerHTML = `
            <strong>
                ⚠ Execution requires recovery verification
            </strong>

            <span>
                ${detail}
            </span>

            <div class="atlas-operator-recovery-grid">

                <div>
                    <small>Expected</small>
                    <strong>${expected}</strong>
                </div>

                <div>
                    <small>Observed</small>
                    <strong>${observed}</strong>
                </div>

                <div>
                    <small>Verification attempts</small>
                    <strong>${attempts}</strong>
                </div>

            </div>

            <span class="atlas-operator-recovery-note">
                Re-verify only observes the target.
                It does not repeat the original action
                and does not perform rollback.
            </span>
        `;


        actionsNode.hidden = false;

        actionsNode.innerHTML = `
            <button
                type="button"
                class="atlas-operator-reverify"
                data-role="reverify"
            >
                Re-verify
            </button>
        `;


        const reverify =
            actionsNode.querySelector(
                '[data-role="reverify"]'
            );


        reverify.addEventListener(
            "click",
            async () => {

                reverify.disabled = true;

                reverify.textContent =
                    "Re-verifying…";

                updateEvent(
                    "verification",
                    "Manual re-verification",
                    "Observing infrastructure state",
                    "working"
                );


                try {

                    const response =
                        await operatorFetch(
                            `/api/operator/actions/${
                                encodeURIComponent(
                                    actionId
                                )
                            }/reverify`,
                            {
                                method: "POST",
                            }
                        );

                    const data =
                        await response.json();


                    if (!response.ok) {

                        throw new Error(
                            data.detail
                            || (
                                "Manual re-verification "
                                + "failed"
                            )
                        );
                    }


                    if (
                        data.status
                        === "VERIFIED"
                    ) {

                        renderOperatorVerifiedRecovery(
                            statusNode,
                            resultNode,
                            actionsNode,
                            data
                        );

                        updateEvent(
                            "verification",
                            "Manual re-verification",
                            "Expected state independently confirmed",
                            "done"
                        );

                        completeOperatorHeader();

                        return;
                    }


                    renderOperatorRecoveryRequired(
                        statusNode,
                        resultNode,
                        actionsNode,
                        actionId,
                        data.execution_state,
                        data.verification_history
                        || []
                    );

                    updateEvent(
                        "verification",
                        "Manual re-verification",
                        "Recovery is still required",
                        "error"
                    );

                    completeOperatorHeader();

                }
                catch (error) {

                    reverify.disabled = false;

                    reverify.textContent =
                        "Re-verify";

                    operatorError(
                        error.message
                    );
                }
            }
        );


        return true;
    }


    function renderOperatorRecoveryState(
        statusNode,
        resultNode,
        actionsNode,
        executionState,
        fallback
    ) {

        const state =
            executionState
            || {};

        const history =
            state.history
            || null;


        if (
            state.state === "RESERVED"
            && !history
        ) {

            statusNode.textContent =
                "OUTCOME UNKNOWN";

            statusNode.className =
                "atlas-operator-status pending";

            actionsNode.hidden = true;

            resultNode.hidden = false;

            resultNode.innerHTML = `
                <strong>
                    ⚠ Execution reserved
                </strong>

                <span>
                    ATLAS has a durable execution
                    reservation but no recorded result.
                    Do not retry automatically.
                    Verify the real target state first.
                </span>
            `;

            return true;
        }


        if (
            state.state === "RECORDED"
            && history
        ) {

            const recordedStatus =
                String(
                    history.status
                    || "RECORDED"
                ).toUpperCase();

            statusNode.textContent =
                recordedStatus;

            statusNode.className = (
                recordedStatus === "SUCCESS"
                ? "atlas-operator-status success"
                : "atlas-operator-status failed"
            );

            actionsNode.hidden = true;

            resultNode.hidden = false;

            resultNode.textContent = (
                history.result
                || fallback
                || "Execution result recorded."
            );

            return true;
        }


        return false;
    }


    function renderOperatorCard(
        payload
    ) {

        const request =
            payload.action_request
            || {};

        const safety =
            payload.safety
            || {};

        const answer =
            document.getElementById(
                "atlasLiveAnswer"
            );

        if (!answer) {
            return;
        }


        const actionId =
            escapeOperatorHTML(
                request.id
            );

        const action =
            escapeOperatorHTML(
                request.action
            );

        const target =
            escapeOperatorHTML(
                request.target
            );

        const risk =
            escapeOperatorHTML(
                request.risk
                || safety.risk
                || "UNKNOWN"
            );

        const rollback =
            escapeOperatorHTML(
                request.rollback
                || "—"
            );

        const targetState =
            escapeOperatorHTML(
                payload.target_state
                || "UNKNOWN"
            );


        answer.hidden = false;

        answer.innerHTML = `
            <div
                class="atlas-operator-card"
                data-action-id="${actionId}"
            >

                <div class="atlas-operator-heading">

                    <span class="atlas-operator-kicker">
                        ATLAS · OPERATION REQUEST
                    </span>

                    <span
                        class="atlas-operator-status pending"
                        data-role="status"
                    >
                        PENDING APPROVAL
                    </span>

                </div>


                <div class="atlas-operator-command">
                    ${action.toUpperCase()}
                </div>

                <div class="atlas-operator-target">
                    ${target}
                </div>


                <div class="atlas-operator-grid">

                    <div>
                        <small>Current state</small>
                        <strong>${targetState}</strong>
                    </div>

                    <div>
                        <small>Risk</small>
                        <strong>${risk}</strong>
                    </div>

                    <div>
                        <small>Safety</small>
                        <strong>
                            ${safety.validated
                                ? "✓ Validated"
                                : "Unknown"}
                        </strong>
                    </div>

                    <div>
                        <small>Rollback</small>
                        <strong>${rollback}</strong>
                    </div>

                </div>


                <div
                    class="atlas-operator-result"
                    data-role="result"
                    hidden
                ></div>


                <div
                    class="atlas-operator-actions"
                    data-role="actions"
                >

                    <button
                        type="button"
                        class="atlas-operator-reject"
                        data-role="reject"
                    >
                        Reject
                    </button>

                    <button
                        type="button"
                        class="atlas-operator-approve"
                        data-role="approve"
                    >
                        Approve
                    </button>

                </div>

            </div>
        `;


        const card =
            answer.querySelector(
                ".atlas-operator-card"
            );

        const approve =
            card.querySelector(
                '[data-role="approve"]'
            );

        const reject =
            card.querySelector(
                '[data-role="reject"]'
            );

        const status =
            card.querySelector(
                '[data-role="status"]'
            );

        const result =
            card.querySelector(
                '[data-role="result"]'
            );

        const actions =
            card.querySelector(
                '[data-role="actions"]'
            );


        reject.addEventListener(
            "click",
            async () => {

                approve.disabled = true;
                reject.disabled = true;

                updateEvent(
                    "approval",
                    "Human approval",
                    "Rejecting operation",
                    "working"
                );


                try {

                    const response =
                        await operatorFetch(
                            `/api/operator/actions/${request.id}/reject`,
                            {
                                method: "POST",
                            }
                        );

                    const data =
                        await response.json();


                    if (!response.ok) {

                        throw new Error(
                            data.detail
                            || "Could not reject action"
                        );
                    }


                    status.textContent =
                        "REJECTED";

                    status.className =
                        "atlas-operator-status rejected";

                    actions.hidden = true;

                    result.hidden = false;

                    result.textContent =
                        "Operation rejected. "
                        + "No infrastructure change was made.";


                    updateEvent(
                        "approval",
                        "Human approval",
                        "Operation rejected",
                        "done"
                    );

                    completeOperatorHeader();

                }
                catch (error) {

                    approve.disabled = false;
                    reject.disabled = false;

                    operatorError(
                        error.message
                    );
                }

            }
        );


        approve.addEventListener(
            "click",
            async () => {

                approve.disabled = true;
                reject.disabled = true;

                approve.textContent =
                    "Executing…";


                updateEvent(
                    "approval",
                    "Human approval",
                    "Approved by operator",
                    "done"
                );

                updateEvent(
                    "execution",
                    "Executing action",
                    `${request.action} · ${request.target}`,
                    "working"
                );


                try {

                    const response =
                        await operatorFetch(
                            `/api/operator/actions/${request.id}/approve`,
                            {
                                method: "POST",
                            }
                        );

                    const data =
                        await response.json();


                    if (
                        response.status === 401
                    ) {

                        status.textContent =
                            "AUTH REQUIRED";

                        status.className =
                            "atlas-operator-status pending";

                        approve.disabled = false;
                        reject.disabled = false;

                        approve.textContent =
                            "Approve";

                        actions.hidden = false;

                        result.hidden = false;

                        result.textContent =
                            "Operator authentication failed. "
                            + "Retry to enter the current token.";

                        updateEvent(
                            "approval",
                            "Operator authentication",
                            "Authentication required",
                            "error"
                        );

                        completeOperatorHeader();

                        return;
                    }


                    if (!response.ok) {

                        throw new Error(
                            data.detail
                            || "Execution failed"
                        );
                    }


                    const execution =
                        data.execution
                        || {};

                    const executionState =
                        data.execution_state
                        || {};

                    const evidence =
                        execution.evidence
                        || [];


                    if (
                        executionState.state
                        === "RECOVERY_REQUIRED"
                    ) {

                        renderOperatorRecoveryRequired(
                            status,
                            result,
                            actions,
                            request.id,
                            executionState,
                            data.verification_history
                            || []
                        );

                        updateEvent(
                            "verification",
                            "Post-action verification",
                            "Manual recovery verification required",
                            "error"
                        );

                        completeOperatorHeader();

                        return;
                    }


                    if (
                        execution.status
                        !== "SUCCESS"
                    ) {

                        if (
                            renderOperatorRecoveryState(
                                status,
                                result,
                                actions,
                                executionState,
                                execution.result
                            )
                        ) {

                            updateEvent(
                                "verification",
                                "Execution recovery",
                                "Manual verification required",
                                "error"
                            );

                            completeOperatorHeader();

                            return;
                        }


                        status.textContent = (
                            execution.status
                            || "BLOCKED"
                        );

                        status.className =
                            "atlas-operator-status failed";

                        actions.hidden = true;

                        result.hidden = false;


                        if (
                            executionState.state
                            === "READY"
                        ) {

                            result.textContent =
                                "Execution was blocked before "
                                + "a durable reservation. "
                                + "No infrastructure command "
                                + "was issued by ATLAS.";
                        }
                        else {

                            result.textContent = (
                                execution.result
                                || "Execution blocked"
                            );
                        }


                        updateEvent(
                            "execution",
                            "Executing action",
                            (
                                execution.result
                                || "Execution blocked"
                            ),
                            "error"
                        );

                        completeOperatorHeader();

                        return;
                    }


                    updateEvent(
                        "execution",
                        "Executing action",
                        "Infrastructure action completed",
                        "done"
                    );

                    updateEvent(
                        "verification",
                        "Post-action verification",
                        (
                            evidence[
                                evidence.length - 1
                            ]
                            || "Verification passed"
                        ),
                        "done"
                    );


                    status.textContent =
                        "SUCCESS";

                    status.className =
                        "atlas-operator-status success";

                    actions.hidden = true;

                    result.hidden = false;

                    result.innerHTML = `
                        <strong>
                            ✓ Operation completed
                        </strong>

                        <span>
                            ${escapeOperatorHTML(
                                request.target
                            )}
                            is verified after execution.
                        </span>
                    `;


                    addMeta(
                        "Operator"
                    );

                    addMeta(
                        `${request.risk} risk`
                    );

                    addMeta(
                        "human-approved"
                    );

                    completeOperatorHeader();

                }
                catch (error) {

                    let recoveredPayload = null;

                    try {

                        recoveredPayload = (
                            await fetchOperatorActionState(
                                request.id
                            )
                        );
                    }
                    catch (
                        recoveryError
                    ) {

                        recoveredPayload = null;
                    }


                    const recoveredState = (
                        recoveredPayload
                        ?.execution_state
                        || null
                    );


                    if (
                        recoveredState?.state
                        === "RECOVERY_REQUIRED"
                    ) {

                        renderOperatorRecoveryRequired(
                            status,
                            result,
                            actions,
                            request.id,
                            recoveredState,
                            recoveredPayload
                                ?.verification_history
                            || []
                        );

                        updateEvent(
                            "verification",
                            "Execution recovery",
                            "Manual recovery verification required",
                            "error"
                        );

                        completeOperatorHeader();

                        return;
                    }


                    if (
                        renderOperatorRecoveryState(
                            status,
                            result,
                            actions,
                            recoveredState,
                            error.message
                        )
                    ) {

                        updateEvent(
                            "verification",
                            "Execution recovery",
                            "Manual verification required",
                            "error"
                        );

                        completeOperatorHeader();

                        return;
                    }


                    status.textContent =
                        "STATUS UNKNOWN";

                    status.className =
                        "atlas-operator-status pending";

                    actions.hidden = true;

                    result.hidden = false;

                    result.innerHTML = `
                        <strong>
                            ⚠ Execution status could not
                            be confirmed
                        </strong>

                        <span>
                            Do not retry automatically.
                            Check the action state and verify
                            the real infrastructure state
                            before issuing another operation.
                        </span>
                    `;

                    operatorError(
                        error.message
                    );
                }

            }
        );
    }


    async function startOperator(
        question,
        command
    ) {

        closeSource();

        createActivity();

        setMode(
            "Operator"
        );


        updateEvent(
            "request",
            "Operational request received",
            question,
            "done"
        );

        updateEvent(
            "target",
            "Resolving target",
            command.target,
            "working"
        );


        try {

            const response =
                await operatorFetch(
                    "/api/operator/actions/propose",
                    {
                        method:
                            "POST",

                        headers: {
                            "Content-Type":
                                "application/json",
                        },

                        body:
                            JSON.stringify(
                                command
                            ),
                    }
                );

            const data =
                await response.json();


            if (!response.ok) {

                throw new Error(
                    data.detail
                    || "Operator request failed"
                );
            }


            if (
                data.status
                !== "PENDING_APPROVAL"
            ) {

                throw new Error(
                    data.status
                    || "Operator request blocked"
                );
            }


            updateEvent(
                "target",
                "Target resolved",
                `${
                    data.action_request.target
                } · ${
                    data.target_state
                }`,
                "done"
            );


            updateEvent(
                "safety",
                "Safety gate",
                `${
                    data.safety.risk
                } risk · validated`,
                "done"
            );


            updateEvent(
                "approval",
                "Human approval",
                "Waiting for your decision",
                "working"
            );


            addMeta(
                "SafeAction"
            );

            addMeta(
                "Human approval"
            );


            renderOperatorCard(
                data
            );

        }
        catch (error) {

            updateEvent(
                "target",
                "Target resolution",
                error.message,
                "error"
            );

            operatorError(
                error.message
            );
        }
    }


    // ============================================================
    // ATLAS OPERATOR CONTROL CENTER V1
    // ============================================================

    const operatorControlCenter =
        document.getElementById(
            "operatorControlCenter"
        );

    const operatorControlRefresh =
        document.getElementById(
            "operatorControlRefresh"
        );

    const operatorControlAuthState =
        document.getElementById(
            "operatorControlAuthState"
        );

    const operatorControlToken =
        document.getElementById(
            "operatorControlToken"
        );

    const operatorControlUnlock =
        document.getElementById(
            "operatorControlUnlock"
        );

    const operatorControlLock =
        document.getElementById(
            "operatorControlLock"
        );

    const operatorControlFilter =
        document.getElementById(
            "operatorControlFilter"
        );

    const operatorControlSummary =
        document.getElementById(
            "operatorControlSummary"
        );

    const operatorControlBody =
        document.getElementById(
            "operatorControlBody"
        );

    const operatorControlList =
        document.getElementById(
            "operatorControlList"
        );

    const operatorControlDetail =
        document.getElementById(
            "operatorControlDetail"
        );

    const operatorControlMessage =
        document.getElementById(
            "operatorControlMessage"
        );

    let operatorControlLoaded = false;


    function setOperatorControlAuthState(
        unlocked
    ) {

        if (operatorControlAuthState) {

            operatorControlAuthState.textContent =
                unlocked
                ? "Unlocked"
                : "Locked";

            operatorControlAuthState.className =
                "operator-auth-state "
                + (
                    unlocked
                    ? "unlocked"
                    : "locked"
                );
        }


        if (operatorControlToken) {

            operatorControlToken.hidden =
                unlocked;

            if (!unlocked) {

                operatorControlToken.value =
                    "";
            }
        }


        if (operatorControlUnlock) {

            operatorControlUnlock.hidden =
                unlocked;
        }


        if (operatorControlLock) {

            operatorControlLock.hidden =
                !unlocked;
        }


        if (operatorControlRefresh) {

            operatorControlRefresh.disabled =
                !unlocked;

            operatorControlRefresh.textContent =
                "Refresh";
        }
    }


    function lockOperatorControlCenter(
        message = (
            "Operator authentication is required "
            + "to inspect operational history."
        )
    ) {

        clearOperatorToken();

        operatorControlLoaded = false;

        setOperatorControlAuthState(
            false
        );


        if (operatorControlSummary) {

            operatorControlSummary.hidden =
                true;
        }


        if (operatorControlBody) {

            operatorControlBody.hidden =
                true;
        }


        if (operatorControlList) {

            operatorControlList.innerHTML =
                "";
        }


        if (operatorControlDetail) {

            operatorControlDetail.innerHTML = `
                <div class="operator-control-empty">
                    Unlock Operator to inspect
                    operational state.
                </div>
            `;
        }


        if (operatorControlMessage) {

            operatorControlMessage.hidden =
                false;

            operatorControlMessage.textContent =
                message;
        }
    }


    async function unlockOperatorControlCenter() {

        if (!operatorControlToken) {
            return;
        }


        const token =
            String(
                operatorControlToken.value
                || ""
            ).trim();


        if (!token) {

            if (operatorControlMessage) {

                operatorControlMessage.hidden =
                    false;

                operatorControlMessage.textContent =
                    "Enter the Operator token to unlock.";
            }

            operatorControlToken.focus();

            return;
        }


        if (operatorControlUnlock) {

            operatorControlUnlock.disabled =
                true;

            operatorControlUnlock.textContent =
                "Unlocking…";
        }


        operatorControlToken.disabled =
            true;


        try {

            const headers =
                new Headers();

            headers.set(
                "Authorization",
                "Bearer " + token
            );


            const response =
                await fetch(
                    "/api/operator/actions?limit=1",
                    {
                        headers,
                    }
                );


            let payload = {};

            try {

                payload =
                    await response.json();
            }

            catch (error) {

                payload = {};
            }


            if (!response.ok) {

                throw new Error(
                    payload.detail
                    || "Operator authentication failed"
                );
            }


            setOperatorToken(
                token
            );

            operatorControlToken.value =
                "";

            setOperatorControlAuthState(
                true
            );


            await loadOperatorControlCenter();

        }

        catch (error) {

            clearOperatorToken();

            setOperatorControlAuthState(
                false
            );


            if (operatorControlMessage) {

                operatorControlMessage.hidden =
                    false;

                operatorControlMessage.textContent =
                    error.message;
            }
        }

        finally {

            operatorControlToken.disabled =
                false;

            if (operatorControlUnlock) {

                operatorControlUnlock.disabled =
                    false;

                operatorControlUnlock.textContent =
                    "Unlock";
            }
        }
    }


    function operatorStateClass(
        state
    ) {

        return String(
            state
            || "UNKNOWN"
        )
            .toLowerCase()
            .replace(
                /[^a-z0-9_-]/g,
                "-"
            );
    }


    function operatorTimestamp(
        value
    ) {

        if (!value) {
            return "—";
        }

        const date =
            new Date(value);

        if (
            Number.isNaN(
                date.getTime()
            )
        ) {
            return String(value);
        }

        return date.toLocaleString();
    }


    function renderOperatorControlSummary(
        summary
    ) {

        if (!operatorControlSummary) {
            return;
        }

        const entries =
            Object.entries(
                summary
                || {}
            );

        operatorControlSummary.hidden = false;

        if (!entries.length) {

            operatorControlSummary.innerHTML = `
                <span>
                    No operations recorded
                </span>
            `;

            return;
        }


        operatorControlSummary.innerHTML =
            entries
                .map(
                    ([state, count]) => `
                        <span
                            class="
                                operator-summary-chip
                                ${operatorStateClass(state)}
                            "
                        >
                            <strong>
                                ${escapeOperatorHTML(count)}
                            </strong>

                            ${escapeOperatorHTML(state)}
                        </span>
                    `
                )
                .join("");
    }


    function operatorDetailRow(
        label,
        value
    ) {

        return `
            <div>
                <small>
                    ${escapeOperatorHTML(label)}
                </small>

                <strong>
                    ${escapeOperatorHTML(
                        value ?? "—"
                    )}
                </strong>
            </div>
        `;
    }


    async function loadOperatorControlDetail(
        actionId
    ) {

        if (!operatorControlDetail) {
            return;
        }

        operatorControlDetail.innerHTML = `
            <div class="operator-control-empty">
                Loading operation…
            </div>
        `;


        const response =
            await operatorFetch(
                `/api/operator/actions/${
                    encodeURIComponent(
                        actionId
                    )
                }`
            );

        const payload =
            await response.json();


        if (!response.ok) {
            throw new Error(
                payload.detail
                || "Could not load operation"
            );
        }


        const action =
            payload.action_request
            || {};

        const execution =
            payload.execution_state
            || {};

        const verification =
            execution.verification
            || {};

        const history =
            payload.verification_history
            || [];

        const rawState =
            String(
                execution.state
                || action.status
                || "UNKNOWN"
            ).toUpperCase();

        const state = (
            rawState === "NOT_READY"
            ? String(
                action.status
                || "UNKNOWN"
            ).toUpperCase()
            : rawState
        );


        const verificationRows =
            history.length
            ? history
                .map(
                    item => `
                        <div class="operator-audit-entry">

                            <div>
                                <span
                                    class="
                                        operator-state
                                        ${operatorStateClass(
                                            item.status
                                        )}
                                    "
                                >
                                    ${escapeOperatorHTML(
                                        item.status
                                    )}
                                </span>

                                <small>
                                    ${escapeOperatorHTML(
                                        operatorTimestamp(
                                            item.verified_at
                                        )
                                    )}
                                </small>
                            </div>

                            <p>
                                ${escapeOperatorHTML(
                                    item.detail
                                    || "No detail"
                                )}
                            </p>

                            <small>
                                ${
                                    escapeOperatorHTML(
                                        item.source
                                        || "POST_EXECUTION"
                                    )
                                }
                                ${
                                    item.requested_by
                                    ? " · "
                                        + escapeOperatorHTML(
                                            item.requested_by
                                        )
                                    : ""
                                }
                            </small>

                        </div>
                    `
                )
                .join("")
            : `
                <div class="operator-control-empty">
                    No verification attempts recorded.
                </div>
            `;


        let actionControls = "";


        if (
            state
            === "PENDING_APPROVAL"
        ) {

            actionControls = `
                <div class="operator-detail-actions">

                    <button
                        type="button"
                        data-operator-action="reject"
                    >
                        Reject
                    </button>

                    <button
                        type="button"
                        class="primary"
                        data-operator-action="approve"
                    >
                        Approve
                    </button>

                </div>
            `;
        }


        if (
            state
            === "RECOVERY_REQUIRED"
        ) {

            actionControls = `
                <div class="operator-detail-actions">

                    <button
                        type="button"
                        class="primary"
                        data-operator-action="reverify"
                    >
                        Re-verify
                    </button>

                </div>
            `;
        }


        operatorControlDetail.innerHTML = `
            <div class="operator-detail-heading">

                <div>
                    <small>
                        ${escapeOperatorHTML(
                            action.id
                            || actionId
                        )}
                    </small>

                    <h4>
                        ${escapeOperatorHTML(
                            action.action
                            || "Operation"
                        )}
                    </h4>

                    <p>
                        ${escapeOperatorHTML(
                            action.target
                            || "—"
                        )}
                    </p>
                </div>

                <span
                    class="
                        operator-state
                        ${operatorStateClass(state)}
                    "
                >
                    ${escapeOperatorHTML(state)}
                </span>

            </div>


            <div class="operator-detail-grid">

                ${operatorDetailRow(
                    "Risk",
                    action.risk
                )}

                ${operatorDetailRow(
                    "Created",
                    operatorTimestamp(
                        action.created_at
                    )
                )}

                ${operatorDetailRow(
                    "Approved by",
                    action.approved_by
                )}

                ${operatorDetailRow(
                    "Approved at",
                    operatorTimestamp(
                        action.approved_at
                    )
                )}

                ${operatorDetailRow(
                    "Executed",
                    operatorTimestamp(
                        execution.history
                            ?.executed_at
                    )
                )}

                ${operatorDetailRow(
                    "Verified",
                    operatorTimestamp(
                        verification.verified_at
                    )
                )}

                ${operatorDetailRow(
                    "Expected",
                    verification.expected_state
                )}

                ${operatorDetailRow(
                    "Observed",
                    verification.observed_state
                )}

            </div>


            ${
                execution.history
                ?.result
                ? `
                    <div class="operator-detail-result">
                        <small>
                            Execution result
                        </small>

                        <p>
                            ${escapeOperatorHTML(
                                execution.history.result
                            )}
                        </p>
                    </div>
                `
                : ""
            }


            ${
                verification.detail
                ? `
                    <div class="operator-detail-result">
                        <small>
                            Verification
                        </small>

                        <p>
                            ${escapeOperatorHTML(
                                verification.detail
                            )}
                        </p>
                    </div>
                `
                : ""
            }


            ${actionControls}


            <div class="operator-audit">

                <div class="operator-audit-heading">
                    Verification history
                </div>

                ${verificationRows}

            </div>
        `;


        const controls = [
            ...operatorControlDetail
                .querySelectorAll(
                    "[data-operator-action]"
                )
        ];


        controls.forEach(
            control => {

                control.addEventListener(
                    "click",
                    async () => {

                        const operation =
                            control.dataset
                                .operatorAction;


                        controls.forEach(
                            item => {
                                item.disabled = true;
                            }
                        );


                        try {

                            let endpoint = "";


                            if (
                                operation
                                === "approve"
                            ) {

                                endpoint =
                                    `/api/operator/actions/${
                                        encodeURIComponent(
                                            actionId
                                        )
                                    }/approve`;
                            }

                            else if (
                                operation
                                === "reject"
                            ) {

                                endpoint =
                                    `/api/operator/actions/${
                                        encodeURIComponent(
                                            actionId
                                        )
                                    }/reject`;
                            }

                            else if (
                                operation
                                === "reverify"
                            ) {

                                endpoint =
                                    `/api/operator/actions/${
                                        encodeURIComponent(
                                            actionId
                                        )
                                    }/reverify`;
                            }

                            else {

                                throw new Error(
                                    "Unknown operator action"
                                );
                            }


                            const actionResponse =
                                await operatorFetch(
                                    endpoint,
                                    {
                                        method: "POST",
                                    }
                                );


                            const actionPayload =
                                await actionResponse.json();


                            if (
                                !actionResponse.ok
                            ) {

                                throw new Error(
                                    actionPayload.detail
                                    || (
                                        "Operator action "
                                        + "failed"
                                    )
                                );
                            }


                            await loadOperatorControlCenter();

                            await loadOperatorControlDetail(
                                actionId
                            );

                        }
                        catch (error) {

                            controls.forEach(
                                item => {
                                    item.disabled = false;
                                }
                            );


                            if (
                                operatorControlMessage
                            ) {

                                operatorControlMessage.hidden =
                                    false;

                                operatorControlMessage.textContent =
                                    error.message;
                            }
                        }
                    }
                );
            }
        );
    }


    async function loadOperatorControlCenter() {

        if (
            !operatorControlCenter
            || !operatorControlList
        ) {
            return;
        }


        if (operatorControlRefresh) {
            operatorControlRefresh.disabled =
                true;

            operatorControlRefresh.textContent =
                "Refreshing…";
        }


        try {

            const selectedState =
                operatorControlFilter
                    ?.value
                || "ALL";

            const query =
                selectedState === "ALL"
                ? ""
                : (
                    "?state="
                    + encodeURIComponent(
                        selectedState
                    )
                );


            const response =
                await operatorFetch(
                    "/api/operator/actions"
                    + query
                );

            const payload =
                await response.json();


            if (!response.ok) {
                throw new Error(
                    payload.detail
                    || (
                        "Could not load "
                        + "Operator history"
                    )
                );
            }


            operatorControlLoaded = true;

            if (operatorControlMessage) {
                operatorControlMessage.hidden =
                    true;
            }

            if (operatorControlBody) {
                operatorControlBody.hidden =
                    false;
            }


            renderOperatorControlSummary(
                payload.summary
                || {}
            );


            const actions =
                payload.actions
                || [];


            if (!actions.length) {

                operatorControlList.innerHTML = `
                    <div class="operator-control-empty">
                        No operations match this filter.
                    </div>
                `;

                return;
            }


            operatorControlList.innerHTML =
                actions
                    .map(
                        item => {

                            const action =
                                item.action_request
                                || {};

                            const state =
                                item.state
                                || "UNKNOWN";

                            return `
                                <button
                                    type="button"
                                    class="operator-operation-row"
                                    data-action-id="${
                                        escapeOperatorHTML(
                                            item.id
                                        )
                                    }"
                                >

                                    <span
                                        class="
                                            operator-state
                                            ${operatorStateClass(
                                                state
                                            )}
                                        "
                                    >
                                        ${escapeOperatorHTML(
                                            state
                                        )}
                                    </span>

                                    <strong>
                                        ${escapeOperatorHTML(
                                            action.action
                                            || "operation"
                                        )}
                                    </strong>

                                    <span>
                                        ${escapeOperatorHTML(
                                            action.target
                                            || "—"
                                        )}
                                    </span>

                                    <small>
                                        ${escapeOperatorHTML(
                                            operatorTimestamp(
                                                action.created_at
                                            )
                                        )}
                                    </small>

                                </button>
                            `;
                        }
                    )
                    .join("");


            operatorControlList
                .querySelectorAll(
                    "[data-action-id]"
                )
                .forEach(
                    row => {

                        row.addEventListener(
                            "click",
                            async () => {

                                try {

                                    await loadOperatorControlDetail(
                                        row.dataset
                                            .actionId
                                    );

                                }
                                catch (error) {

                                    if (
                                        operatorControlMessage
                                    ) {

                                        operatorControlMessage.hidden =
                                            false;

                                        operatorControlMessage.textContent =
                                            error.message;
                                    }
                                }
                            }
                        );
                    }
                );

        }
        catch (error) {

            if (
                operatorControlMessage
            ) {

                operatorControlMessage.hidden =
                    false;

                operatorControlMessage.textContent =
                    error.message;
            }

        }
        finally {

            if (operatorControlRefresh) {

                operatorControlRefresh.disabled =
                    !getStoredOperatorToken();

                operatorControlRefresh.textContent =
                    "Refresh";
            }
        }
    }


    if (operatorControlUnlock) {

        operatorControlUnlock.addEventListener(
            "click",
            unlockOperatorControlCenter
        );
    }


    if (operatorControlToken) {

        operatorControlToken.addEventListener(
            "keydown",
            event => {

                if (
                    event.key
                    === "Enter"
                ) {

                    event.preventDefault();

                    unlockOperatorControlCenter();
                }
            }
        );
    }


    if (operatorControlLock) {

        operatorControlLock.addEventListener(
            "click",
            () => {

                lockOperatorControlCenter(
                    "Operator locked. "
                    + "No operational action can be approved "
                    + "from this browser session."
                );
            }
        );
    }


    if (operatorControlRefresh) {

        operatorControlRefresh.addEventListener(
            "click",
            loadOperatorControlCenter
        );
    }


    if (operatorControlFilter) {

        operatorControlFilter.addEventListener(
            "change",
            () => {

                if (
                    operatorControlLoaded
                ) {
                    loadOperatorControlCenter();
                }
            }
        );
    }


    if (
        getStoredOperatorToken()
    ) {

        setOperatorControlAuthState(
            true
        );

        loadOperatorControlCenter();
    }

    else {

        setOperatorControlAuthState(
            false
        );
    }


    form.addEventListener(
        "submit",
        event => {

            event.preventDefault();

            const question =
                input.value.trim();

            if (!question) {
                input.focus();
                return;
            }

            startAsk(
                question
            );

        }
    );


    input.addEventListener(
        "keydown",
        event => {

            if (
                event.key === "Enter"
                && !event.shiftKey
            ) {

                event.preventDefault();

                form.requestSubmit();

            }

        }
    );

});
