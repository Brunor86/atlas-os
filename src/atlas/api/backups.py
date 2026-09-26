from fastapi import APIRouter

from atlas.services.backup_intelligence import (
    BackupInventoryService,
)


router = APIRouter(
    prefix="/api/backups",
    tags=["backups"],
)


service = BackupInventoryService()


@router.get("")
def backup_inventory():
    return service.inventory()
