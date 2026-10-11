import hashlib
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates

from atlas.core.version import __version__
from atlas.services.sky import SkyObservationService


BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(
    directory=str(
        BASE_DIR / "templates"
    )
)

router = APIRouter()


def _static_asset_version() -> str:
    digest = hashlib.sha256()

    for path in (
        BASE_DIR / "static/css/atlas.css",
        BASE_DIR / "static/css/atlas-sky.css",
    ):
        digest.update(
            path.read_bytes()
        )

    return digest.hexdigest()[:12]


SKY_STATIC_ASSET_VERSION = (
    _static_asset_version()
)


def _service() -> SkyObservationService:
    return SkyObservationService()


@router.get("/sky")
def sky_home(
    request: Request,
):
    service = _service()

    observations = service.list_observations()

    selected = (
        observations[0]
        if observations
        else None
    )

    return templates.TemplateResponse(
        request=request,
        name="sky.html",
        context={
            "atlas_version": __version__,
            "atlas_home_url": os.getenv(
                "ATLAS_HOME_URL",
                "/",
            ),
            "static_asset_version": SKY_STATIC_ASSET_VERSION,
            "sky": service.overview(),
            "observations": observations,
            "selected": selected,
        },
    )


@router.get("/sky/{observation_id}")
def sky_observation(
    observation_id: str,
    request: Request,
):
    service = _service()

    selected = service.get_observation(
        observation_id
    )

    if selected is None:
        raise HTTPException(
            status_code=404,
            detail="Sky observation not found",
        )

    return templates.TemplateResponse(
        request=request,
        name="sky.html",
        context={
            "atlas_version": __version__,
            "atlas_home_url": os.getenv(
                "ATLAS_HOME_URL",
                "/",
            ),
            "static_asset_version": SKY_STATIC_ASSET_VERSION,
            "sky": service.overview(),
            "observations": service.list_observations(),
            "selected": selected,
        },
    )


@router.get("/api/sky/observations")
def sky_observations_api():
    service = _service()

    return {
        "summary": service.overview(),
        "observations": service.list_observations(),
    }


@router.get("/api/sky/observations/{observation_id}")
def sky_observation_api(
    observation_id: str,
):
    observation = (
        _service().get_observation(
            observation_id
        )
    )

    if observation is None:
        raise HTTPException(
            status_code=404,
            detail="Sky observation not found",
        )

    return observation


@router.get(
    "/api/sky/observations/"
    "{observation_id}/artifacts/{artifact_name}"
)
def sky_artifact(
    observation_id: str,
    artifact_name: str,
):
    path = _service().artifact_path(
        observation_id,
        artifact_name,
    )

    if path is None:
        raise HTTPException(
            status_code=404,
            detail="Sky artifact not found",
        )

    return FileResponse(
        path=path,
        filename=path.name,
    )
