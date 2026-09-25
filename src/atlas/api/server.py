import logging
import json
import asyncio
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


from atlas.context.builder import ContextBuilder

from atlas.core.version import __version__
from atlas.api.dashboard import health_score_from_noc_score


from atlas.services.health.service import HealthService
from atlas.services.infrastructure import InfrastructureService
from atlas.services.insights.service import InsightService
from atlas.services.snapshots.loader import SnapshotLoader
from atlas.services.intelligence import IntelligenceService

from atlas.services.events.analytics import EventAnalytics
from atlas.services.events.correlation import EventCorrelation

from atlas.services.noc.service import NOCService
from atlas.services.noc.impact import ImpactEngine
from atlas.services.metrics import MetricsService
from atlas.services.incidents.service import IncidentService
from atlas.services.ai.service import AIService
from atlas.api.stream_status import completed_status
from atlas.services.ai.models import AIRequest
from atlas.services.ai.runtime_status import AIRuntimeStatusService

from atlas.services.control_plane.health import (
    ControlPlaneHealthService,
)

from atlas.services.backup_intelligence.inventory import (
    BackupInventoryService,
)

from atlas.services.assets.api import AssetAPIService
from atlas.api.assets import router as assets_router
from atlas.api.operator_actions import router as operator_actions_router
from atlas.api.backups import router as backups_router


from atlas.storage.repository import SnapshotRepository
from atlas.storage.database import Database
from atlas.storage.event_repository import EventRepository


BASE_DIR = Path(__file__).resolve().parent


logger = logging.getLogger(__name__)


def _diagnostic(*parts):

    logger.debug(
        "%s",
        " ".join(
            str(part)
            for part in parts
        ),
    )




app = FastAPI(
    title="ATLAS API",
    description="Infrastructure API for ATLAS Homelab",
    version=__version__,
)



app.include_router(
    assets_router
)


app.include_router(
    operator_actions_router
)


app.include_router(
    backups_router
)



app.mount(
    "/static",
    StaticFiles(
        directory=BASE_DIR / "static"
    ),
    name="static",
)



templates = Jinja2Templates(
    directory=str(
        BASE_DIR / "templates"
    )
)


ai_service = AIService()

ai_runtime_status = AIRuntimeStatusService()

control_plane_health = ControlPlaneHealthService(
    ai_status=ai_runtime_status
)





@app.get("/")
def home(
    request: Request
):
    _diagnostic("ATLAS DEBUG HOME START")



    _diagnostic("ATLAS DEBUG snapshot")
    infra = SnapshotLoader().load()
    _diagnostic("ATLAS DEBUG snapshot OK")



    if infra is None:
        infra = InfrastructureService().collect()



    #
    # Docker metrics from Prometheus
    #

    _diagnostic("ATLAS DEBUG metrics")
    metrics_service = MetricsService()
    _diagnostic("ATLAS DEBUG metrics OK")



    docker_memory = metrics_service.docker_memory()


    docker_cpu = metrics_service.docker_cpu()



    #
    # Merge Prometheus metrics into containers
    #

    for container in infra.docker.containers:


        if container.name in docker_memory:

            container.memory_mb = docker_memory[container.name]["memory_mb"]



        if container.name in docker_cpu:

            container.cpu_percent = docker_cpu[container.name]["cpu_percent"]





    health = HealthService().evaluate(
        infra
    )



    insights = InsightService().generate(
        infra,
        health,
    )


    #
    # Dashboard rendering is read-only.
    #
    # Event persistence belongs to an explicit operational
    # refresh cycle, never to an HTTP GET request.
    #

    correlation = EventCorrelation()



    incident_correlation = correlation.analyze(
        insights
    )



    repository = SnapshotRepository()



    history = repository.get_history(
        20
    )



    latest = repository.get_latest()


    ctx = ContextBuilder().build(
        infra
    )




    ai_insights = IntelligenceService().analyze(

        ctx,

    )



    event_repository = EventRepository()



    recent_events = event_repository.get_recent_events(
        10
    )



    event_history = event_repository.get_recent_events(
        20
    )



    latest_event = None



    if recent_events:

        latest_event = recent_events[0]



    event_center = {


        "summary": {


            "active":
                event_repository.count_active_events(),


            "severity":
                event_repository.count_by_severity(),


        },


        "latest":
            latest_event,


    }




    analytics = EventAnalytics()



    event_analytics = {


        "summary":
            analytics.summary(),



        "top_events":
            analytics.top_events(3),



        "categories":
            analytics.by_category(),



        "average_duration":
            analytics.average_duration(),


    }





    events = Database().get_active_events()

    incident_service = IncidentService()


    incidents = incident_service.list_all()


    incident_detail = None

    incident_timeline = []


    if incidents:

        incident_id = incidents[0][0]


        incident_detail = incident_service.detail(
            incident_id
        )


        incident_timeline = incident_service.timeline(
            incident_id
        )



    incident_summary = incident_service.summary()


    incident_severity = incident_service.severity_distribution()



    incident_timeline = []


    if incidents:

        incident_timeline = incident_service.timeline(
            incidents[0][0]
        )



    _diagnostic("ATLAS DEBUG NOC INIT")
    noc = NOCService(
        mutations_enabled=False
    )
    _diagnostic("ATLAS DEBUG NOC INIT OK")

    _diagnostic("ATLAS DEBUG NOC GENERATE")

    noc.load_knowledge()

    noc_result = noc.generate(
        {
            "health": health,
            "events": events,
        }
    )

    _diagnostic(
        "ATLAS DEBUG NOC GENERATED",
        noc_result,
    )

    noc_report = {
        "summary": {
            "status": noc_result.status,
            "score": noc_result.score,
            "impact_score": noc_result.score,
            "health_score": health_score_from_noc_score(
                noc_result.score
            ),
            "priority": noc_result.priority,
            "active_events": noc_result.active_events,
            "critical_services": noc_result.critical_services,
        },
        "incidents": [
            incident.__dict__
            for incident in noc_result.incidents
        ],
        "impact": {},
    }




    _diagnostic(
        "DEBUG DASHBOARD IMPACT DISABLED"
    )








    impact = {

        "critical_assets": 0,

        "total_score": 0,

        "severity": "UNKNOWN",

        "assets": []

    }

    if getattr(noc, "incidents", None):

        for incident in noc.incidents:

            info = getattr(
                incident,
                "impact_intelligence",
                {},
            )

            if not info:
                continue

            impact["assets"].append(info)

            impact["critical_assets"] += 1

            impact["total_score"] += info.get(
                "score"
            ) or 0

            if info.get("severity") == "CRITICAL":

                impact["severity"] = "CRITICAL"

            elif (
                info.get("severity") == "HIGH"
                and impact["severity"] != "CRITICAL"
            ):

                impact["severity"] = "HIGH"




    ctx = ContextBuilder().build(
        infra
    )





    backup_inventory = (
        BackupInventoryService().inventory()
    )


    _diagnostic("DEBUG TEMPLATE NOC")
    _diagnostic(noc_report)

    _diagnostic("DEBUG TEMPLATE NOC FINAL")
    _diagnostic(noc_report)

    return templates.TemplateResponse(

        request=request,

        name="index.html",


        context={


            "infra":
                infra,


            "health":
                health,


            "insights":
                insights,


            "ai_insights":
                ai_insights,

            "ai":
                ai_runtime_status.status(),


            "events":
                events,


            "event_center":
                event_center,


            "event_history":
                event_history,


            "event_analytics":
                event_analytics,


            "incident_correlation":
                incident_correlation,

            "incidents":
                incidents,


            "incident_detail":
                incident_detail,


            "incident_timeline":
                incident_timeline,


            "incident_summary":
                incident_summary,


            "incident_severity":
                incident_severity,

            "context":
                ctx,


            "atlas_version":
                __version__,


            "noc":
                noc_report,

            "noc_service":
                noc,

            "impact":
                impact,

            "backups":
                backup_inventory,


        },

    )







@app.get("/health")
def health_endpoint():


    infra = InfrastructureService().collect()



    return HealthService().evaluate(
        infra
    )







@app.get("/api/context")
def context():


    infra = InfrastructureService().collect()




    ctx = ContextBuilder().build(
        infra
    )



    return ctx







@app.get("/api/incidents")
def incidents_api():


    service = IncidentService()


    return {

        "summary":
            service.summary(),


        "severity":
            service.severity_distribution(),


        "incidents":
            service.list_all(),

    }




@app.get("/api/incidents/{incident_id}")
def incident_detail_api(
    incident_id: str,
):


    service = IncidentService()


    return {

        "incident":
            service.detail(
                incident_id
            ),


        "timeline":
            service.timeline(
                incident_id
            ),

    }




@app.post("/api/incidents/{incident_id}/status")
def incident_status_api(
    incident_id: str,
    status: str,
):


    service = IncidentService()


    return service.update_status(

        incident_id,

        status,

    )



@app.get("/api/incidents/{incident_id}/timeline")
def incident_timeline(
    incident_id: str,
):


    service = IncidentService()


    return {

        "incident":
            incident_id,


        "timeline":
            service.timeline(
                incident_id
            ),

    }




@app.get("/api/assets")
def api_assets():

    return AssetAPIService().list_assets()



@app.get("/api/assets/overview")
def api_assets_overview():

    return AssetAPIService().overview()



@app.get("/api/assets/{asset_id}")
def api_asset(asset_id: str):

    asset = AssetAPIService().get_asset(
        asset_id
    )

    if not asset:
        return {
            "error": "asset not found"
        }

    return asset



@app.get("/api/assets/{asset_id}/context")
def api_asset_context(
    asset_id: str,
):

    context = AssetAPIService().get_context(
        asset_id
    )

    if not context:
        return {
            "error": "asset context not found"
        }

    return context



@app.get("/api/system/health")
def system_health():
    return control_plane_health.status()


@app.get("/api/ai/status")
def ai_status():
    return ai_runtime_status.status()

@app.post("/api/ai/ask")
async def ai_ask(
    request: Request,
):
    """
    Ask the ATLAS operator about the current infrastructure.

    The operator decides whether the request can be answered
    deterministically, through MCP knowledge tools, or requires
    the configured local LLM.
    """

    payload = await request.json()

    question = str(
        payload.get(
            "question",
            "",
        )
        or ""
    ).strip()

    if not question:
        return {
            "status": "ERROR",
            "error": "question is required",
        }

    response = ai_service.ask_operator(
        AIRequest(
            task="incident_reasoning",
            user_prompt=question,
        )
    )

    metadata = (
        response.metadata
        or {}
    )

    return {
        "status": "SUCCESS",
        "answer": response.content,
        "latency_ms": response.latency_ms,
        "model": response.model,
        "provider": response.provider,
        "execution": {
            "deterministic":
                bool(
                    metadata.get(
                        "deterministic",
                        False,
                    )
                    or metadata.get(
                        "context_mode"
                    )
                    == "deterministic"
                ),

            "llm_used":
                bool(
                    metadata.get(
                        "llm_used",
                        False,
                    )
                ),

            "mcp_agent":
                bool(
                    metadata.get(
                        "mcp_agent",
                        False,
                    )
                ),

            "planner_calls":
                int(
                    metadata.get(
                        "planner_calls",
                        0,
                    )
                    or 0
                ),

            "tools_used":
                list(
                    metadata.get(
                        "tools_used",
                        [],
                    )
                    or []
                ),

            "context_mode":
                metadata.get(
                    "context_mode"
                ),
        },
    }


def _sse_event(
    event: str,
    data: dict,
) -> str:
    """
    Encode one Server-Sent Event.

    Only observable ATLAS execution information is streamed.
    Internal model reasoning / chain-of-thought is never exposed.
    """

    payload = json.dumps(
        data,
        ensure_ascii=False,
        default=str,
    )

    return (
        f"event: {event}\n"
        f"data: {payload}\n\n"
    )


@app.get("/api/ai/ask/stream")
async def ai_ask_stream(
    question: str,
):
    """
    Stream observable Ask ATLAS activity in real time.

    OperatorAgent emits verified execution lifecycle events.
    No private model reasoning is exposed.
    """

    question = str(
        question or ""
    ).strip()

    if not question:

        async def invalid():

            yield _sse_event(
                "error",
                {
                    "message":
                        "question is required",
                },
            )

        return StreamingResponse(
            invalid(),
            media_type="text/event-stream",
        )


    async def stream():

        loop = (
            asyncio.get_running_loop()
        )

        activity_queue = (
            asyncio.Queue()
        )


        def on_activity(
            event,
            data,
        ):
            """
            OperatorAgent runs in a worker thread.
            Move activity safely onto the ASGI event loop.
            """

            payload = (
                dict(data)
                if isinstance(
                    data,
                    dict,
                )
                else {}
            )

            loop.call_soon_threadsafe(
                activity_queue.put_nowait,
                (
                    str(event),
                    payload,
                ),
            )


        yield _sse_event(
            "started",
            {
                "message":
                    "ATLAS received your request.",

                "question":
                    question,
            },
        )


        task = asyncio.create_task(
            asyncio.to_thread(
                ai_service.ask_operator,
                AIRequest(
                    task="incident_reasoning",
                    user_prompt=question,
                ),
                event_callback=on_activity,
            )
        )


        while True:

            if (
                task.done()
                and activity_queue.empty()
            ):
                break


            queue_task = asyncio.create_task(
                activity_queue.get()
            )


            done, pending = await asyncio.wait(
                {
                    task,
                    queue_task,
                },
                timeout=1.0,
                return_when=asyncio.FIRST_COMPLETED,
            )


            if queue_task in done:

                event, data = (
                    queue_task.result()
                )

                yield _sse_event(
                    event,
                    data,
                )

            else:

                queue_task.cancel()

                try:
                    await queue_task
                except asyncio.CancelledError:
                    pass


            if (
                not done
                and not task.done()
            ):

                # Transport heartbeat only while ATLAS is
                # genuinely still working.
                yield ": heartbeat\n\n"


        # Give thread-safe callbacks scheduled at task completion
        # one event-loop turn to reach the queue.
        await asyncio.sleep(0)


        while not activity_queue.empty():

            event, data = (
                activity_queue.get_nowait()
            )

            yield _sse_event(
                event,
                data,
            )


        try:

            response = (
                await task
            )

        except Exception as exc:

            yield _sse_event(
                "error",
                {
                    "message":
                        (
                            "ATLAS could not "
                            "complete the request."
                        ),

                    "detail":
                        str(exc),
                },
            )

            return


        metadata = (
            response.metadata
            or {}
        )


        execution = {
            "deterministic":
                bool(
                    metadata.get(
                        "deterministic",
                        False,
                    )
                    or metadata.get(
                        "context_mode"
                    )
                    == "deterministic"
                ),

            "llm_used":
                bool(
                    metadata.get(
                        "llm_used",
                        False,
                    )
                ),

            "mcp_agent":
                bool(
                    metadata.get(
                        "mcp_agent",
                        False,
                    )
                ),

            "planner_calls":
                int(
                    metadata.get(
                        "planner_calls",
                        0,
                    )
                    or 0
                ),

            "tools_used":
                list(
                    metadata.get(
                        "tools_used",
                        [],
                    )
                    or []
                ),

            "context_mode":
                metadata.get(
                    "context_mode"
                ),
        }


        yield _sse_event(
            "execution",
            execution,
        )


        yield _sse_event(
            "answer",
            {
                "content":
                    response.content,

                "latency_ms":
                    response.latency_ms,

                "model":
                    response.model,

                "provider":
                    response.provider,
            },
        )


        yield _sse_event(
            "completed",
            {
                "status":
                    completed_status(
                        metadata
                    ),
            },
        )


    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":
                "no-cache",

            "Connection":
                "keep-alive",

            "X-Accel-Buffering":
                "no",
        },
    )

