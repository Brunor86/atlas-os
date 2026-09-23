
from fastapi import APIRouter, HTTPException

from atlas.services.assets.api import AssetAPIService
from atlas.services.noc.impact import ImpactEngine


router = APIRouter(
    prefix="/api/assets",
    tags=["assets"],
)


service = AssetAPIService()
impact = ImpactEngine()



@router.get("")
def list_assets():

    return service.list_assets()





@router.get("/overview")
def overview():

    return service.overview()



@router.get("/dashboard")
def dashboard_assets():

    return {
        "overview": service.overview(),
        "assets": service.list_assets(),
    }


@router.get("/{asset_id}")
def get_asset(asset_id: str):

    asset = service.get_asset(
        asset_id
    )

    if not asset:
        raise HTTPException(
            status_code=404,
            detail="asset not found",
        )

    return asset



@router.get("/{asset_id}/context")
def get_context(asset_id: str):

    context = service.get_context(
        asset_id
    )

    if not context:
        raise HTTPException(
            status_code=404,
            detail="asset context not found",
        )

    return context



@router.get("/{asset_id}/impact")
def get_impact(asset_id: str):

    result = impact.analyze(
        asset_id
    )

    if "error" in result:
        raise HTTPException(
            status_code=404,
            detail=result["error"],
        )

    return result
