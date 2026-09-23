import typer
from rich.console import Console
from rich.table import Table

from atlas.core.version import __version__

from atlas.services.system import SystemService
from atlas.services.docker import DockerService
from atlas.providers.homelab import HomelabProvider
from atlas.services.doctor import DoctorService
from atlas.renderers.docker import DockerRenderer
from atlas.services.storage import StorageService
from atlas.renderers.storage import StorageRenderer
from atlas.services.network import NetworkService
from atlas.renderers.network import NetworkRenderer
from atlas.services.infrastructure import InfrastructureService
from atlas.services.dev_context import DevContextService
from atlas.services.context.operational import OperationalContextBuilder
from atlas.services.ai.service import AIService
from atlas.services.ai.models import AIRequest

app = typer.Typer(
    help="ATLAS Infrastructure & Homelab Management Platform",
    no_args_is_help=True,
)

console = Console()


@app.callback()
def main():
    """ATLAS Infrastructure & Homelab Management Platform."""
    pass


@app.command()
def version():
    console.rule("[bold cyan]ATLAS[/bold cyan]")
    console.print(
        f"[green]Version[/green]: {__version__}"
    )
    console.print("[green]Author[/green] : Bruno Rossini")
    console.rule()


@app.command()
def system():
    service = SystemService()
    info = service.get_info()

    table = Table(title="ATLAS SYSTEM")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Hostname", info.hostname)
    table.add_row("OS", info.os_name)
    table.add_row("Kernel", info.kernel)
    table.add_row("Architecture", info.architecture)
    table.add_row("Python", info.python_version)
    table.add_row("Uptime", info.uptime)
    table.add_row("Boot Time", info.boot_time)
    table.add_row("Timezone", info.timezone)

    console.print(table)


@app.command()
def homelab():
    homelab = HomelabProvider().build()

    table = Table(title="ATLAS HOMELAB")
    table.add_column("Component")
    table.add_column("Status")

    table.add_row("Hostname", homelab.system.hostname)
    table.add_row("OS", homelab.system.os_name)
    table.add_row("Kernel", homelab.system.kernel)

    console.print(table)


@app.command()
def docker():
    service = DockerService()
    info = service.get_info()

    console.rule("[bold cyan]ATLAS DOCKER[/bold cyan]")

    console.print(f"Docker Version : {info.version}")
    console.print(f"Containers     : {info.total}")
    console.print(f"Running        : {info.running}")
    console.print(f"Exited         : {info.exited}")

    renderer = DockerRenderer()
    console.print(renderer.render(info))


@app.command()
def doctor():
    service = DoctorService()
    report = service.run()

    console.rule("[bold cyan]ATLAS DOCTOR[/bold cyan]")

    table = Table()
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Message")

    for check in report.checks:
        table.add_row(
            check.name,
            check.status,
            check.message,
        )

    console.print(table)


@app.command()
def storage():
    service = StorageService()
    info = service.get_info()

    renderer = StorageRenderer()
    console.print(renderer.render(info))


@app.command()
def network():
    service = NetworkService()
    info = service.get_info()

    console.rule("[bold cyan]ATLAS NETWORK[/bold cyan]")

    console.print(f"Hostname : {info.hostname}")
    console.print(f"Gateway  : {info.gateway}")
    console.print(f"DNS      : {', '.join(info.dns)}")

    renderer = NetworkRenderer()
    console.print(renderer.render(info))


@app.command()
def context(
    ai: bool = typer.Option(
        False,
        "--ai",
        help="Show compact operational context for ATLAS intelligence.",
    ),
):
    builder = OperationalContextBuilder()
    ctx = builder.build()

    console.rule("[bold cyan]ATLAS CONTEXT[/bold cyan]")

    system = ctx.get("system", {})

    infrastructure = ctx.get(
        "infrastructure",
        {},
    )

    # OperationalContextBuilder may expose the
    # infrastructure snapshot as an Infrastructure
    # model rather than a dictionary.
    if hasattr(infrastructure, "docker"):
        docker_obj = infrastructure.docker
        storage_obj = getattr(
            infrastructure,
            "storage",
            [],
        )

        docker = {
            "containers": getattr(
                docker_obj,
                "total",
                0,
            ),
            "running": getattr(
                docker_obj,
                "running",
                0,
            ),
        }

        storage = {
            "disks": len(
                storage_obj or []
            ),
        }

    elif isinstance(infrastructure, dict):
        docker = infrastructure.get(
            "docker",
            ctx.get("docker", {}),
        )

        storage = infrastructure.get(
            "storage",
            ctx.get("storage", {}),
        )

    else:
        docker = ctx.get(
            "docker",
            {},
        )

        storage = ctx.get(
            "storage",
            {},
        )

    assets = ctx.get(
        "assets",
        {},
    )

    if isinstance(assets, list):
        inventory = assets
    elif isinstance(assets, dict):
        inventory = assets.get("inventory", [])
    else:
        inventory = []


    console.print(
        f"[bold]System[/bold]   "
        f"{system.get('hostname', 'unknown')} | "
        f"{system.get('os', 'unknown')}"
    )

    docker_total = docker.get(
        "containers",
        0,
    )

    docker_running = docker.get(
        "running",
        0,
    )

    console.print(
        f"[bold]Docker[/bold]   "
        f"{docker_running}/{docker_total} running"
    )

    disk_count = storage.get(
        "disks",
        0,
    )

    console.print(
        f"[bold]Storage[/bold]  {disk_count} disks"
    )

    type_counts = {}

    for asset in inventory:

        if isinstance(asset, dict):
            asset_type = asset.get(
                "type",
                "unknown",
            )

        else:
            asset_type = getattr(
                asset,
                "type",
                "unknown",
            )

            if hasattr(
                asset_type,
                "value",
            ):
                asset_type = asset_type.value

        type_counts[asset_type] = (
            type_counts.get(
                asset_type,
                0,
            ) + 1
        )

    if type_counts:

        summary = " | ".join(
            f"{kind}: {count}"
            for kind, count in sorted(
                type_counts.items()
            )
        )

        console.print(
            f"[bold]Assets[/bold]   "
            f"{len(inventory)} total — {summary}"
        )

    health = ctx.get(
        "health",
        {},
    )

    findings = health.get(
        "findings",
        [],
    )

    if findings:
        console.print(
            f"[bold yellow]Health[/bold]   "
            f"{len(findings)} finding(s)"
        )
    else:
        console.print(
            "[bold green]Health[/bold green]   OK"
        )

    if ai:
        incidents = ctx.get(
            "incidents",
            [],
        )

        lifecycle = ctx.get(
            "lifecycle",
            {},
        )

        ai_runtime = ctx.get(
            "ai_runtime",
            {},
        )

        recommendations = ctx.get(
            "recommendations",
            [],
        )

        actions = ctx.get(
            "actions",
            [],
        )

        console.print()

        console.rule(
            "[bold magenta]NOC / OPERATIONAL INTELLIGENCE[/bold magenta]"
        )

        open_incidents = []

        for incident in incidents:

            if isinstance(
                incident,
                (tuple, list),
            ):
                status = (
                    incident[4]
                    if len(incident) > 4
                    else "UNKNOWN"
                )

                if status == "OPEN":
                    open_incidents.append(
                        incident
                    )

            elif isinstance(
                incident,
                dict,
            ):
                if incident.get(
                    "status"
                ) == "OPEN":
                    open_incidents.append(
                        incident
                    )

        critical = 0
        medium = 0
        warning = 0

        for incident in open_incidents:

            severity = "UNKNOWN"

            if isinstance(
                incident,
                (tuple, list),
            ):
                severity = (
                    incident[3]
                    if len(incident) > 3
                    else "UNKNOWN"
                )

            elif isinstance(
                incident,
                dict,
            ):
                severity = incident.get(
                    "severity",
                    "UNKNOWN",
                )

            severity = str(
                severity
            ).upper()

            if severity == "CRITICAL":
                critical += 1

            elif severity == "MEDIUM":
                medium += 1

            elif severity in (
                "WARNING",
                "HIGH",
            ):
                warning += 1

        console.print(
            f"[bold]Incidents[/bold] "
            f"{len(open_incidents)} open | "
            f"{critical} critical | "
            f"{warning} warning | "
            f"{medium} medium"
        )

        for incident in open_incidents:

            if isinstance(
                incident,
                (tuple, list),
            ):
                incident_id = (
                    incident[0]
                    if len(incident) > 0
                    else "UNKNOWN"
                )

                title = (
                    incident[1]
                    if len(incident) > 1
                    else "unknown"
                )

                asset = (
                    incident[2]
                    if len(incident) > 2
                    else "unknown"
                )

                severity = (
                    incident[3]
                    if len(incident) > 3
                    else "UNKNOWN"
                )

                impact_intelligence = (
                    incident[8]
                    if len(incident) > 8
                    else {}
                )

            else:
                incident_id = incident.get(
                    "incident_id",
                    incident.get(
                        "id",
                        "UNKNOWN",
                    ),
                )

                title = incident.get(
                    "title",
                    incident.get(
                        "name",
                        "unknown",
                    ),
                )

                asset = incident.get(
                    "asset",
                    "unknown",
                )

                severity = incident.get(
                    "severity",
                    "UNKNOWN",
                )

                impact_intelligence = incident.get(
                    "impact_intelligence",
                    {},
                )

            if not isinstance(
                impact_intelligence,
                dict,
            ):
                impact_intelligence = {}

            impact_severity = (
                impact_intelligence.get(
                    "severity"
                )
            )

            impact_score = (
                impact_intelligence.get(
                    "score"
                )
            )

            upstream = (
                impact_intelligence.get(
                    "upstream",
                    [],
                )
            )

            console.print()

            console.print(
                f"[bold cyan]{incident_id}[/bold cyan] "
                f"{title}"
            )

            console.print(
                f"  Asset       {asset}"
            )

            console.print(
                f"  Severity    {severity}"
            )

            if impact_severity:

                score_text = (
                    f" | score {impact_score}"
                    if impact_score is not None
                    else ""
                )

                console.print(
                    f"  Impact      "
                    f"{impact_severity}{score_text}"
                )

            if upstream:

                chain = " → ".join(
                    item.get(
                        "asset_id",
                        "unknown",
                    )
                    for item in upstream
                    if isinstance(
                        item,
                        dict,
                    )
                )

                if chain:
                    console.print(
                        f"  Upstream    {chain}"
                    )

        if isinstance(
            lifecycle,
            dict,
        ):
            state = lifecycle.get(
                "current_state"
            )

            if state:
                console.print(
                    f"[bold]Lifecycle[/bold]  "
                    f"{state}"
                )

        if isinstance(
            ai_runtime,
            dict,
        ):
            runtime_state = ai_runtime.get(
                "state",
                ai_runtime.get(
                    "status",
                    "UNKNOWN",
                ),
            )

            console.print(
                "[bold magenta]AI Runtime[/bold magenta]",
                runtime_state,
            )

        console.print(
            f"[bold cyan]Actions[/bold cyan]   "
            f"{len(actions)}"
        )

        console.print(
            f"[bold]Recommendations[/bold] "
            f"{len(recommendations)}"
        )

    else:
        console.print(ctx)


@app.command("ai-chat")
def ai_chat():
    """Start an interactive ATLAS local AI session."""

    service = AIService()

    console.rule(
        "[bold magenta]ATLAS AI — LOCAL OPERATOR[/bold magenta]"
    )

    console.print(
        "Escribí una pregunta y presioná ENTER."
    )
    console.print(
        "Escribí [bold]exit[/bold] para salir."
    )
    console.print()

    while True:
        try:
            question = typer.prompt(
                "TÚ",
                default="",
                show_default=False,
            ).strip()

        except (EOFError, KeyboardInterrupt):
            console.print("\nSaliendo...")
            break

        if question.lower() in {"exit", "quit"}:
            console.print("Saliendo...")
            break

        if not question:
            continue

        try:
            response = service.ask_operator(
                AIRequest(
                    task="incident_reasoning",
                    user_prompt=question,
                )
            )

            console.print()
            console.print("[bold cyan]ATLAS >[/bold cyan]")
            console.print(response.content)
            console.print()

            metadata = response.metadata or {}

            console.print(
                f"[dim]"
                f"model={response.model} "
                f"provider={response.provider} "
                f"fallback={metadata.get('fallback')} "
                f"tools={metadata.get('tools_used')} "
                f"mcp={metadata.get('mcp_agent')}"
                f"[/dim]"
            )

            console.print()

        except Exception as exc:
            console.print(
                f"[bold red][ERROR][/bold red] {exc}"
            )
            console.print()


@app.command("dev-context")
def dev_context():
    """Show the ATLAS architectural development context."""

    service = DevContextService()
    context = service.build()

    console.rule(
        "[bold cyan]ATLAS DEVELOPMENT CONTEXT[/bold cyan]"
    )

    git = context["git"]

    console.print(
        "[bold]Git[/bold]        "
        f"{git['branch']} | "
        f"{git['commit']} | "
        f"{git['tag']}"
    )

    console.print(
        "[bold]Working tree[/bold] "
        + (
            f"DIRTY ({git['dirty_files']} files)"
            if git["dirty"]
            else "CLEAN"
        )
    )

    symbols = context["symbols"]

    console.print(
        "[bold]Python files[/bold] "
        f"{symbols['python_files']}"
    )

    console.print()

    # --------------------------------------------------------------
    # ARCHITECTURE
    # --------------------------------------------------------------

    console.rule("[bold]ARCHITECTURE[/bold]")

    architecture = context["architecture"]

    for name, info in architecture.items():

        label = (
            "root"
            if name == "."
            else name
        )

        console.print(
            f"[cyan]{label}/[/cyan] "
            f"({info['count']} files)"
        )

        for filename in info["files"]:
            console.print(
                f"  {filename}"
            )

    console.print()

    # --------------------------------------------------------------
    # SYMBOLS
    # --------------------------------------------------------------

    console.rule("[bold]SYMBOLS[/bold]")

    console.print(
        f"Classes       {symbols['class_count']}"
    )

    console.print(
        f"Functions     {symbols['function_count']}"
    )

    console.print()

    # --------------------------------------------------------------
    # DUPLICATION
    # --------------------------------------------------------------

    console.rule(
        "[bold]DUPLICATION CHECK[/bold]"
    )

    duplicates = context["duplicates"]

    duplicate_classes = duplicates[
        "duplicate_classes"
    ]

    duplicate_functions = duplicates[
        "duplicate_functions"
    ]

    if duplicate_classes:

        console.print(
            "[bold yellow]Duplicate classes detected[/bold yellow]"
        )

        for name, entries in sorted(
            duplicate_classes.items()
        ):

            console.print(
                f"  {name}"
            )

            for entry in entries:
                console.print(
                    f"    {entry['file']}:{entry['line']}"
                )

    else:
        console.print(
            "[bold green]No duplicate class names detected[/bold green]"
        )

    console.print()

    if duplicate_functions:

        console.print(
            "[bold yellow]Duplicate functions detected[/bold yellow]"
        )

        for name, entries in sorted(
            duplicate_functions.items()
        ):

            console.print(
                f"  {name}"
            )

            for entry in entries:
                console.print(
                    f"    {entry['file']}:{entry['line']}"
                )

    else:
        console.print(
            "[bold green]No duplicate top-level function names detected[/bold green]"
        )

    console.print()

    # --------------------------------------------------------------
    # ARCHITECTURAL RISKS
    # --------------------------------------------------------------

    console.rule(
        "[bold]ARCHITECTURAL RISKS[/bold]"
    )

    risk = context["risk"]

    console.print(
        f"Service files      {risk['service_files']}"
    )

    console.print(
        f"Model files        {risk['model_files']}"
    )

    duplicate_services = risk[
        "duplicate_service_names"
    ]

    duplicate_models = risk[
        "duplicate_model_names"
    ]

    if duplicate_services:
        console.print(
            "[bold yellow]Repeated service filenames[/bold yellow]"
        )

        for name, count in sorted(
            duplicate_services.items()
        ):
            console.print(
                f"  {name}.py -> {count} files"
            )

    if duplicate_models:
        console.print(
            "[bold yellow]Repeated model filenames[/bold yellow]"
        )

        for name, count in sorted(
            duplicate_models.items()
        ):
            console.print(
                f"  {name}.py -> {count} files"
            )

    if (
        not duplicate_services
        and not duplicate_models
    ):
        console.print(
            "[bold green]No repeated service/model filenames detected[/bold green]"
        )

    console.print()

    # --------------------------------------------------------------
    # RECENT COMMITS
    # --------------------------------------------------------------

    console.rule(
        "[bold]RECENT COMMITS[/bold]"
    )

    for commit in context["recent_commits"]:
        console.print(
            f"  {commit}"
        )

if __name__ == "__main__":
    app()
