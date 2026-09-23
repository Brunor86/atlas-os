
from fastapi import APIRouter

from atlas.services.noc.impact import ImpactEngine


router = APIRouter(
    prefix="/api/noc",
    tags=["noc"],
)


engine = ImpactEngine()



@router.get("/assets/{asset_id}/impact")
def asset_impact(
    asset_id: str,
):

    return engine.analyze(
        asset_id
    )
